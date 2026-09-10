from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime
import uuid
from app.config.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    actor_id = Column(String, nullable=False, index=True)
    actor_email = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False, index=True) # e.g. USER_STATUS_CHANGE, ROLE_CHANGE, MASTER_ACCESS
    target_type = Column(String, nullable=True, index=True) # e.g. user, project, system, provider
    target_id = Column(String, nullable=True, index=True)
    status = Column(String, default="SUCCESS", index=True) # SUCCESS, FAILED, DENIED
    reason = Column(Text, nullable=True)
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
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "status": self.status,
            "reason": self.reason,
            "metadata": parsed_meta,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
