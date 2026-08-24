from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
from app.config.database import Base

class ProjectMembership(Base):
    __tablename__ = "project_memberships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    role = Column(String, default="OWNER") # OWNER or MEMBER
    status = Column(String, default="ACTIVE") # ACTIVE or REVOKED
    invited_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "role": self.role,
            "status": self.status,
            "invited_by": self.invited_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
