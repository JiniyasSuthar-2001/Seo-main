from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.config.database import Base

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "masked_email": self.email,
            "name": self.name,
            "picture": self.picture,
            "has_password": bool(self.password_hash),
            "platform_role": self.platform_role or "USER",
            "status": self.status or "ACTIVE",
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

