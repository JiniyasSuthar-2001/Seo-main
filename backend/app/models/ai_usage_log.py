from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from datetime import datetime
import uuid
from app.config.database import Base

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String, nullable=True, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    crawl_id = Column(String, nullable=True, index=True)
    page_url = Column(String, nullable=True, index=True)
    task_type = Column(String, nullable=False, default="page_solution") # page_solution, problem_explanation, rewrite, code_fix
    model = Column(String, nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    units_consumed = Column(Integer, default=1) # 1 page credit per page-specific solution
    status = Column(String, default="success") # success, failed, limit_reached
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "crawl_id": self.crawl_id,
            "page_url": self.page_url,
            "task_type": self.task_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "units_consumed": self.units_consumed,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
