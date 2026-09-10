from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.auth import require_master_user
from app.models.user import User
from app.services.master_service import MasterService

router = APIRouter(prefix="/api/master", tags=["Master Space"])

# Dependency shortcut for Master authorization
master_guard = require_master_user()

@router.get("/dashboard")
def get_master_dashboard(
    range_type: str = Query("30d", description="today, 7d, 30d, this_month, last_month, custom"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns top-level SaaS platform KPI metrics and aggregations."""
    metrics = MasterService.get_dashboard_metrics(
        range_type=range_type,
        custom_start=start_date,
        custom_end=end_date,
        db=db
    )
    return metrics

@router.get("/customers")
def get_customers(
    search: str = Query("", description="Search by customer name, email, or ID"),
    status: str = Query("all", description="all, active, suspended, inactive"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns a paginated list of platform customers with aggregated website & AI metrics."""
    return MasterService.get_customers_list(
        search=search,
        status_filter=status,
        page=page,
        page_size=page_size,
        db=db
    )

@router.get("/customers/{customer_id}")
def get_customer_detail(
    customer_id: str,
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns Customer 360 overview including websites, users, activity, AI usage breakdown, and reports."""
    detail = MasterService.get_customer_detail(customer_id=customer_id, db=db)
    if not detail:
        raise HTTPException(status_code=404, detail="Customer not found")
    return detail

@router.post("/customers/{customer_id}/status")
def update_customer_status(
    customer_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Updates customer account status (e.g. ACTIVE or SUSPENDED) and logs audit record."""
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    new_status = payload.get("status", "ACTIVE").upper()
    reason = payload.get("reason", "Admin status update")

    old_status = user.status or "ACTIVE"
    user.status = new_status
    db.commit()
    db.refresh(user)

    # Log audit entry
    MasterService.log_audit_action(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="CUSTOMER_STATUS_UPDATE",
        target_type="user",
        target_id=user.id,
        status="SUCCESS",
        reason=reason,
        metadata={"old_status": old_status, "new_status": new_status},
        db=db
    )

    return {"success": True, "customer_id": user.id, "status": user.status}

@router.get("/websites")
def get_websites(
    search: str = Query("", description="Search by website URL, project name, or customer"),
    status: str = Query("all", description="all, completed, running, failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform-wide list of websites/projects with health metrics and crawl statuses."""
    return MasterService.get_websites_list(
        search=search,
        status_filter=status,
        page=page,
        page_size=page_size,
        db=db
    )

@router.get("/websites/{website_id}")
def get_website_detail(
    website_id: str,
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns Website 360 view with health score, crawl history, reports, and chronological activity timeline."""
    detail = MasterService.get_website_detail(website_id=website_id, db=db)
    if not detail:
        raise HTTPException(status_code=404, detail="Website not found")
    return detail

@router.get("/ai-analytics")
def get_ai_analytics(
    range_type: str = Query("30d", description="today, 7d, 30d, this_month, last_month, custom"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform-wide AI usage analytics broken down by customer, website, provider, model, and task."""
    return MasterService.get_ai_analytics(
        range_type=range_type,
        custom_start=start_date,
        custom_end=end_date,
        db=db
    )

@router.get("/providers")
def get_providers(
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns provider monitoring summary including request counts, tokens, estimated cost, and status."""
    return MasterService.get_providers_summary(db=db)

@router.get("/providers/{provider_name}/health")
def check_provider_health(
    provider_name: str,
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Executes safe backend health check for the specified provider."""
    return MasterService.check_provider_health(provider_key=provider_name, db=db)

@router.get("/activity")
def get_activity(
    event_type: str = Query("all", description="all, crawl_completed, ai_request_executed, user_created"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform-wide global activity timeline with pagination and filtering."""
    return MasterService.get_global_activity(
        event_type=event_type,
        page=page,
        page_size=page_size,
        db=db
    )

@router.get("/system-health")
def get_system_health(
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns infrastructure health monitoring status for API, Database, Crawler, AI Gateway, and Storage."""
    return MasterService.get_system_health(db=db)

@router.get("/audit-logs")
def get_audit_logs(
    search: str = Query("", description="Search by actor email, action, or target"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform admin audit logs for security and compliance monitoring."""
    return MasterService.get_audit_logs(
        search=search,
        page=page,
        page_size=page_size,
        db=db
    )

# -------------------------------------------------------------------------
# PART 2 — MASTER CONTROL ENDPOINTS
# -------------------------------------------------------------------------
@router.get("/ai/control")
def get_ai_control(
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform global AI kill switches and feature controls."""
    return MasterService.get_ai_control_settings(db=db)

@router.patch("/ai/control")
def update_ai_control(
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Updates platform global AI kill switches (pause all, pause background, etc.)."""
    return MasterService.update_ai_control_settings(payload=payload, actor_user=current_user, db=db)

@router.get("/credits")
def get_credits_overview(
    search: str = Query("", description="Search by customer email, name, or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns credit distribution stats, customer AI wallets list, and transaction history."""
    return MasterService.get_credits_overview(search=search, page=page, page_size=page_size, db=db)

@router.get("/customers/{customer_id}/wallet")
def get_customer_wallet(
    customer_id: str,
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns customer AI wallet state and limits."""
    from app.services.credit_service import CreditService
    wallet = CreditService.get_or_create_wallet(customer_id, db)
    return wallet.to_dict()

@router.get("/customers/{customer_id}/credit-transactions")
def get_customer_credit_transactions(
    customer_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns customer's immutable credit transaction ledger."""
    from app.models.ai_wallet import AICreditTransaction
    from sqlalchemy import desc
    tx_query = db.query(AICreditTransaction).filter(AICreditTransaction.customer_id == customer_id).order_by(desc(AICreditTransaction.created_at))
    total = tx_query.count()
    txs = tx_query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [t.to_dict() for t in txs],
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.post("/customers/{customer_id}/credits")
def allocate_customer_credits(
    customer_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Allocates, adds bonus, or adjusts credits for a customer account with an audit reason."""
    amount = payload.get("amount", 0)
    tx_type = payload.get("transaction_type", "allocation")
    reason = payload.get("reason", "Admin credit adjustment")

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Credit amount must be greater than zero.")

    return MasterService.allocate_customer_credits(
        customer_id=customer_id,
        amount=int(amount),
        transaction_type=tx_type,
        reason=reason,
        actor_user=current_user,
        db=db
    )

@router.patch("/customers/{customer_id}/ai-settings")
def update_customer_ai_settings(
    customer_id: str,
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Updates customer AI enable/disable switch and custom limits (daily, monthly, per-request)."""
    return MasterService.update_customer_ai_settings(
        customer_id=customer_id,
        payload=payload,
        actor_user=current_user,
        db=db
    )

@router.get("/budgets")
def get_budgets_overview(
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Returns platform AI budget metrics and threshold states."""
    return MasterService.get_budgets_overview(db=db)

@router.patch("/budgets")
def update_budgets(
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Updates platform AI daily/monthly budget thresholds and hard stop setting."""
    return MasterService.update_ai_control_settings(payload=payload, actor_user=current_user, db=db)

@router.patch("/providers/routing")
def update_provider_routing(
    payload: dict = Body(...),
    current_user: User = Depends(master_guard),
    db: Session = Depends(get_db)
):
    """Updates primary and fallback AI provider routing configuration."""
    from app.services.credit_service import CreditService
    s = CreditService.get_or_create_platform_settings(db)
    if "primary_provider" in payload:
        s.primary_provider = payload["primary_provider"]
    if "fallback_provider" in payload:
        s.fallback_provider = payload["fallback_provider"]
    db.commit()

    MasterService.log_audit_action(
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="PROVIDER_ROUTING_UPDATE",
        target_type="platform_ai_settings",
        target_id="default",
        status="SUCCESS",
        reason=payload.get("reason", "Provider routing rules update"),
        metadata={"primary_provider": s.primary_provider, "fallback_provider": s.fallback_provider},
        db=db
    )

    return {"success": True, "primary_provider": s.primary_provider, "fallback_provider": s.fallback_provider}

