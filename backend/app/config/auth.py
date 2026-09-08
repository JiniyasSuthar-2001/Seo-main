"""
Authentication and JWT token management module.
Enforces cryptographically signed JWT sessions with configurable expiration.
Strictly prevents X-User-ID header authentication bypass in production environments.
"""
import os
import time
import jwt
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from app.config.settings import settings

ALGORITHM = "HS256"
DEFAULT_EXPIRE_SECONDS = 86400 * 7  # 7 days

def get_secret_key() -> str:
    """Returns configured SECRET_KEY for JWT signing. Raises RuntimeError if missing."""
    key = os.environ.get("SECRET_KEY") or settings.SECRET_KEY
    if not key or not key.strip():
        raise RuntimeError("CONFIGURATION ERROR: Missing required 'SECRET_KEY' environment variable for authentication.")
    return key.strip()

def create_access_token(user_id: str, extra_claims: Optional[Dict[str, Any]] = None, expires_in: int = DEFAULT_EXPIRE_SECONDS) -> str:
    """
    Generates a cryptographically signed JWT access token for the given user_id.
    """
    secret = get_secret_key()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expires_in
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT access token.
    Raises HTTPException 401 if invalid, expired, or tampered.
    """
    secret = get_secret_key()
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Authentication token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

def is_dev_user_header_allowed() -> bool:
    """
    Determines whether X-User-ID header authentication is permitted.
    STRICT SECURITY RULES:
    1. NEVER allowed in production (settings.is_production == True).
    2. Disabled by default in all environments.
    3. Requires explicit ALLOW_DEV_USER_HEADER=true in non-production environments.
    """
    env = (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or settings.ENVIRONMENT or "development").strip().lower()
    if env == "production" or settings.is_production:
        return False
    
    dev_flag = os.environ.get("ALLOW_DEV_USER_HEADER")
    if dev_flag is not None:
        return dev_flag.strip().lower() in ("true", "1")
    return getattr(settings, "ALLOW_DEV_USER_HEADER", False)

def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    FastAPI dependency that extracts and validates the authenticated application user ID.
    Primary authentication: Authorization: Bearer <token> header with cryptographically verified JWT.
    Development-only fallback: X-User-ID is only accepted when ALLOW_DEV_USER_HEADER=true and NOT in production.
    Raises HTTP 401 Unauthorized if no valid identity is present.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return user_id

    # Strictly gated development / test fallback
    clean_header_user = (x_user_id or "").strip()
    if clean_header_user and clean_header_user not in ("undefined", "null") and is_dev_user_header_allowed():
        return clean_header_user

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please provide a valid Authorization Bearer token."
    )
