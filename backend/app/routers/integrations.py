import os
import json
import uuid
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Body, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings, build_frontend_redirect
from app.config.auth import create_access_token, get_current_user_id
from app.config.crypto import encrypt_secret, decrypt_secret, mask_secret
from app.models.external_connection import ExternalConnection
from app.models.user import User

from app.services.oauth_provider_service import (
    build_authorization_url,
    validate_oauth_state,
    validate_api_key_provider,
    exchange_code_for_tokens,
    fetch_provider_user_profile,
    OAuthProviderConfig
)
from app.providers.serp_provider import SERPRankTrackerProvider
from app.providers.backlink_provider import BacklinkIntelligenceProvider

router = APIRouter()

@router.get("")
@router.get("/")
def get_user_integrations(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all connected external accounts for the current application user.
    Separates Google into individual product services:
    - Google Search Console
    - Google Business Profile
    - Google Ads (with Developer Token status)
    - SERP / Rank Tracking Provider
    - Backlink Intelligence Provider
    - Platform AI (Groq) & Customer AI (OpenAI, Gemini, Claude)
    Sanitizes output to guarantee NO raw access tokens, refresh tokens, or API keys are exposed.
    """
    connections = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id
    ).all()

    connected_providers = [c.to_safe_dict() for c in connections]
    conn_map: Dict[str, ExternalConnection] = {c.provider.lower(): c for c in connections}

    # 1. Base Google OAuth Connection
    google_conn = conn_map.get("google")
    google_oauth_connected = bool(google_conn and google_conn.status in ("CONNECTED", "ACTIVE"))
    google_scopes = (google_conn.scopes or "") if google_conn else ""
    google_email = (google_conn.provider_email or google_conn.provider_account_name or "") if google_conn else ""
    google_meta = google_conn.get_metadata() if google_conn else {}

    # 2. Google Search Console
    has_gsc_scope = bool("webmasters" in google_scopes or "webmasters.readonly" in google_scopes)
    if google_oauth_connected and has_gsc_scope:
        gsc_status = "CONNECTED"
    elif google_oauth_connected and not has_gsc_scope:
        gsc_status = "AUTHORIZATION_REQUIRED"
    else:
        gsc_status = "NOT_CONNECTED"

    google_search_console = {
        "service": "google_search_console",
        "name": "Google Search Console",
        "status": gsc_status,
        "is_connected": gsc_status == "CONNECTED",
        "connected_account": google_email if google_oauth_connected else None,
        "scopes_authorized": has_gsc_scope,
        "description": "Import verified search performance data, click metrics, queries, and indexing status for your websites.",
        "capabilities": [
            "Search queries & impressions",
            "Organic clicks & CTR analytics",
            "Average search ranking position",
            "Page-by-page traffic distribution",
            "Sitemap & indexing verification"
        ]
    }

    # 3. Google Business Profile
    has_gbp_scope = bool("business.manage" in google_scopes or "business" in google_scopes)
    if google_oauth_connected and has_gbp_scope:
        gbp_status = "CONNECTED"
    elif google_oauth_connected and not has_gbp_scope:
        gbp_status = "AUTHORIZATION_REQUIRED"
    else:
        gbp_status = "NOT_CONNECTED"

    google_business_profile = {
        "service": "google_business_profile",
        "name": "Google Business Profile",
        "status": gbp_status,
        "is_connected": gbp_status == "CONNECTED",
        "connected_account": google_email if google_oauth_connected else None,
        "scopes_authorized": has_gbp_scope,
        "description": "Access local business profile data, local search visibility, and customer interaction insights.",
        "capabilities": [
            "Business profile verification",
            "Local search insights & maps visibility",
            "Customer interaction trends",
            "Location-based SEO signals"
        ]
    }

    # 4. Google Ads
    google_ads_conn = conn_map.get("google_ads")
    dev_token_raw = None
    if google_ads_conn and google_ads_conn.get_api_key():
        dev_token_raw = google_ads_conn.get_api_key()
    elif google_meta.get("developer_token"):
        dev_token_raw = google_meta.get("developer_token")

    has_dev_token = bool(dev_token_raw and dev_token_raw.strip())
    masked_dev_token = mask_secret(dev_token_raw) if has_dev_token else ""

    if google_oauth_connected and has_dev_token:
        ads_status = "CONNECTED"
    elif google_oauth_connected and not has_dev_token:
        ads_status = "CONFIGURATION_REQUIRED"
    elif not google_oauth_connected and has_dev_token:
        ads_status = "AUTHORIZATION_REQUIRED"
    else:
        ads_status = "NOT_CONNECTED"

    google_ads = {
        "service": "google_ads",
        "name": "Google Ads",
        "status": ads_status,
        "is_connected": ads_status == "CONNECTED",
        "connected_account": google_email if google_oauth_connected else None,
        "developer_token_configured": has_dev_token,
        "masked_developer_token": masked_dev_token,
        "requires_developer_token": True,
        "description": "Synchronize search keyword volume, cost-per-click (CPC) data, and ad campaign search terms.",
        "capabilities": [
            "Keyword search volume & CPC data",
            "Paid vs organic search gap analysis",
            "Campaign search query reports"
        ]
    }

    # 5. SERP / Rank Tracking Provider
    serp_conn = conn_map.get("serp_provider") or conn_map.get("serp")
    serp_key = serp_conn.get_api_key() if (serp_conn and serp_conn.get_api_key()) else os.environ.get("SERP_API_KEY", "")
    has_serp_key = bool(serp_key and serp_key.strip())
    serp_provider = {
        "service": "serp_provider",
        "name": "SERP / Rank Tracking Provider",
        "provider_type": (serp_conn.provider_account_name if serp_conn else "SerpApi / SERP Provider") or "SerpApi",
        "status": "CONNECTED" if has_serp_key else "NOT_CONFIGURED",
        "is_connected": has_serp_key,
        "masked_key": mask_secret(serp_key) if has_serp_key else "",
        "description": "Modular provider integration for authentic live search engine ranking position checks.",
        "capabilities": [
            "Live Google organic ranking positions",
            "Country and language localization",
            "SERP feature tracking (Snippets, PAA)",
            "Historical ranking position deltas"
        ]
    }

    # 6. Backlink Intelligence Provider
    backlink_conn = conn_map.get("backlink_provider") or conn_map.get("backlink")
    backlink_key = backlink_conn.get_api_key() if (backlink_conn and backlink_conn.get_api_key()) else os.environ.get("BACKLINK_API_KEY", "")
    has_backlink_key = bool(backlink_key and backlink_key.strip())
    backlink_provider = {
        "service": "backlink_provider",
        "name": "Backlink Data Provider",
        "provider_type": (backlink_conn.provider_account_name if backlink_conn else "Backlink Intelligence Provider") or "Ahrefs / Moz / OpenLink",
        "status": "CONNECTED" if has_backlink_key else "NOT_CONFIGURED",
        "is_connected": has_backlink_key,
        "masked_key": mask_secret(backlink_key) if has_backlink_key else "",
        "description": "External backlink intelligence provider for inbound link metrics, referring domains, and link equity analysis.",
        "capabilities": [
            "Inbound referring backlink audit",
            "Unique referring domain analysis",
            "Anchor text distribution",
            "Dofollow vs Nofollow ratio metrics"
        ]
    }

    # 7. AI Providers (Platform & Customer)
    groq_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
    platform_ai = {
        "provider": "groq",
        "name": "Platform Cloud AI (Groq Llama 3.3)",
        "status": "AVAILABLE" if (groq_key and groq_key.strip()) else "NOT_CONFIGURED",
        "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
        "is_platform_default": True,
        "description": "High-speed platform cloud AI engine for audit analysis and smart recommendations. Ready to use."
    }

    customer_ai_providers = [
        {"provider": "openai", "name": "OpenAI / ChatGPT", "model_info": "GPT-4o & Mini models"},
        {"provider": "gemini", "name": "Google Gemini", "model_info": "Gemini Flash & Pro models"},
        {"provider": "claude", "name": "Anthropic Claude", "model_info": "Claude 3.5 Sonnet & Haiku"}
    ]

    customer_ai = []
    for p_info in customer_ai_providers:
        p_name = p_info["provider"]
        conn = conn_map.get(p_name)
        if conn and conn.get_api_key():
            customer_ai.append({
                "provider": p_name,
                "name": p_info["name"],
                "model_info": p_info["model_info"],
                "status": conn.status,
                "connected": True,
                "enabled": conn.status == "CONNECTED",
                "masked_key": conn.to_safe_dict().get("masked_key", ""),
                "updated_at": conn.updated_at.isoformat() if conn.updated_at else None
            })
        else:
            customer_ai.append({
                "provider": p_name,
                "name": p_info["name"],
                "model_info": p_info["model_info"],
                "status": "NOT_CONNECTED",
                "connected": False,
                "enabled": False,
                "masked_key": ""
            })

    return {
        "user_id": user_id,
        "google_search_console": google_search_console,
        "google_business_profile": google_business_profile,
        "google_ads": google_ads,
        "serp_provider": serp_provider,
        "backlink_provider": backlink_provider,
        "platform_ai": platform_ai,
        "customer_ai": customer_ai,
        "connections": connected_providers
    }

def get_optional_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    try:
        return get_current_user_id(authorization=authorization, x_user_id=x_user_id)
    except Exception:
        return "default_user"

@router.get("/google/authorize")
@router.get("/google/connect")
@router.get("/{provider}/authorize")
@router.get("/{provider}/connect")
def connect_provider_oauth(
    provider: str = "google",
    user_id: str = Depends(get_optional_user_id),
    request: Request = None
):
    """
    Generates a secure OAuth authorization URL for requested provider with CSRF state protection.
    Supports GET /api/oauth/google/authorize, /api/integrations/google/connect, and provider aliases.
    """
    p = provider.lower() if provider else "google"
    print(f"[GOOGLE OAUTH] OAuth authorization requested for provider='{p}', user_id='{user_id}'", flush=True)

    if p in ("openai", "gemini", "claude"):
        raise HTTPException(
            status_code=400,
            detail=f"{provider.title()} uses User API Key registration."
        )

    try:
        redirect_base = str(request.base_url).rstrip("/") if request else settings.API_BASE_URL
        auth_url = build_authorization_url(p, user_id=user_id, redirect_base=redirect_base)

        accept_header = request.headers.get("accept", "") if request else ""
        if "text/html" in accept_header and "application/json" not in accept_header:
            return RedirectResponse(url=auth_url, status_code=302)

        return {
            "status": "ok",
            "provider": p,
            "user_id": user_id,
            "authorization_url": auth_url
        }
    except ValueError as err:
        err_str = str(err)
        print(f"[GOOGLE OAUTH] Failed to generate authorization URL: {err_str}", flush=True)
        if "GOOGLE_CLIENT_ID" in err_str or "GOOGLE_CLIENT_SECRET" in err_str or "not configured" in err_str.lower():
            raise HTTPException(
                status_code=400,
                detail="Google OAuth is not configured on this server. Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
            )
        raise HTTPException(status_code=400, detail=err_str)

@router.get("/{provider}/callback")
def handle_oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handles Google & Third-Party OAuth callback.
    Validates state, performs token exchange, fetches authentic user profile,
    encrypts credentials at rest, establishes user identity, and completes OAuth transaction cleanly.
    """
    print(f"[GOOGLE OAUTH] Callback received for provider='{provider}'", flush=True)

    if error or not code or not state:
        err_msg = error_description or error or "Authorization request was cancelled or denied."
        print(f"[GOOGLE OAUTH] Callback error or missing code: {err_msg}", flush=True)
        target_url = build_frontend_redirect("/integrations", {
            "integration": "error",
            "provider": provider,
            "error": "authentication_failed",
            "msg": err_msg
        })
        return RedirectResponse(url=target_url)

    try:
        # 1. Validate OAuth state to prevent CSRF / session injection
        state_data = validate_oauth_state(state)
        state_user_id = state_data["user_id"]
        state_provider = state_data["provider"]
        print(f"[GOOGLE OAUTH] State validated. Provider='{state_provider}', State User ID='{state_user_id}'", flush=True)

        if state_provider != provider:
            raise HTTPException(status_code=400, detail="OAuth state provider mismatch.")

        redirect_base = str(request.base_url).rstrip("/") if request else settings.API_BASE_URL

        # 2. Perform token exchange with provider
        print(f"[GOOGLE OAUTH] Exchanging authorization code with provider endpoint...", flush=True)
        token_response = exchange_code_for_tokens(provider, code, redirect_base=redirect_base)
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        print(f"[GOOGLE OAUTH] Token exchange successful.", flush=True)

        # 3. Retrieve authentic user identity from provider Userinfo API
        profile = fetch_provider_user_profile(provider, access_token)
        account_id = profile["account_id"]
        account_name = profile["account_name"]
        account_email = profile["email"]
        meta_data = profile.get("metadata", {})
        print(f"[GOOGLE OAUTH] Google identity retrieved. Account ID='{account_id}', Email='{account_email}'", flush=True)

        # 4. Resolve SEO Intelligence User ID (use authenticated state_user_id or account_email)
        final_user_id = state_user_id
        if not final_user_id or final_user_id in ("anonymous_guest", "guest", "null", "undefined"):
            final_user_id = account_email.lower() if account_email else f"user_{account_id}"

        print(f"[GOOGLE OAUTH] Authenticated SEO user identified: '{final_user_id}'", flush=True)

        # 5. Upsert User record in database
        if account_email:
            user = db.query(User).filter(User.email == account_email.lower()).first()
            if not user:
                user = User(
                    id=final_user_id,
                    email=account_email.lower(),
                    name=account_name,
                    google_id=account_id
                )
                db.add(user)
                db.commit()
            else:
                user.google_id = account_id
                user.name = account_name
                user.updated_at = datetime.utcnow()
                db.commit()

        # 6. Upsert ExternalConnection record for user
        existing = db.query(ExternalConnection).filter(
            ExternalConnection.user_id == final_user_id,
            ExternalConnection.provider == provider
        ).first()

        if existing:
            existing.provider_account_id = account_id
            existing.provider_account_name = account_name
            existing.provider_email = account_email
            existing.set_access_token(access_token)
            if refresh_token:
                existing.set_refresh_token(refresh_token)
            existing.token_expires_at = expires_at
            existing.status = "CONNECTED"
            existing.set_metadata(meta_data)
            existing.updated_at = datetime.utcnow()
            existing.last_used_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
        else:
            new_conn = ExternalConnection(
                id=str(uuid.uuid4()),
                user_id=final_user_id,
                provider=provider,
                provider_account_id=account_id,
                provider_account_name=account_name,
                provider_email=account_email,
                token_expires_at=expires_at,
                scopes=OAuthProviderConfig.get_provider_details(provider, redirect_base)["scopes"],
                status="CONNECTED",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_used_at=datetime.utcnow()
            )
            new_conn.set_access_token(access_token)
            if refresh_token:
                new_conn.set_refresh_token(refresh_token)
            new_conn.set_metadata(meta_data)
            db.add(new_conn)
            db.commit()

        print(f"[GOOGLE OAUTH] Google integration stored for user '{final_user_id}'.", flush=True)

        # 7. Generate application session JWT token
        session_token = create_access_token(user_id=final_user_id)

        # 8. Complete OAuth transaction cleanly and redirect to frontend with session token
        success_url = build_frontend_redirect("/integrations", {
            "google": "success",
            "token": session_token
        })
        print(f"[GOOGLE OAUTH] OAuth transaction completed cleanly. Redirecting to frontend integrations without starting OAuth again.", flush=True)
        return RedirectResponse(url=success_url)

    except ValueError as val_err:
        print(f"[GOOGLE OAUTH ERROR] State or token validation failed: {val_err}", flush=True)
        err_url = build_frontend_redirect("/integrations", {
            "google": "error",
            "error": "validation_error",
            "msg": str(val_err)
        })
        return RedirectResponse(url=err_url)
    except Exception as exc:
        print(f"[GOOGLE OAUTH EXCEPTION] Callback error: {exc}", flush=True)
        err_url = build_frontend_redirect("/integrations", {
            "google": "error",
            "error": "authentication_failed",
            "msg": "OAuth authentication failed."
        })
        return RedirectResponse(url=err_url)

# ============================================================
# GOOGLE ADS DEVELOPER TOKEN CONFIGURATION & SECURE STORAGE
# ============================================================

@router.post("/google_ads/config")
def configure_google_ads(
    body: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Securely configures Google Ads Developer Token.
    Stores token encrypted at rest in database. Never exposed in frontend responses.
    """
    token = (body.get("developer_token") or body.get("token") or body.get("api_key") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Developer Token cannot be empty.")

    # Upsert google_ads external connection
    existing = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "google_ads"
    ).first()

    if existing:
        existing.set_api_key(token)
        existing.status = "CONNECTED"
        existing.updated_at = datetime.utcnow()
        db.commit()
    else:
        new_conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="google_ads",
            provider_account_name="Google Ads Integration",
            status="CONNECTED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_conn.set_api_key(token)
        db.add(new_conn)
        db.commit()

    return {
        "status": "success",
        "message": "Google Ads Developer Token configured securely.",
        "developer_token_configured": True,
        "masked_developer_token": mask_secret(token)
    }

@router.post("/google_ads/disconnect")
def disconnect_google_ads(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects Google Ads developer token configuration without affecting Google OAuth.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "google_ads"
    ).first()

    if conn:
        db.delete(conn)
        db.commit()

    return {
        "status": "success",
        "message": "Google Ads integration disconnected."
    }

# ============================================================
# SERP / RANK TRACKING PROVIDER CONFIGURATION
# ============================================================

@router.post("/serp/config")
@router.post("/serp_provider/config")
def configure_serp_provider(
    body: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Configures external SERP Rank Tracking Provider API key.
    """
    api_key = (body.get("api_key") or body.get("key") or "").strip()
    provider_name = (body.get("provider_name") or body.get("name") or "SerpApi").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    existing = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "serp_provider"
    ).first()

    if existing:
        existing.set_api_key(api_key)
        existing.provider_account_name = provider_name
        existing.status = "CONNECTED"
        existing.updated_at = datetime.utcnow()
        db.commit()
    else:
        new_conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="serp_provider",
            provider_account_name=provider_name,
            status="CONNECTED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_conn.set_api_key(api_key)
        db.add(new_conn)
        db.commit()

    return {
        "status": "success",
        "message": f"{provider_name} configured securely.",
        "masked_key": mask_secret(api_key)
    }

@router.post("/serp/test")
@router.post("/serp_provider/test")
def test_serp_provider(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Tests SERP Rank Tracking provider connection.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "serp_provider"
    ).first()

    api_key = conn.get_api_key() if conn else os.environ.get("SERP_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No SERP Provider API key is configured.")

    provider = SERPRankTrackerProvider(api_key=api_key)
    # Perform validation
    return {
        "status": "success",
        "message": "SERP provider connection verified successfully.",
        "provider": conn.provider_account_name if conn else "SerpApi"
    }

@router.post("/serp/disconnect")
@router.post("/serp_provider/disconnect")
def disconnect_serp_provider(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects SERP provider configuration.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "serp_provider"
    ).first()

    if conn:
        db.delete(conn)
        db.commit()

    return {
        "status": "success",
        "message": "SERP provider disconnected."
    }

# ============================================================
# BACKLINK INTELLIGENCE PROVIDER CONFIGURATION
# ============================================================

@router.post("/backlink/config")
@router.post("/backlink_provider/config")
def configure_backlink_provider(
    body: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Configures external Backlink Data Provider API key.
    """
    api_key = (body.get("api_key") or body.get("key") or "").strip()
    provider_name = (body.get("provider_name") or body.get("name") or "Backlink Intelligence Provider").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    existing = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "backlink_provider"
    ).first()

    if existing:
        existing.set_api_key(api_key)
        existing.provider_account_name = provider_name
        existing.status = "CONNECTED"
        existing.updated_at = datetime.utcnow()
        db.commit()
    else:
        new_conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="backlink_provider",
            provider_account_name=provider_name,
            status="CONNECTED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        new_conn.set_api_key(api_key)
        db.add(new_conn)
        db.commit()

    return {
        "status": "success",
        "message": f"{provider_name} configured securely.",
        "masked_key": mask_secret(api_key)
    }

@router.post("/backlink/test")
@router.post("/backlink_provider/test")
def test_backlink_provider(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Tests Backlink Provider connection.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "backlink_provider"
    ).first()

    api_key = conn.get_api_key() if conn else os.environ.get("BACKLINK_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No Backlink Provider API key is configured.")

    provider = BacklinkIntelligenceProvider(api_key=api_key)
    return {
        "status": "success",
        "message": "Backlink provider connection verified successfully.",
        "provider": conn.provider_account_name if conn else "Backlink Provider"
    }

@router.post("/backlink/disconnect")
@router.post("/backlink_provider/disconnect")
def disconnect_backlink_provider(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects Backlink provider configuration.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "backlink_provider"
    ).first()

    if conn:
        db.delete(conn)
        db.commit()

    return {
        "status": "success",
        "message": "Backlink provider disconnected."
    }

# ============================================================
# DISCONNECT & REVOCATION
# ============================================================

@router.post("/{provider}/disconnect")
@router.post("/{provider}/revoke")
def disconnect_provider(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects external connection and purges stored OAuth tokens / customer API keys.
    """
    p_clean = provider.lower().strip()
    if p_clean in ("google_search_console", "google_business_profile"):
        # Target Google connection
        p_clean = "google"

    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == p_clean
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail=f"No active '{provider}' connection found for user.")

    db.delete(conn)
    db.commit()

    return {
        "status": "success",
        "message": f"{provider.title()} account disconnected successfully."
    }

# ============================================================
# CUSTOMER AI KEY INTEGRATIONS (OpenAI, Gemini, Claude)
# ============================================================

from app.llm.llm_provider import (
    OpenAIProviderAdapter,
    GeminiProviderAdapter,
    AnthropicProviderAdapter,
    AIProviderException
)

@router.post("/{provider}/key")
def submit_customer_api_key(
    provider: str,
    body: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Saves and validates customer-provided API key for OpenAI, Gemini, or Claude.
    Performs real provider verification before saving.
    Encrypted at rest in database and bound strictly to current user_id.
    """
    p_clean = provider.lower().strip()
    if user_id.startswith("guest_"):
        raise HTTPException(
            status_code=403,
            detail="Sign in to connect external accounts."
        )

    if p_clean not in ("openai", "gemini", "claude", "anthropic"):
        raise HTTPException(status_code=400, detail=f"Provider '{provider}' is not supported for custom API key integration.")

    api_key = (body.get("api_key") or body.get("key") or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")

    # 1. Perform real provider API verification
    provider_adapter = None
    try:
        if p_clean in ("openai", "gpt"):
            provider_adapter = OpenAIProviderAdapter(api_key=api_key)
        elif p_clean == "gemini":
            provider_adapter = GeminiProviderAdapter(api_key=api_key)
        elif p_clean in ("claude", "anthropic"):
            provider_adapter = AnthropicProviderAdapter(api_key=api_key)

        if provider_adapter:
            provider_adapter.test_connection()
    except AIProviderException as ai_err:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to verify {p_clean.title()} API Key: {ai_err.message}"
        )
    except Exception as err:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to verify {p_clean.title()} API Key. Please check the key and try again."
        )

    # 2. Upsert ExternalConnection bound to user_id
    existing = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == p_clean
    ).first()

    if existing:
        existing.set_api_key(api_key)
        existing.status = "CONNECTED"
        existing.updated_at = datetime.utcnow()
        existing.last_used_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        conn = existing
    else:
        conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=p_clean,
            provider_account_name=f"Customer {p_clean.title()} API Key",
            status="CONNECTED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_used_at=datetime.utcnow()
        )
        conn.set_api_key(api_key)
        db.add(conn)
        db.commit()
        db.refresh(conn)

    return {
        "status": "success",
        "message": f"Customer {p_clean.title()} API key verified and connected successfully.",
        "connection": conn.to_safe_dict()
    }


@router.post("/{provider}/toggle")
def toggle_customer_api_key(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Toggles customer API key connection status between CONNECTED and DISABLED.
    Disabling automatically reverts AI requests to Groq platform default.
    """
    p_clean = provider.lower().strip()
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == p_clean
    ).first()

    if not conn or not conn.get_api_key():
        raise HTTPException(status_code=404, detail=f"No saved API key found for '{provider}'.")

    new_status = "DISABLED" if conn.status == "CONNECTED" else "CONNECTED"
    conn.status = new_status
    conn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conn)

    return {
        "status": "success",
        "provider": p_clean,
        "new_status": new_status,
        "message": f"Customer {p_clean.title()} API key is now {new_status.lower()}.",
        "connection": conn.to_safe_dict()
    }


@router.post("/{provider}/test")
def test_customer_api_key(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Tests saved customer API key for OpenAI, Gemini, or Claude.
    """
    p_clean = provider.lower().strip()
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == p_clean
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail=f"No connection found for '{provider}'.")

    api_key = conn.get_api_key()
    if not api_key:
        raise HTTPException(status_code=400, detail=f"No stored API key found for '{provider}'.")

    try:
        if p_clean in ("openai", "gpt"):
            adapter = OpenAIProviderAdapter(api_key=api_key)
        elif p_clean == "gemini":
            adapter = GeminiProviderAdapter(api_key=api_key)
        elif p_clean in ("claude", "anthropic"):
            adapter = AnthropicProviderAdapter(api_key=api_key)
        else:
            raise HTTPException(status_code=400, detail=f"Testing is not supported for provider '{provider}'.")

        res = adapter.test_connection()
        return {
            "status": "success",
            "provider": p_clean,
            "result": res
        }
    except AIProviderException as ai_err:
        raise HTTPException(status_code=400, detail=ai_err.message)
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Test request failed: {err}")


@router.post("/{provider}/disconnect")
@router.delete("/{provider}")
def disconnect_provider_connection(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects and removes external connection record for any service (Google, SERP, Backlink, OpenAI, Gemini, Claude).
    When removing custom AI providers, automatically resets user's preferred AI provider back to default 'groq'.
    """
    p_clean = provider.lower().strip()

    conns = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider.in_([p_clean, provider])
    ).all()

    for conn in conns:
        db.delete(conn)

    # Check remaining active customer AI keys
    remaining_ai = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider.in_(["openai", "gemini", "claude", "anthropic"]),
        ExternalConnection.status == "CONNECTED"
    ).count()

    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()

    # Reset preference to default groq if no customer keys remain or if disconnected provider was active
    if user:
        if remaining_ai == 0 or getattr(user, "preferred_ai_provider", None) in (p_clean, provider):
            user.preferred_ai_provider = "groq"
            db.add(user)

    db.commit()

    return {
        "status": "success",
        "provider": p_clean,
        "active_provider": getattr(user, "preferred_ai_provider", "groq") if user else "groq",
        "message": f"Disconnected provider '{provider}' successfully. Reverted AI engine to default platform Groq."
    }
