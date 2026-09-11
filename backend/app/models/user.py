from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.config.database import Base

class AccountStatus:
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
    INACTIVE = "INACTIVE"

    CANONICAL_SET = {ACTIVE, SUSPENDED, DISABLED, INACTIVE}
    BLOCKED_SET = {SUSPENDED, DISABLED, INACTIVE}

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # Google Email or User ID
    google_id = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    picture = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    platform_role = Column(String, default="USER", nullable=True, index=True) # SUPER_ADMIN, ADMIN, SUPPORT, ANALYST, USER
    status = Column(String, default="ACTIVE", nullable=True, index=True) # ACTIVE, SUSPENDED, INACTIVE
    permissions_json = Column(String, default="[]", nullable=True) # JSON array of permission strings or '["*"]'
    created_by = Column(String, nullable=True) # Creator admin user ID
    last_login_at = Column(DateTime, nullable=True)
    disabled_at = Column(DateTime, nullable=True)
    disabled_by = Column(String, nullable=True)
    session_revoked_at = Column(DateTime, nullable=True) # Used to invalidate JWTs issued before this time
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_permissions_list(self):
        import json
        if not self.permissions_json:
            return ["*"] if (self.platform_role or "").upper() in ("SUPER_MASTER", "SUPER_ADMIN") else []
        try:
            val = json.loads(self.permissions_json)
            if isinstance(val, list):
                return val
            return [str(val)]
        except Exception:
            return ["*"] if (self.platform_role or "").upper() in ("SUPER_MASTER", "SUPER_ADMIN") else []

    def to_dict(self):
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "masked_email": self.email,
            "name": self.name,
            "picture": self.picture,
            "has_password": bool(self.password_hash),
            "platform_role": (self.platform_role or "USER").upper(),
            "status": (self.status or "ACTIVE").upper(),
            "permissions": self.get_permissions_list(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def to_master_dict(self):
        """Safe representation for Master Account management table - NEVER includes password hashes"""
        return {
            "id": self.id,
            "login_id": self.id,
            "email": self.email,
            "name": self.name or self.id,
            "role": (self.platform_role or "MASTER_ADMIN").upper(),
            "platform_role": (self.platform_role or "MASTER_ADMIN").upper(),
            "status": (self.status or "ACTIVE").upper(),
            "permissions": self.get_permissions_list(),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "disabled_at": self.disabled_at.isoformat() if self.disabled_at else None,
            "disabled_by": self.disabled_by
        }

