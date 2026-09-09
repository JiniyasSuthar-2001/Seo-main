import os
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.ai_usage_log import AIUsageLog

class AIUsageService:
    """
    Tracks and enforces AI page consumption limits independently from crawl page counts.
    Ensures that crawls and deterministic SEO analysis NEVER consume AI page allowance,
    and only real, successful AI solution requests against specific pages consume credits.
    """
    DEFAULT_MONTHLY_AI_PAGE_LIMIT = 500

    @classmethod
    def get_user_usage_count(cls, user_id: str, db: Session) -> int:
        if not user_id or not db:
            return 0
        try:
            return db.query(AIUsageLog).filter(
                AIUsageLog.user_id == user_id,
                AIUsageLog.status == "success"
            ).count()
        except Exception:
            return 0

    @classmethod
    def can_consume_ai_page(cls, user_id: Optional[str], db: Optional[Session], limit: int = DEFAULT_MONTHLY_AI_PAGE_LIMIT) -> bool:
        if not user_id or not db:
            return True # Allow default fallback if no explicit user tracking
        usage = cls.get_user_usage_count(user_id, db)
        return usage < limit

    @classmethod
    def record_ai_usage(
        cls,
        user_id: Optional[str],
        project_id: Optional[str],
        crawl_id: Optional[str],
        page_url: Optional[str],
        task_type: str = "page_solution",
        model: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        units_consumed: int = 1,
        status: str = "success",
        error_message: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Optional[AIUsageLog]:
        if not db:
            return None
        try:
            log_entry = AIUsageLog(
                user_id=user_id,
                project_id=project_id,
                crawl_id=crawl_id,
                page_url=page_url,
                task_type=task_type,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                units_consumed=units_consumed,
                status=status,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            return log_entry
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[AI USAGE SERVICE] Failed to record usage log: {e}", flush=True)
            return None
