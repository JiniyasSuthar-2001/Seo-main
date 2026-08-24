from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime, timedelta
import uuid
from app.config.database import Base

class ProjectInvitation(Base):
    __tablename__ = "project_invitations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    invited_email = Column(String, index=True)
    invited_by_user_id = Column(String)
    role = Column(String, default="MEMBER")
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, EXPIRED, REVOKED
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        masked = self.invited_email[0] + "***" + self.invited_email[self.invited_email.find("@"):] if "@" in self.invited_email else "user***@gmail.com"
        return {
            "id": self.id,
            "project_id": self.project_id,
            "invited_email": self.invited_email,
            "masked_email": masked,
            "invited_by_user_id": self.invited_by_user_id,
            "role": self.role,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
