from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime, timedelta
import uuid
from app.config.database import Base

class ProjectInvitation(Base):
    __tablename__ = "project_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    invited_email = Column(String, index=True)
    invited_user_id = Column(String, nullable=True)
    invited_by_user_id = Column(String)
    role = Column(String, default="MEMBER")
    permissions_json = Column(String, nullable=True)
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, REJECTED, EXPIRED, CANCELLED
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "invited_email": self.invited_email,
            "invited_user_id": self.invited_user_id,
            "masked_email": self.invited_email,
            "invited_by_user_id": self.invited_by_user_id,
            "role": self.role,
            "permissions_json": self.permissions_json,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None
        }
