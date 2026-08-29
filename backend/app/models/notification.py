from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
import json
from app.config.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    invitation_id = Column(String, ForeignKey("project_invitations.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String)
    message = Column(String)
    type = Column(String, default="TEAM_INVITATION") # TEAM_INVITATION, SYSTEM, ALERT
    status = Column(String, default="UNREAD") # UNREAD, READ, ARCHIVED
    data_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    def to_dict(self):
        parsed_data = {}
        if self.data_json:
            try:
                parsed_data = json.loads(self.data_json)
            except Exception:
                parsed_data = {}

        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "invitation_id": self.invitation_id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "status": self.status,
            "is_read": self.status == "READ",
            "data": parsed_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }
