from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
import uuid
from app.config.database import Base

class PlatformEvent(Base):
    __tablename__ = "platform_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, nullable=True, index=True)
    project_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, default="info", index=True) # info, warning, critical
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        import json
        parsed_meta = None
        if self.metadata_json:
            try:
                parsed_meta = json.loads(self.metadata_json)
            except Exception:
                parsed_meta = self.metadata_json

        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "metadata": parsed_meta,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
