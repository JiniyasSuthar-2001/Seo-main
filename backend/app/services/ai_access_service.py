import logging
from datetime import datetime, time
from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.ai_wallet import AIWallet, AICreditTransaction, PlatformAISettings
from app.models.user import User, AccountStatus
from app.services.credit_service import CreditService, CreditTransactionType
from app.services.ai_usage_service import AIUsageService

logger = logging.getLogger(__name__)

class AIAccessService:
    """
    Centralized Authorization and Consumption Gate for Customer AI Services.
    Enforces:
    1. Customer Account Status (ACTIVE only)
    2. Global Master AI Controls (kill switches & feature flags)
    3. Customer AI Wallet Status (is_enabled, status)
    4. Per-Request Credit Limits
    5. Product / Plan Safety Page Allowance (can_consume_ai_page)
    6. Customer Daily Limits
    7. Customer Monthly Limits
    8. Available Credit Balance
    """

    @classmethod
    def check_authorization(
        cls,
        customer_id: Optional[str],
        db: Session,
        task_type: str = "ai_request",
        estimated_credits: int = 1,
        is_background: bool = False,
        is_report: bool = False
    ) -> Dict[str, Any]:
        if not db:
            raise HTTPException(status_code=500, detail="Database session required for AI authorization.")

        cid = customer_id or "default_guest"

        # 1. Customer Account Status Check
        user = db.query(User).filter((User.id == cid) | (User.email == cid)).first()
        if user and user.status and user.status.upper() in AccountStatus.BLOCKED_SET:
            st = user.status.upper()
            raise HTTPException(
                status_code=403,
                detail=f"ACCOUNT_{st}: Your customer account is currently {st.lower()}. Please contact platform administration."
            )

        # 2. Global Platform AI Kill Switch & Feature Flags
        platform_settings = CreditService.get_or_create_platform_settings(db)
        if not platform_settings.global_ai_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI services are temporarily unavailable."
            )

        if not platform_settings.new_requests_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI services are temporarily unavailable."
            )

        if is_background and not platform_settings.background_ai_enabled:
            raise HTTPException(
                status_code=403,
                detail="Background AI processing is temporarily unavailable."
            )

        if is_report and not platform_settings.ai_reports_enabled:
            raise HTTPException(
                status_code=403,
                detail="AI enrichment for reports is temporarily unavailable."
            )

        # 3. Customer AI Enabled & Wallet Status
        wallet = CreditService.get_or_create_wallet(cid, db)
        if not wallet.is_enabled or (wallet.status and wallet.status.upper() in ("DISABLED", "PAUSED")):
            raise HTTPException(
                status_code=403,
                detail="AI access is currently disabled for this account."
            )

        # 4. Per-Request Limit Check
        if wallet.per_request_limit and estimated_credits > wallet.per_request_limit:
            raise HTTPException(
                status_code=400,
                detail="This AI request exceeds your allowed request limit."
            )

        # 5. Product / Plan Safety Page Allowance Check
        if not AIUsageService.can_consume_ai_page(user_id=cid, db=db):
            raise HTTPException(
                status_code=429,
                detail="Your monthly AI usage limit has been reached."
            )

        # 6. Daily Limit Check
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
                detail="Your daily AI usage limit has been reached."
            )

        # 7. Monthly Limit Check
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
                detail="Your monthly AI usage limit has been reached."
            )

        # 8. Available Credits / Wallet Balance Check
        if wallet.remaining_credits < estimated_credits:
            wallet.status = "EXHAUSTED"
            db.commit()
            raise HTTPException(
                status_code=402,
                detail="You do not have enough AI credits to complete this request."
            )

        return {
            "allowed": True,
            "wallet": wallet,
            "customer_id": cid,
            "estimated_credits": estimated_credits,
            "remaining_credits": wallet.remaining_credits,
            "remaining_daily": max(0, wallet.daily_limit - daily_used) if wallet.daily_limit else None,
            "remaining_monthly": max(0, wallet.monthly_limit - monthly_used) if wallet.monthly_limit else None
        }

    @classmethod
    def record_successful_ai_consumption(
        cls,
        customer_id: str,
        project_id: Optional[str],
        task_type: str,
        units_consumed: int = 1,
        model: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        crawl_id: Optional[str] = None,
        page_url: Optional[str] = None,
        reference_id: Optional[str] = None,
        db: Session = None
    ):
        if not db or units_consumed <= 0:
            return None

        cid = customer_id or "default_guest"

        # 1. Deduct credits from wallet & record transaction
        tx = CreditService.deduct_credits(
            customer_id=cid,
            amount=units_consumed,
            reference_id=reference_id,
            reason=f"AI consumption: {task_type}",
            db=db
        )

        # 2. Record usage log
        usage_log = AIUsageService.record_ai_usage(
            user_id=cid,
            project_id=project_id,
            crawl_id=crawl_id,
            page_url=page_url,
            task_type=task_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            units_consumed=units_consumed,
            status="success",
            db=db
        )

        return tx, usage_log

    @classmethod
    def record_failed_ai_attempt(
        cls,
        customer_id: str,
        project_id: Optional[str],
        task_type: str,
        error_message: str,
        model: Optional[str] = None,
        crawl_id: Optional[str] = None,
        page_url: Optional[str] = None,
        db: Session = None
    ):
        if not db:
            return None

        cid = customer_id or "default_guest"

        # Record failed usage log with 0 units consumed - NEVER deduct credits on failure
        return AIUsageService.record_ai_usage(
            user_id=cid,
            project_id=project_id,
            crawl_id=crawl_id,
            page_url=page_url,
            task_type=task_type,
            model=model,
            units_consumed=0,
            status="failed",
            error_message=error_message[:500] if error_message else None,
            db=db
        )
