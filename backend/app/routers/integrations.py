import os
import json
import uuid
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Request, Body, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings, build_frontend_redirect
from app.config.auth import create_access_token, get_current_user_id
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

router = APIRouter()

@router.get("")
@router.get("/")
def get_user_integrations(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all connected external accounts for the current application user.
    Includes platform AI (Groq) and customer AI connections.
    Sanitizes output to guarantee NO raw access tokens, refresh tokens, or API keys are exposed.
    """
    connections = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id
    ).all()

    connected_providers = [c.to_safe_dict() for c in connections]
    
    groq_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
    platform_ai = {
        "provider": "groq",
        "name": "Groq Platform AI",
        "status": "AVAILABLE" if (groq_key and groq_key.strip()) else "NOT_CONFIGURED",
        "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
        "is_platform_default": True,
        "description": "Groq is provided by the platform and is available automatically when you don't use a personal AI provider."
    }

    conn_map = {c.provider.lower(): c for c in connections}

    customer_ai_providers = [
        {"provider": "openai", "name": "OpenAI / ChatGPT", "model_info": "GPT-4o & Mini models"},
        {"provider": "gemini", "name": "Google Gemini", "model_info": "Gemini Flash & Pro models"},
        {"provider": "claude", "name": "Anthropic Claude", "model_info": "Claude 3.5 Sonnet"}
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

    all_providers = [
        {"provider": "google", "name": "Google (Search Console / Profile / Business)", "category": "Search & Analytics", "supports_oauth": True},
        {"provider": "meta", "name": "Meta (Facebook Pages & Instagram)", "category": "Social & Marketing", "supports_oauth": True},
        {"provider": "openai", "name": "OpenAI (GPT-4o)", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "gemini", "name": "Google Gemini AI", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "claude", "name": "Claude AI (Anthropic)", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "microsoft", "name": "Microsoft Workspace", "category": "Search & Analytics", "supports_oauth": True},
        {"provider": "linkedin", "name": "LinkedIn Business", "category": "Social & Marketing", "supports_oauth": True},
        {"provider": "twitter", "name": "X / Twitter", "category": "Social & Marketing", "supports_oauth": True},
    ]

    return {
        "user_id": user_id,
        "platform_ai": platform_ai,
        "customer_ai": customer_ai,
        "connections": connected_providers,
        "supported_providers": all_providers
    }

@router.get("/{provider}/connect")
def connect_provider_oauth(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    request: Request = None
):
    """
    Generates a secure OAuth authorization URL for the requested provider with CSRF state protection.
    Binds the OAuth state to the currently authenticated SEO Intelligence user.
    """
    p = provider.lower()
    print(f"[GOOGLE OAUTH] Explicit OAuth login URL requested for provider='{p}', user_id='{user_id}'", flush=True)

    if user_id.startswith("guest_"):
        raise HTTPException(
            status_code=403,
            detail="Sign in to connect external accounts."
        )

    if p in ("openai", "gemini", "claude"):
        raise HTTPException(
            status_code=400,
            detail=f"{provider.title()} uses User API Key registration."
        )

    try:
        redirect_base = str(request.base_url).rstrip("/") if request else settings.API_BASE_URL
        auth_url = build_authorization_url(p, user_id=user_id, redirect_base=redirect_base)
        
        return {
            "status": "ok",
            "provider": p,
            "user_id": user_id,
            "authorization_url": auth_url
        }
    except ValueError as err:
        print(f"[GOOGLE OAUTH] Failed to generate login URL: {err}", flush=True)
        raise HTTPException(status_code=400, detail=str(err))

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
        target_url = build_frontend_redirect("/settings", {
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
        success_url = build_frontend_redirect("/settings", {
            "integration": "success",
            "provider": provider,
            "token": session_token
        })
        print(f"[GOOGLE OAUTH] OAuth transaction completed cleanly. Redirecting to frontend settings without starting OAuth again.", flush=True)
        return RedirectResponse(url=success_url)

    except ValueError as val_err:
        print(f"[GOOGLE OAUTH ERROR] State or token validation failed: {val_err}", flush=True)
        err_url = build_frontend_redirect("/settings", {
            "integration": "error",
            "provider": provider,
            "error": "validation_error",
            "msg": str(val_err)
        })
        return RedirectResponse(url=err_url)
    except Exception as exc:
        print(f"[GOOGLE OAUTH EXCEPTION] Callback error: {exc}", flush=True)
        err_url = build_frontend_redirect("/settings", {
            "integration": "error",
            "provider": provider,
            "error": "authentication_failed",
            "msg": "OAuth authentication failed."
        })
        return RedirectResponse(url=err_url)

from app.llm.llm_provider import (
    OpenAIProviderAdapter,
    GeminiProviderAdapter,
    AnthropicProviderAdapter,
    AIProviderException
)

@router.post("/{provider}/disconnect")
def disconnect_provider(
    provider: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects external connection and purges stored OAuth tokens / customer API keys.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == provider
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail=f"No active '{provider}' connection found for user.")

    db.delete(conn)
    db.commit()

    return {
        "status": "success",
        "message": f"{provider.title()} account disconnected successfully."
    }

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
            test_res = provider_adapter.test_connection()
            print(f"[CUSTOMER AI KEY] Verified {p_clean} key for user '{user_id}': {test_res}", flush=True)
    except AIProviderException as ai_err:
        print(f"[CUSTOMER AI KEY ERROR] Verification failed for {p_clean}: {ai_err.message}", flush=True)
        raise HTTPException(
            status_code=400,
            detail=f"Unable to verify {p_clean.title()} API Key: {ai_err.message}"
        )
    except Exception as err:
        print(f"[CUSTOMER AI KEY ERROR] Unexpected verification error: {err}", flush=True)
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

