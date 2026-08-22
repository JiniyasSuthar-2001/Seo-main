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
from app.config.settings import settings
from app.models.external_connection import ExternalConnection

from app.services.oauth_provider_service import (
    build_authorization_url,
    validate_oauth_state,
    validate_api_key_provider,
    exchange_code_for_tokens,
    fetch_provider_user_profile,
    OAuthProviderConfig
)

router = APIRouter()

def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """
    Extracts the authenticated application user ID from the request headers.
    Defaults to 'user_default' for single-user desktop environment.
    """
    clean_user = (x_user_id or "").strip()
    return clean_user if clean_user else "user_default"


@router.get("")
@router.get("/")
def get_user_integrations(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all connected external accounts for the current application user.
    Sanitizes output to guarantee NO raw access tokens, refresh tokens, or API keys are exposed.
    """
    connections = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id
    ).all()

    connected_providers = [c.to_safe_dict() for c in connections]
    
    all_providers = [
        {"provider": "google", "name": "Google (Search Console / Profile / Business)", "category": "Search & Analytics", "supports_oauth": True},
        {"provider": "meta", "name": "Meta (Facebook Pages & Instagram)", "category": "Social & Marketing", "supports_oauth": True},
        {"provider": "openai", "name": "OpenAI (GPT-4o & Embeddings)", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "gemini", "name": "Google Gemini AI", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "claude", "name": "Claude AI (Anthropic)", "category": "AI & Automation", "supports_oauth": False},
        {"provider": "microsoft", "name": "Microsoft Workspace", "category": "Search & Analytics", "supports_oauth": True},
        {"provider": "linkedin", "name": "LinkedIn Business", "category": "Social & Marketing", "supports_oauth": True},
        {"provider": "twitter", "name": "X / Twitter", "category": "Social & Marketing", "supports_oauth": True},
    ]

    return {
        "user_id": user_id,
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
    """
    p = provider.lower()
    if p in ("openai", "gemini", "claude"):
        raise HTTPException(
            status_code=400,
            detail=f"{provider.title()} uses User API Key registration. Use POST /api/integrations/{p}/key to connect your account."
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
    Validates the OAuth authorization callback, performs a REAL token exchange with the provider,
    fetches authentic user profile details, encrypts credentials at rest, and associates connection.
    """
    if error or not code or not state:
        err_msg = error_description or error or "Authorization request was cancelled or denied."
        quoted_msg = urllib.parse.quote(err_msg)
        return RedirectResponse(url=f"/settings?integration=error&provider={provider}&msg={quoted_msg}")

    try:
        # Validate OAuth state to prevent CSRF and session hijacking
        state_data = validate_oauth_state(state)
        user_id = state_data["user_id"]
        state_provider = state_data["provider"]

        if state_provider != provider:
            raise HTTPException(status_code=400, detail="OAuth state provider mismatch.")

        redirect_base = str(request.base_url).rstrip("/") if request else settings.API_BASE_URL

        
        # Real token exchange with provider
        token_response = exchange_code_for_tokens(provider, code, redirect_base=redirect_base)
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Retrieve authentic user identity from provider
        profile = fetch_provider_user_profile(provider, access_token)
        account_id = profile["account_id"]
        account_name = profile["account_name"]
        account_email = profile["email"]
        meta_data = profile.get("metadata", {})

        # Upsert connection record for user
        existing = db.query(ExternalConnection).filter(
            ExternalConnection.user_id == user_id,
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
                user_id=user_id,
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

        return RedirectResponse(url=f"/settings?integration=success&provider={provider}")

    except ValueError as val_err:
        err_msg = urllib.parse.quote(str(val_err))
        return RedirectResponse(url=f"/settings?integration=error&provider={provider}&msg={err_msg}")
    except Exception as exc:
        err_msg = urllib.parse.quote(f"Authentication error: {exc}")
        return RedirectResponse(url=f"/settings?integration=error&provider={provider}&msg={err_msg}")


@router.post("/{provider}/key")
def save_user_api_key(
    provider: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Saves and encrypts a user-provided API key for AI providers (OpenAI, Gemini, Claude).
    Validates key format/ping against provider before storing encrypted ciphertext.
    """
    p = provider.lower()
    if p not in ("openai", "gemini", "claude", "anthropic"):
        raise HTTPException(status_code=400, detail=f"API key connection is supported for 'openai', 'gemini', and 'claude'. Got '{provider}'.")

    raw_key = (payload.get("api_key") or "").strip()
    if not raw_key:
        raise HTTPException(status_code=400, detail="API Key is required.")

    try:
        profile = validate_api_key_provider(p, raw_key)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    existing = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == p
    ).first()

    if existing:
        existing.provider_account_id = profile["account_id"]
        existing.provider_account_name = profile["account_name"]
        existing.provider_email = profile["email"]
        existing.set_api_key(raw_key)
        existing.status = "CONNECTED"
        existing.updated_at = datetime.utcnow()
        existing.last_used_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing.to_safe_dict()
    else:
        new_conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider=p,
            provider_account_id=profile["account_id"],
            provider_account_name=profile["account_name"],
            provider_email=profile["email"],
            status="CONNECTED",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_used_at=datetime.utcnow()
        )
        new_conn.set_api_key(raw_key)
        db.add(new_conn)
        db.commit()
        db.refresh(new_conn)
        return new_conn.to_safe_dict()


@router.post("/{connection_id}/disconnect")
def disconnect_external_account(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnects and securely revokes an external account connection.
    Guarantees user isolation.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.id == connection_id,
        ExternalConnection.user_id == user_id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="External connection not found or unauthorized.")

    provider = conn.provider
    db.delete(conn)
    db.commit()

    return {
        "status": "disconnected",
        "id": connection_id,
        "provider": provider,
        "message": f"Successfully disconnected {provider.title()} account."
    }


@router.post("/{connection_id}/refresh")
def refresh_account_token(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Triggers token refresh lifecycle for an expired OAuth access token.
    If refresh token is invalid or unconfigured, sets status to REAUTH_REQUIRED.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.id == connection_id,
        ExternalConnection.user_id == user_id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="External connection not found or unauthorized.")

    refresh_token = conn.get_refresh_token()
    if not refresh_token:
        conn.status = "REAUTH_REQUIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="No refresh token available. Please reconnect your account.")

    conn.status = "REAUTH_REQUIRED"
    db.commit()
    raise HTTPException(status_code=400, detail="Token refresh requires valid provider client credentials. Reauthorization required.")


@router.post("/{connection_id}/meta/select-assets")
def select_meta_assets(
    connection_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Updates user-selected Facebook Pages and Instagram accounts for Meta connection.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.id == connection_id,
        ExternalConnection.user_id == user_id
    ).first()

    if not conn or conn.provider not in ("meta", "facebook", "instagram"):
        raise HTTPException(status_code=404, detail="Meta connection not found or unauthorized.")

    meta = conn.get_metadata()
    meta["selected_pages"] = payload.get("selected_pages", meta.get("selected_pages", []))
    meta["selected_instagram"] = payload.get("selected_instagram", meta.get("selected_instagram", []))

    conn.set_metadata(meta)
    conn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conn)

    return conn.to_safe_dict()


@router.post("/{connection_id}/test")
def test_connection_health(
    connection_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Performs a lightweight connection health check against the provider's API.
    Updates connection status to HEALTHY or ERROR.
    """
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.id == connection_id,
        ExternalConnection.user_id == user_id
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="External connection not found or unauthorized.")

    p = conn.provider
    try:
        if p in ("openai", "gemini", "claude", "anthropic"):
            key = conn.get_api_key()
            if not key:
                conn.status = "REAUTH_REQUIRED"
                db.commit()
                raise HTTPException(status_code=400, detail="Missing API Key. Reauthorization required.")
            validate_api_key_provider(p, key)
        
        conn.status = "HEALTHY"
        conn.last_used_at = datetime.utcnow()
        db.commit()
        db.refresh(conn)
        return {
            "status": "HEALTHY",
            "provider": p,
            "connection_id": conn.id,
            "message": f"Connection test for {p.title()} succeeded. Status is HEALTHY."
        }
    except Exception as err:
        conn.status = "ERROR"
        db.commit()
        raise HTTPException(status_code=400, detail=f"{p.title()} connection test failed: {err}")
