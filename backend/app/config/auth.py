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

def get_current_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
) -> str:
    """
    FastAPI dependency that extracts and validates the authenticated application user ID.
    First checks Authorization: Bearer <token> header.
    Falls back to X-User-ID header if present (for local single-user desktop workflow / unit tests).
    Raises HTTP 401 Unauthorized if no valid identity is present.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                return user_id

    clean_header_user = (x_user_id or "").strip()
    if clean_header_user and clean_header_user != "undefined" and clean_header_user != "null":
        return clean_header_user

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please provide a valid Authorization Bearer token or authenticated user session."
    )
