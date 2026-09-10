from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
import uuid
from app.config.database import Base

class AIWallet(Base):
    __tablename__ = "ai_wallets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    customer_id = Column(String, unique=True, nullable=False, index=True) # User ID / Customer ID
    allocated_credits = Column(Integer, default=50000)
    bonus_credits = Column(Integer, default=0)
    used_credits = Column(Integer, default=0)
    reserved_credits = Column(Integer, default=0)
    monthly_limit = Column(Integer, default=50000)
    daily_limit = Column(Integer, default=5000)
    per_request_limit = Column(Integer, default=1000)
    is_enabled = Column(Boolean, default=True) # Customer AI Kill Switch
    status = Column(String, default="ACTIVE", index=True) # ACTIVE, PAUSED, DISABLED, EXHAUSTED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def total_allocated(self) -> int:
        return (self.allocated_credits or 0) + (self.bonus_credits or 0)

    @property
    def remaining_credits(self) -> int:
        return max(0, self.total_allocated - (self.used_credits or 0) - (self.reserved_credits or 0))

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "allocated_credits": self.allocated_credits,
            "bonus_credits": self.bonus_credits,
            "total_allocated": self.total_allocated,
            "used_credits": self.used_credits,
            "reserved_credits": self.reserved_credits,
            "remaining_credits": self.remaining_credits,
            "monthly_limit": self.monthly_limit,
            "daily_limit": self.daily_limit,
            "per_request_limit": self.per_request_limit,
            "is_enabled": self.is_enabled,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AICreditTransaction(Base):
    __tablename__ = "ai_credit_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    wallet_id = Column(String, ForeignKey("ai_wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False) # Positive for additions/refunds, negative for deductions
    transaction_type = Column(String, nullable=False, index=True) # allocation, consumption, refund, bonus, adjustment, expiration, reset
    reference_type = Column(String, nullable=True) # ai_usage_log, admin_adjustment, plan_allocation, retry_refund
    reference_id = Column(String, nullable=True, index=True)
    reason = Column(Text, nullable=True)
    actor_user_id = Column(String, nullable=True) # Admin ID or system
    balance_after = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "reason": self.reason,
            "actor_user_id": self.actor_user_id,
            "balance_after": self.balance_after,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PlatformAISettings(Base):
    __tablename__ = "platform_ai_settings"

    id = Column(String, primary_key=True, default="default")
    global_ai_enabled = Column(Boolean, default=True) # Global Master AI Kill Switch
    new_requests_enabled = Column(Boolean, default=True)
    background_ai_enabled = Column(Boolean, default=True)
    ai_reports_enabled = Column(Boolean, default=True)
    primary_provider = Column(String, default="gemini")
    fallback_provider = Column(String, default="ollama")
    routing_mode = Column(String, default="primary_fallback") # primary_fallback, cost_optimized, task_routed
    daily_budget_dollars = Column(Float, default=100.0)
    monthly_budget_dollars = Column(Float, default=2500.0)
    budget_warning_threshold = Column(Float, default=80.0) # 80%
    budget_critical_threshold = Column(Float, default=90.0) # 90%
    budget_hard_stop = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def daily_budget_usd(self) -> float:
        return self.daily_budget_dollars or 100.0

    @daily_budget_usd.setter
    def daily_budget_usd(self, value: float):
        self.daily_budget_dollars = value

    @property
    def monthly_budget_usd(self) -> float:
        return self.monthly_budget_dollars or 2500.0

    @monthly_budget_usd.setter
    def monthly_budget_usd(self, value: float):
        self.monthly_budget_dollars = value

    def to_dict(self):
        return {
            "id": self.id,
            "global_ai_enabled": self.global_ai_enabled,
            "new_requests_enabled": self.new_requests_enabled,
            "background_ai_enabled": self.background_ai_enabled,
            "ai_reports_enabled": self.ai_reports_enabled,
            "primary_provider": self.primary_provider,
            "fallback_provider": self.fallback_provider,
            "routing_mode": self.routing_mode,
            "daily_budget_dollars": self.daily_budget_dollars,
            "monthly_budget_dollars": self.monthly_budget_dollars,
            "budget_warning_threshold": self.budget_warning_threshold,
            "budget_critical_threshold": self.budget_critical_threshold,
            "budget_hard_stop": self.budget_hard_stop,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
