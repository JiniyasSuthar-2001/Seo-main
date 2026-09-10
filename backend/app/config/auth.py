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

MASTER_ROLES = {"SUPER_ADMIN", "ADMIN", "SUPPORT", "ANALYST"}

def require_master_user(allowed_roles: Optional[set] = None):
    """
    Returns a FastAPI dependency that verifies the authenticated user has an authorized platform master role.
    Raises HTTP 403 Forbidden for unauthorized users.
    Auto-promotes initial user to SUPER_ADMIN if no master user exists.
    """
    roles_check = allowed_roles or MASTER_ROLES

    def dependency(
        authorization: Optional[str] = Header(None),
        x_user_id: Optional[str] = Header(None)
    ):
        user_id = get_current_user_id(authorization=authorization, x_user_id=x_user_id)
        from app.config.database import SessionLocal
        from app.models.user import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user_count = db.query(User).count()
                role = "SUPER_ADMIN" if user_count == 0 else "USER"
                user = User(
                    id=user_id,
                    email=user_id if "@" in user_id else f"{user_id}@example.com",
                    name=user_id,
                    platform_role=role,
                    status="ACTIVE"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            # Auto-promote single user to SUPER_ADMIN if no admin exists yet
            if not user.platform_role or user.platform_role == "USER":
                admin_count = db.query(User).filter(User.platform_role.in_(list(MASTER_ROLES))).count()
                if admin_count == 0:
                    user.platform_role = "SUPER_ADMIN"
                    db.commit()
                    db.refresh(user)

            current_role = (user.platform_role or "USER").upper()
            if current_role not in roles_check:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Master space requires authorized role ({', '.join(sorted(roles_check))})."
                )

            if user.status and user.status.upper() == "SUSPENDED":
                raise HTTPException(
                    status_code=403,
                    detail="Account is suspended. Please contact platform administration."
                )

            return user
        finally:
            db.close()

    return dependency

