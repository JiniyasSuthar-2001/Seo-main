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
    Enforces account suspension check: Suspended users are immediately rejected across all endpoints with 403.
    """
    resolved_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            payload = decode_access_token(token)
            resolved_id = payload.get("sub")

    if not resolved_id:
        clean_header_user = (x_user_id or "").strip()
        if clean_header_user and clean_header_user not in ("undefined", "null") and is_dev_user_header_allowed():
            resolved_id = clean_header_user

    if not resolved_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid Authorization Bearer token."
        )

    # Database account status check
    from app.config.database import SessionLocal
    from app.models.user import User
    db = SessionLocal()
    try:
        user = db.query(User).filter((User.id == resolved_id) | (User.email == resolved_id)).first()
        if user and user.status and user.status.upper() == "SUSPENDED":
            raise HTTPException(
                status_code=403,
                detail="ACCOUNT_SUSPENDED: Your customer account is currently suspended. Please contact platform administration."
            )
    finally:
        db.close()

    return resolved_id

MASTER_ROLES = {"SUPER_MASTER", "MASTER_ADMIN", "SUPER_ADMIN", "ADMIN", "SUPPORT", "ANALYST"}

def ensure_root_super_master():
    """
    Guarantees the authoritative root Super Master account exists in the database with secure bcrypt hash.
    Seeds from environment configuration or default initial root credentials.
    """
    try:
        from app.config.database import SessionLocal
        from app.models.user import User
        from app.config.security import get_password_hash
        import json

        db = SessionLocal()
        try:
            root_id = (os.environ.get("MASTER_ADMIN_ID") or "Kirito@420").strip()
            root_pass = os.environ.get("MASTER_ADMIN_PASSWORD") or "Uis001Digital"
            root_email = root_id.lower() if "@" in root_id else f"{root_id.lower()}@master.local"

            existing = db.query(User).filter(
                (User.id == root_id) | (User.email == root_id) | (User.email == root_email) | (User.id == root_email)
            ).first()

            if not existing:
                print(f"[MASTER AUTH] Provisioning authoritative root Super Master account '{root_id}'...", flush=True)
                new_master = User(
                    id=root_id,
                    email=root_email,
                    name="Root Super Master",
                    password_hash=get_password_hash(root_pass),
                    platform_role="SUPER_MASTER",
                    status="ACTIVE",
                    permissions_json=json.dumps(["*"]),
                    created_by="SYSTEM_BOOTSTRAP"
                )
                db.add(new_master)
                db.commit()
                print(f"[MASTER AUTH] Root Super Master provisioned successfully.", flush=True)
            else:
                # Ensure existing account is SUPER_MASTER, ACTIVE, and has full permissions
                modified = False
                if existing.platform_role != "SUPER_MASTER":
                    existing.platform_role = "SUPER_MASTER"
                    modified = True
                if existing.status != "ACTIVE":
                    existing.status = "ACTIVE"
                    modified = True
                if not existing.password_hash:
                    existing.password_hash = get_password_hash(root_pass)
                    modified = True
                if existing.permissions_json != json.dumps(["*"]):
                    existing.permissions_json = json.dumps(["*"])
                    modified = True
                if modified:
                    db.commit()
                    print(f"[MASTER AUTH] Authoritative root Super Master account updated.", flush=True)
        finally:
            db.close()
    except Exception as e:
        print(f"[MASTER AUTH ERROR] Failed to bootstrap root Super Master: {e}", flush=True)

def require_master_user(required_permission: Optional[str] = None):
    """
    Returns a FastAPI dependency that verifies the authenticated user has an authoritative platform master role
    and holds the specified Master permission.
    Strictly checks database platform_role, active status, session revocation, and permission matrix.
    Raises HTTP 403 Forbidden for unauthorized or disabled users.
    """
    def dependency(
        authorization: Optional[str] = Header(None),
        x_user_id: Optional[str] = Header(None)
    ):
        token_iat = None
        resolved_id = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1].strip()
            if token:
                payload = decode_access_token(token)
                resolved_id = payload.get("sub")
                token_iat = payload.get("iat")

        if not resolved_id:
            clean_header_user = (x_user_id or "").strip()
            if clean_header_user and clean_header_user not in ("undefined", "null") and is_dev_user_header_allowed():
                resolved_id = clean_header_user

        if not resolved_id:
            raise HTTPException(
                status_code=401,
                detail="Master authentication required. Please provide a valid Authorization Bearer token."
            )

        from app.config.database import SessionLocal
        from app.models.user import User
        from app.config.master_permissions import user_has_master_permission

        db = SessionLocal()
        try:
            user = db.query(User).filter(
                (User.id == resolved_id) | (User.email == resolved_id) | (User.id == resolved_id.lower()) | (User.email == resolved_id.lower())
            ).first()

            if not user:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. Master account record not found."
                )

            user_status = (user.status or "ACTIVE").upper()
            if user_status in ("SUSPENDED", "DISABLED", "INACTIVE"):
                raise HTTPException(
                    status_code=403,
                    detail=f"ACCOUNT_{user_status}: This Master account has been {user_status.lower()} by platform administration."
                )

            # Check if active session was revoked
            if user.session_revoked_at and token_iat:
                revoked_ts = int(user.session_revoked_at.timestamp())
                if token_iat < revoked_ts:
                    raise HTTPException(
                        status_code=401,
                        detail="SESSION_REVOKED: This Master session has been revoked. Please sign in again."
                    )

            current_role = (user.platform_role or "USER").upper()
            if current_role not in MASTER_ROLES:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Master space requires authorized administrative role."
                )

            # Check granular permission if required
            if required_permission:
                has_perm = user_has_master_permission(
                    user_role=current_role,
                    user_permissions=user.get_permissions_list(),
                    required_permission=required_permission
                )
                if not has_perm:
                    raise HTTPException(
                        status_code=403,
                        detail=f"PERMISSION_DENIED: You do not have the required '{required_permission}' permission."
                    )

            return user
        finally:
            db.close()

    return dependency


