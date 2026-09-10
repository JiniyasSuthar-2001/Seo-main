import json
import logging
from datetime import datetime, time
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.ai_wallet import AIWallet, AICreditTransaction, PlatformAISettings
from app.models.user import User

logger = logging.getLogger(__name__)

class CreditTransactionType:
    ALLOCATION = "allocation"
    BONUS = "bonus"
    CONSUMPTION = "consumption"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    EXPIRATION = "expiration"
    RESET = "reset"

class CreditService:

    @classmethod
    def get_customer_id_for_user(cls, db: Session, user_id: Optional[str]) -> str:
        if not user_id:
            return "default_guest"
        user = db.query(User).filter(User.id == user_id).first()
        return user.id if user else user_id

    @classmethod
    def get_or_create_platform_settings(cls, db: Session) -> PlatformAISettings:
        settings = db.query(PlatformAISettings).filter(PlatformAISettings.id == "default").first()
        if not settings:
            settings = PlatformAISettings(id="default")
            db.add(settings)
            try:
                db.commit()
                db.refresh(settings)
            except Exception:
                db.rollback()
                settings = db.query(PlatformAISettings).filter(PlatformAISettings.id == "default").first()
        return settings

    @classmethod
    def get_or_create_wallet(cls, customer_id: str, db: Session) -> AIWallet:
        if not customer_id:
            customer_id = "default_guest"

        wallet = db.query(AIWallet).filter(AIWallet.customer_id == customer_id).first()
        if not wallet:
            wallet = AIWallet(
                customer_id=customer_id,
                allocated_credits=50000,
                bonus_credits=0,
                used_credits=0,
                reserved_credits=0,
                monthly_limit=50000,
                daily_limit=5000,
                per_request_limit=1000,
                is_enabled=True,
                status="ACTIVE"
            )
            db.add(wallet)
            try:
                db.commit()
                db.refresh(wallet)
                # Create initial allocation transaction
                tx = AICreditTransaction(
                    wallet_id=wallet.id,
                    customer_id=customer_id,
                    amount=50000,
                    transaction_type=CreditTransactionType.ALLOCATION,
                    reference_type="plan_allocation",
                    reason="Initial account allocation",
                    balance_after=50000
                )
                db.add(tx)
                db.commit()
            except Exception:
                db.rollback()
                wallet = db.query(AIWallet).filter(AIWallet.customer_id == customer_id).first()

        return wallet

    @classmethod
    def check_ai_authorization(
        cls,
        customer_id: Optional[str],
        task_type: str = "page_solution",
        estimated_credits: int = 1,
        is_background: bool = False,
        is_report: bool = False,
        db: Session = None
    ) -> AIWallet:
        if not db:
            return None

        # 1. Global Platform AI Kill Switch & Feature Flags
        platform_settings = cls.get_or_create_platform_settings(db)
        if not platform_settings.global_ai_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI_DISABLED_GLOBALLY: Platform AI capabilities are currently disabled by administrator."
            )

        if not platform_settings.new_requests_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI_NEW_REQUESTS_PAUSED: New AI requests are temporarily paused across the platform."
            )

        if is_background and not platform_settings.background_ai_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI_BACKGROUND_PAUSED: Background AI processing is currently paused."
            )

        if is_report and not platform_settings.ai_reports_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI_REPORTS_PAUSED: AI enrichment for report downloads is currently paused."
            )

        # 2. Customer Wallet Authorization
        cid = customer_id or "default_guest"
        wallet = cls.get_or_create_wallet(cid, db)

        if not wallet.is_enabled or (wallet.status and wallet.status.upper() in ("DISABLED", "PAUSED")):
            raise HTTPException(
                status_code=403,
                detail=f"AI_DISABLED_FOR_CUSTOMER: AI capabilities have been disabled/paused for customer account ({cid})."
            )

        # 3. Per-Request Limit
        if wallet.per_request_limit and estimated_credits > wallet.per_request_limit:
            raise HTTPException(
                status_code=400,
                detail=f"PER_REQUEST_LIMIT_EXCEEDED: Requested {estimated_credits} credits exceeds per-request limit ({wallet.per_request_limit})."
            )

        # 4. Remaining Balance Check
        if wallet.remaining_credits < estimated_credits:
            wallet.status = "EXHAUSTED"
            db.commit()
            raise HTTPException(
                status_code=402,
                detail=f"INSUFFICIENT_CREDITS: Customer has {wallet.remaining_credits} credits remaining, required {estimated_credits}."
            )

        # 5. Daily Limit Check
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        daily_used_query = db.query(func.sum(AICreditTransaction.amount)).filter(
            and_(
                AICreditTransaction.customer_id == cid,
                AICreditTransaction.transaction_type == CreditTransactionType.CONSUMPTION,
                AICreditTransaction.created_at >= today_start
            )
        ).scalar()
        daily_used = abs(daily_used_query or 0)

        if wallet.daily_limit and (daily_used + estimated_credits > wallet.daily_limit):
            raise HTTPException(
                status_code=429,
                detail=f"DAILY_LIMIT_EXCEEDED: Daily usage ({daily_used} credits) plus request ({estimated_credits}) exceeds daily limit ({wallet.daily_limit})."
            )

        # 6. Monthly Limit Check
        month_start = datetime(now.year, now.month, 1)
        monthly_used_query = db.query(func.sum(AICreditTransaction.amount)).filter(
            and_(
                AICreditTransaction.customer_id == cid,
                AICreditTransaction.transaction_type == CreditTransactionType.CONSUMPTION,
                AICreditTransaction.created_at >= month_start
            )
        ).scalar()
        monthly_used = abs(monthly_used_query or 0)

        if wallet.monthly_limit and (monthly_used + estimated_credits > wallet.monthly_limit):
            raise HTTPException(
                status_code=429,
                detail=f"MONTHLY_LIMIT_EXCEEDED: Monthly usage ({monthly_used} credits) exceeds monthly limit ({wallet.monthly_limit})."
            )

        return wallet

    @classmethod
    def allocate_credits(
        cls,
        customer_id: str,
        amount: int,
        transaction_type: str = CreditTransactionType.ALLOCATION,
        reason: str = "Admin allocation",
        actor_user_id: Optional[str] = None,
        reference_id: Optional[str] = None,
        db: Session = None
    ) -> AICreditTransaction:
        if not db:
            return None

        if not reason or not str(reason).strip():
            raise HTTPException(status_code=400, detail="A valid reason is required for manual credit operations.")

        tx_type = (transaction_type or "allocation").lower().strip()
        wallet = cls.get_or_create_wallet(customer_id, db)

        if tx_type == CreditTransactionType.BONUS:
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Bonus credit amount must be positive.")
            wallet.bonus_credits = (wallet.bonus_credits or 0) + amount
        elif tx_type == CreditTransactionType.ADJUSTMENT:
            if amount == 0:
                raise HTTPException(status_code=400, detail="Adjustment amount cannot be zero.")
            # Positive adjustment increases allocated_credits, negative adjustment safely decreases balance
            if amount > 0:
                wallet.allocated_credits = (wallet.allocated_credits or 0) + amount
            else:
                wallet.allocated_credits = max(0, (wallet.allocated_credits or 0) + amount)
        elif tx_type == CreditTransactionType.RESET:
            wallet.used_credits = 0
            wallet.reserved_credits = 0
            if amount > 0:
                wallet.allocated_credits = amount
        else: # allocation
            if amount <= 0:
                raise HTTPException(status_code=400, detail="Allocation credit amount must be positive.")
            wallet.allocated_credits = (wallet.allocated_credits or 0) + amount

        wallet.updated_at = datetime.utcnow()
        if wallet.remaining_credits > 0 and wallet.status == "EXHAUSTED":
            wallet.status = "ACTIVE"

        db.commit()
        db.refresh(wallet)

        tx = AICreditTransaction(
            wallet_id=wallet.id,
            customer_id=customer_id,
            amount=amount,
            transaction_type=tx_type,
            reference_type="admin_adjustment",
            reference_id=reference_id,
            reason=reason.strip(),
            actor_user_id=actor_user_id,
            balance_after=wallet.remaining_credits
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @classmethod
    def deduct_credits(
        cls,
        customer_id: str,
        amount: int,
        reference_id: Optional[str] = None,
        reason: str = "AI request completion",
        db: Session = None
    ) -> AICreditTransaction:
        if not db or amount <= 0:
            return None

        cid = customer_id or "default_guest"

        # 1. Idempotency Check: Prevent duplicate credit deductions for the same reference_id
        if reference_id:
            existing_tx = db.query(AICreditTransaction).filter(
                and_(
                    AICreditTransaction.customer_id == cid,
                    AICreditTransaction.reference_id == reference_id,
                    AICreditTransaction.transaction_type == CreditTransactionType.CONSUMPTION
                )
            ).first()
            if existing_tx:
                logger.info(f"[CreditService] Idempotent deduction returned for reference_id={reference_id}")
                return existing_tx

        # 2. Concurrency Protection & Atomic Deduction Check
        wallet = cls.get_or_create_wallet(cid, db)

        # Ensure wallet has sufficient credits at the moment of deduction
        if wallet.remaining_credits < amount:
            wallet.status = "EXHAUSTED"
            db.commit()
            raise HTTPException(
                status_code=402,
                detail=f"INSUFFICIENT_CREDITS: Cannot deduct {amount} credits. Remaining: {wallet.remaining_credits}."
            )

        wallet.used_credits = (wallet.used_credits or 0) + amount
        wallet.updated_at = datetime.utcnow()
        if wallet.remaining_credits <= 0:
            wallet.status = "EXHAUSTED"

        db.commit()
        db.refresh(wallet)

        tx = AICreditTransaction(
            wallet_id=wallet.id,
            customer_id=cid,
            amount=-amount,
            transaction_type=CreditTransactionType.CONSUMPTION,
            reference_type="ai_usage_log",
            reference_id=reference_id,
            reason=reason,
            balance_after=wallet.remaining_credits
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @classmethod
    def refund_credits(
        cls,
        customer_id: str,
        amount: int,
        reference_id: Optional[str] = None,
        reason: str = "AI request refund",
        actor_user_id: Optional[str] = None,
        db: Session = None
    ) -> AICreditTransaction:
        if not db or amount <= 0:
            return None

        cid = customer_id or "default_guest"

        # Append-only Compensating ledger transaction
        wallet = cls.get_or_create_wallet(cid, db)

        wallet.used_credits = max(0, (wallet.used_credits or 0) - amount)
        wallet.updated_at = datetime.utcnow()
        if wallet.remaining_credits > 0 and wallet.status == "EXHAUSTED":
            wallet.status = "ACTIVE"

        db.commit()
        db.refresh(wallet)

        tx = AICreditTransaction(
            wallet_id=wallet.id,
            customer_id=cid,
            amount=amount,
            transaction_type=CreditTransactionType.REFUND,
            reference_type="retry_refund" if reference_id else "manual_refund",
            reference_id=reference_id,
            reason=reason or "Compensating refund",
            actor_user_id=actor_user_id,
            balance_after=wallet.remaining_credits
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx

    @classmethod
    def deduct_ai_credits(cls, customer_id: str, amount: int = 1, reference_id: Optional[str] = None, reason: str = "AI request completion", task_type: str = "ai_request", db: Session = None) -> AICreditTransaction:
        return cls.deduct_credits(customer_id=customer_id, amount=amount, reference_id=reference_id, reason=reason, db=db)

    @classmethod
    def refund_ai_credits(cls, customer_id: str, amount: int = 1, reference_id: Optional[str] = None, reason: str = "AI request refund", db: Session = None) -> AICreditTransaction:
        return cls.refund_credits(customer_id=customer_id, amount=amount, reference_id=reference_id, reason=reason, db=db)

    @classmethod
    def update_customer_ai_settings(
        cls,
        customer_id: str,
        is_enabled: Optional[bool] = None,
        monthly_limit: Optional[int] = None,
        daily_limit: Optional[int] = None,
        per_request_limit: Optional[int] = None,
        status: Optional[str] = None,
        db: Session = None
    ) -> AIWallet:
        wallet = cls.get_or_create_wallet(customer_id, db)
        if is_enabled is not None:
            wallet.is_enabled = is_enabled
        if monthly_limit is not None:
            wallet.monthly_limit = monthly_limit
        if daily_limit is not None:
            wallet.daily_limit = daily_limit
        if per_request_limit is not None:
            wallet.per_request_limit = per_request_limit
        if status:
            wallet.status = status.upper()

        wallet.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(wallet)
        return wallet
