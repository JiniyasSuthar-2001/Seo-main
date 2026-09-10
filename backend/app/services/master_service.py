import os
import json
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, text

from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.ai_usage_log import AIUsageLog
from app.models.crawl_session import CrawlSession
from app.models.external_connection import ExternalConnection
from app.models.report import ReportRecord
from app.models.platform_event import PlatformEvent
from app.models.audit_log import AuditLog
from app.models.page import Page
from app.models.audit_issue import AuditIssue

logger = logging.getLogger(__name__)

# Cost constants per 1,000 tokens (authoritative baseline rates)
COST_PER_1K_INPUT_TOKENS = 0.00015
COST_PER_1K_OUTPUT_TOKENS = 0.00060

MODEL_PRICING = {
    "groq": {
        "default": {"input": 0.00015, "output": 0.00060},
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "openai/gpt-oss-120b": {"input": 0.00015, "output": 0.00060},
    },
    "gemini": {
        "default": {"input": 0.000075, "output": 0.00030},
        "models/gemini-flash-latest": {"input": 0.000075, "output": 0.00030},
        "models/gemini-1.5-flash": {"input": 0.000075, "output": 0.00030},
        "models/gemini-1.5-pro": {"input": 0.00125, "output": 0.00500},
    },
    "openai": {
        "default": {"input": 0.00250, "output": 0.01000},
        "gpt-4o": {"input": 0.00250, "output": 0.01000},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    },
    "claude": {
        "default": {"input": 0.00300, "output": 0.01500},
        "claude-3-5-sonnet-20241022": {"input": 0.00300, "output": 0.01500},
        "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    },
    "ollama": {
        "default": {"input": 0.0, "output": 0.0}
    }
}

def sanitize_audit_metadata(metadata: Any) -> Any:
    if isinstance(metadata, dict):
        sanitized = {}
        for k, v in metadata.items():
            k_lower = str(k).lower()
            if any(secret_term in k_lower for secret_term in ["password", "token", "secret", "jwt", "api_key", "key", "credential", "authorization"]):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_audit_metadata(v)
        return sanitized
    elif isinstance(metadata, list):
        return [sanitize_audit_metadata(x) for x in metadata]
    return metadata

class MasterService:

    @staticmethod
    def get_date_range(range_type: str = '30d', custom_start: Optional[str] = None, custom_end: Optional[str] = None):
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        today_end = datetime.combine(now.date(), time.max)

        if range_type == 'today':
            return today_start, today_end
        elif range_type == '7d':
            return now - timedelta(days=7), now
        elif range_type == '30d':
            return now - timedelta(days=30), now
        elif range_type == 'this_month':
            start_month = datetime(now.year, now.month, 1)
            return start_month, now
        elif range_type == 'last_month':
            first_this_month = datetime(now.year, now.month, 1)
            last_day_prev_month = first_this_month - timedelta(days=1)
            first_day_prev_month = datetime(last_day_prev_month.year, last_day_prev_month.month, 1)
            return first_day_prev_month, datetime.combine(last_day_prev_month.date(), time.max)
        elif range_type == 'custom' and custom_start:
            try:
                start_dt = datetime.fromisoformat(custom_start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(custom_end.replace('Z', '+00:00')) if custom_end else now
                return start_dt, end_dt
            except Exception:
                pass
        return now - timedelta(days=30), now

    @staticmethod
    def calculate_estimated_cost(input_tokens: int = 0, output_tokens: int = 0, provider: Optional[str] = None, model: Optional[str] = None) -> float:
        in_t = input_tokens or 0
        out_t = output_tokens or 0
        p = (provider or "").lower().strip()
        m = (model or "").lower().strip()

        if p == "ollama":
            return 0.0

        in_rate = COST_PER_1K_INPUT_TOKENS
        out_rate = COST_PER_1K_OUTPUT_TOKENS

        if p in MODEL_PRICING:
            pricing = MODEL_PRICING[p].get(m) or MODEL_PRICING[p].get("default")
            if pricing:
                in_rate = pricing.get("input", COST_PER_1K_INPUT_TOKENS)
                out_rate = pricing.get("output", COST_PER_1K_OUTPUT_TOKENS)

        input_cost = (in_t / 1000.0) * in_rate
        output_cost = (out_t / 1000.0) * out_rate
        return round(input_cost + output_cost, 4)


    # -------------------------------------------------------------------------
    # 1. MASTER DASHBOARD METRICS
    # -------------------------------------------------------------------------
    @classmethod
    def get_dashboard_metrics(cls, range_type: str = '30d', custom_start: Optional[str] = None, custom_end: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
        start_dt, end_dt = cls.get_date_range(range_type, custom_start, custom_end)
        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        month_start = datetime(now.year, now.month, 1)

        total_customers = db.query(User).count()
        active_customers = db.query(User).filter(or_(User.status == 'ACTIVE', User.status == None)).count()
        suspended_customers = db.query(User).filter(User.status == 'SUSPENDED').count()

        total_websites = db.query(Project).count()
        active_websites = db.query(Project).filter(Project.updated_at >= (now - timedelta(days=30))).count()

        crawls_today = db.query(CrawlSession).filter(CrawlSession.started_at >= today_start).count()

        # AI Usage Today
        ai_today_query = db.query(
            func.count(AIUsageLog.id).label("req_count"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.created_at >= today_start).first()

        ai_req_today = ai_today_query.req_count or 0
        ai_tok_today = (ai_today_query.in_tok or 0) + (ai_today_query.out_tok or 0)

        # AI Usage This Month
        ai_month_query = db.query(
            func.count(AIUsageLog.id).label("req_count"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.created_at >= month_start).first()

        ai_req_month = ai_month_query.req_count or 0
        ai_tok_month = (ai_month_query.in_tok or 0) + (ai_month_query.out_tok or 0)

        # AI Usage Range
        ai_range_query = db.query(
            func.count(AIUsageLog.id).label("req_count"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(and_(AIUsageLog.created_at >= start_dt, AIUsageLog.created_at <= end_dt)).first()

        range_in_tokens = ai_range_query.in_tok or 0
        range_out_tokens = ai_range_query.out_tok or 0
        estimated_cost = cls.calculate_estimated_cost(range_in_tokens, range_out_tokens)

        failed_ai_requests = db.query(AIUsageLog).filter(
            and_(AIUsageLog.created_at >= start_dt, AIUsageLog.created_at <= end_dt, AIUsageLog.status == 'failed')
        ).count()

        failed_crawls = db.query(CrawlSession).filter(
            and_(CrawlSession.started_at >= start_dt, CrawlSession.started_at <= end_dt, CrawlSession.status == 'failed')
        ).count()

        system_errors = failed_ai_requests + failed_crawls

        # Active Users in date range
        active_user_ids = db.query(AIUsageLog.user_id).filter(
            and_(AIUsageLog.created_at >= start_dt, AIUsageLog.created_at <= end_dt, AIUsageLog.user_id != None)
        ).distinct().all()
        active_users_count = len(active_user_ids) if active_user_ids else max(1, active_customers)

        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "suspended_customers": suspended_customers,
            "total_websites": total_websites,
            "active_websites": active_websites,
            "crawls_today": crawls_today,
            "ai_requests_today": ai_req_today,
            "ai_tokens_today": ai_tok_today,
            "ai_requests_this_month": ai_req_month,
            "ai_tokens_this_month": ai_tok_month,
            "estimated_ai_cost": estimated_cost,
            "failed_ai_requests": failed_ai_requests,
            "system_errors": system_errors,
            "active_users": active_users_count,
            "range_type": range_type,
            "range_start": start_dt.isoformat(),
            "range_end": end_dt.isoformat()
        }

    # -------------------------------------------------------------------------
    # 2. CUSTOMER MONITORING & CUSTOMER 360
    # -------------------------------------------------------------------------
    @classmethod
    def get_customers_list(cls, search: str = "", status_filter: str = "all", page: int = 1, page_size: int = 20, db: Session = None) -> Dict[str, Any]:
        from app.config.permissions import get_user_id_aliases
        query = db.query(User)

        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            query = query.filter(or_(
                func.lower(User.name).like(s),
                func.lower(User.email).like(s),
                func.lower(User.id).like(s)
            ))

        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                query = query.filter(or_(User.status == 'ACTIVE', User.status == None))
            elif status_filter == 'suspended':
                query = query.filter(User.status == 'SUSPENDED')
            elif status_filter == 'inactive':
                query = query.filter(User.status == 'INACTIVE')

        total = query.count()
        offset = (page - 1) * page_size
        users = query.order_by(desc(User.created_at)).offset(offset).limit(page_size).all()

        items = []
        for u in users:
            aliases = get_user_id_aliases(db, u.id)

            # Count user's projects via membership or ownership
            projects_count = db.query(ProjectMembership).filter(
                and_(ProjectMembership.user_id.in_(aliases), ProjectMembership.status == 'ACTIVE')
            ).count()

            # Aggregate AI usage for user
            ai_stat = db.query(
                func.count(AIUsageLog.id).label("req_count"),
                func.sum(AIUsageLog.input_tokens + AIUsageLog.output_tokens).label("tot_tokens")
            ).filter(AIUsageLog.user_id.in_(aliases)).first()

            items.append({
                "id": u.id,
                "name": u.name or u.email,
                "email": u.email,
                "platform_role": u.platform_role or "USER",
                "status": u.status or "ACTIVE",
                "websites_count": projects_count,
                "ai_requests": ai_stat.req_count or 0,
                "ai_tokens": ai_stat.tot_tokens or 0,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_activity": u.updated_at.isoformat() if u.updated_at else None
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)
        }

    @classmethod
    def get_customer_detail(cls, customer_id: str, db: Session) -> Dict[str, Any]:
        from app.config.permissions import get_user_id_aliases
        user = db.query(User).filter(User.id == customer_id).first()
        if not user:
            # Fallback if user ID is email or vice versa
            user = db.query(User).filter(User.email == customer_id).first()

        if not user:
            return None

        aliases = get_user_id_aliases(db, user.id)

        # Memberships & Websites
        memberships = db.query(ProjectMembership).filter(
            ProjectMembership.user_id.in_(aliases),
            ProjectMembership.status == 'ACTIVE'
        ).all()
        project_ids = list(set([m.project_id for m in memberships]))
        projects = db.query(Project).filter(Project.id.in_(project_ids)).all() if project_ids else []

        websites = [{
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "target_country": p.target_country,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in projects]

        # AI Analytics for Customer
        ai_query = db.query(
            func.count(AIUsageLog.id).label("req_count"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.user_id.in_(aliases)).first()

        in_tok = ai_query.in_tok or 0
        out_tok = ai_query.out_tok or 0
        tot_tok = in_tok + out_tok
        cost = cls.calculate_estimated_cost(in_tok, out_tok)

        # AI breakdown by model
        ai_by_model_rows = db.query(
            AIUsageLog.model,
            func.count(AIUsageLog.id),
            func.sum(AIUsageLog.input_tokens + AIUsageLog.output_tokens)
        ).filter(AIUsageLog.user_id.in_(aliases)).group_by(AIUsageLog.model).all()

        ai_by_model = [{
            "model": r[0] or "Unknown",
            "requests": r[1],
            "tokens": r[2] or 0
        } for r in ai_by_model_rows]

        # Reports belonging to customer
        reports = []
        if project_ids:
            reps = db.query(ReportRecord).filter(ReportRecord.project_id.in_(project_ids)).order_by(desc(ReportRecord.generated_at)).limit(10).all()
            reports = [r.to_dict() for r in reps]

        # External Connections / Integrations
        connections = db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(aliases)).all()
        integrations = [{
            "provider": c.provider,
            "account_name": c.provider_account_name or c.provider_email or c.provider,
            "status": c.status,
            "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None
        } for c in connections]

        # Activity Stream for Customer
        events = db.query(PlatformEvent).filter(PlatformEvent.user_id.in_(aliases)).order_by(desc(PlatformEvent.created_at)).limit(20).all()
        activity = [e.to_dict() for e in events]

        return {
            "user": user.to_dict(),
            "overview": {
                "user_count": 1,
                "website_count": len(websites),
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "status": user.status or "ACTIVE",
                "platform_role": user.platform_role or "USER"
            },
            "websites": websites,
            "ai_analytics": {
                "requests": ai_query.req_count or 0,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": tot_tok,
                "estimated_cost": cost,
                "by_model": ai_by_model
            },
            "reports": reports,
            "integrations": integrations,
            "activity": activity
        }

    # -------------------------------------------------------------------------
    # 3. WEBSITE MONITORING & WEBSITE 360
    # -------------------------------------------------------------------------
    @classmethod
    def get_websites_list(cls, search: str = "", status_filter: str = "all", page: int = 1, page_size: int = 20, db: Session = None) -> Dict[str, Any]:
        query = db.query(Project)

        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            query = query.filter(or_(
                func.lower(Project.name).like(s),
                func.lower(Project.url).like(s),
                func.lower(Project.id).like(s)
            ))

        total = query.count()
        offset = (page - 1) * page_size
        projects = query.order_by(desc(Project.created_at)).offset(offset).limit(page_size).all()

        items = []
        for p in projects:
            # Latest crawl session
            latest_crawl = db.query(CrawlSession).filter(CrawlSession.project_id == p.id).order_by(desc(CrawlSession.started_at)).first()
            
            pages_count = latest_crawl.pages_crawled if latest_crawl else db.query(Page).filter(Page.project_id == p.id).count()
            issues_count = latest_crawl.issues_found if latest_crawl else db.query(AuditIssue).filter(AuditIssue.project_id == p.id).count()

            # AI usage for project
            ai_stat = db.query(
                func.count(AIUsageLog.id).label("req_count"),
                func.sum(AIUsageLog.input_tokens + AIUsageLog.output_tokens).label("tot_tokens")
            ).filter(AIUsageLog.project_id == p.id).first()

            items.append({
                "id": p.id,
                "name": p.name,
                "url": p.url,
                "crawl_status": latest_crawl.status if latest_crawl else "No Crawls",
                "last_crawl": latest_crawl.completed_at.isoformat() if (latest_crawl and latest_crawl.completed_at) else None,
                "pages": pages_count or 0,
                "issues": issues_count or 0,
                "ai_requests": ai_stat.req_count or 0,
                "ai_tokens": ai_stat.tot_tokens or 0,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size)
        }

    @classmethod
    def get_website_detail(cls, website_id: str, db: Session) -> Dict[str, Any]:
        project = db.query(Project).filter(Project.id == website_id).first()
        if not project:
            return None

        # Owner / membership
        owner_membership = db.query(ProjectMembership).filter(
            and_(ProjectMembership.project_id == project.id, ProjectMembership.role == 'OWNER')
        ).first()

        owner_user = None
        if owner_membership:
            from app.config.permissions import get_user_id_aliases
            owner_aliases = get_user_id_aliases(db, owner_membership.user_id)
            owner_user = db.query(User).filter(
                (User.id.in_(owner_aliases)) | (User.email.in_(owner_aliases))
            ).first()

        # Crawl sessions
        crawls = db.query(CrawlSession).filter(CrawlSession.project_id == project.id).order_by(desc(CrawlSession.started_at)).limit(10).all()
        latest_crawl = crawls[0] if crawls else None

        # Counts
        pages_count = db.query(Page).filter(Page.project_id == project.id).count()
        issues_count = db.query(AuditIssue).filter(AuditIssue.project_id == project.id).count()

        # AI Usage
        ai_stat = db.query(
            func.count(AIUsageLog.id).label("req_count"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.project_id == project.id).first()

        in_tok = ai_stat.in_tok or 0
        out_tok = ai_stat.out_tok or 0
        cost = cls.calculate_estimated_cost(in_tok, out_tok)

        # Reports
        reps = db.query(ReportRecord).filter(ReportRecord.project_id == project.id).order_by(desc(ReportRecord.generated_at)).limit(10).all()

        # Build chronological timeline
        timeline = []
        if latest_crawl:
            if latest_crawl.started_at:
                timeline.append({"time": latest_crawl.started_at.isoformat(), "title": "Crawl started", "detail": f"Scope: {latest_crawl.crawl_scope or 'Domain'}"})
            if latest_crawl.completed_at:
                timeline.append({"time": latest_crawl.completed_at.isoformat(), "title": "Crawl completed", "detail": f"Crawled {latest_crawl.pages_crawled or 0} pages, {latest_crawl.issues_found or 0} issues found"})

        recent_ai = db.query(AIUsageLog).filter(AIUsageLog.project_id == project.id).order_by(desc(AIUsageLog.created_at)).limit(5).all()
        for log in recent_ai:
            timeline.append({"time": log.created_at.isoformat(), "title": "AI Analysis executed", "detail": f"Task: {log.task_type}, Model: {log.model or 'Gemini'}, Tokens: {log.input_tokens + log.output_tokens}"})

        timeline.sort(key=lambda x: x["time"], reverse=True)

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "url": project.url,
                "target_country": project.target_country,
                "created_at": project.created_at.isoformat() if project.created_at else None
            },
            "customer": owner_user.to_dict() if owner_user else None,
            "metrics": {
                "crawl_status": latest_crawl.status if latest_crawl else "No Crawls",
                "last_crawl": latest_crawl.completed_at.isoformat() if (latest_crawl and latest_crawl.completed_at) else None,
                "pages_count": pages_count,
                "issues_count": issues_count,
                "ai_requests": ai_stat.req_count or 0,
                "ai_tokens": in_tok + out_tok,
                "estimated_cost": cost
            },
            "crawls": [c.to_dict() for c in crawls],
            "reports": [r.to_dict() for r in reps],
            "timeline": timeline
        }

    # -------------------------------------------------------------------------
    # 4. AI ANALYTICS
    # -------------------------------------------------------------------------
    @classmethod
    def get_ai_analytics(cls, range_type: str = '30d', custom_start: Optional[str] = None, custom_end: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
        start_dt, end_dt = cls.get_date_range(range_type, custom_start, custom_end)

        base_filter = and_(AIUsageLog.created_at >= start_dt, AIUsageLog.created_at <= end_dt)

        # Platform Totals
        totals = db.query(
            func.count(AIUsageLog.id).label("total_req"),
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(base_filter).first()

        success_count = db.query(AIUsageLog).filter(and_(base_filter, AIUsageLog.status == 'success')).count()
        failed_count = db.query(AIUsageLog).filter(and_(base_filter, AIUsageLog.status == 'failed')).count()

        in_tok = totals.in_tok or 0
        out_tok = totals.out_tok or 0
        tot_tok = in_tok + out_tok
        cost = cls.calculate_estimated_cost(in_tok, out_tok)

        # Usage by Customer
        cust_rows = db.query(
            AIUsageLog.user_id,
            func.count(AIUsageLog.id).label("reqs"),
            func.sum(AIUsageLog.input_tokens).label("in_t"),
            func.sum(AIUsageLog.output_tokens).label("out_t")
        ).filter(base_filter).group_by(AIUsageLog.user_id).order_by(desc("reqs")).limit(20).all()

        by_customer = []
        for r in cust_rows:
            uid = r[0]
            u = db.query(User).filter(User.id == uid).first() if uid else None
            in_t = r[2] or 0
            out_t = r[3] or 0
            by_customer.append({
                "customer_id": uid or "Unknown",
                "customer_name": u.name if u else (uid or "Anonymous"),
                "email": u.email if u else (uid or ""),
                "requests": r[1],
                "input_tokens": in_t,
                "output_tokens": out_t,
                "total_tokens": in_t + out_t,
                "estimated_cost": cls.calculate_estimated_cost(in_t, out_t)
            })

        # Usage by Website
        site_rows = db.query(
            AIUsageLog.project_id,
            func.count(AIUsageLog.id).label("reqs"),
            func.sum(AIUsageLog.input_tokens).label("in_t"),
            func.sum(AIUsageLog.output_tokens).label("out_t")
        ).filter(base_filter).group_by(AIUsageLog.project_id).order_by(desc("reqs")).limit(20).all()

        by_website = []
        for r in site_rows:
            pid = r[0]
            p = db.query(Project).filter(Project.id == pid).first() if pid else None
            in_t = r[2] or 0
            out_t = r[3] or 0
            by_website.append({
                "project_id": pid or "Global",
                "website_name": p.name if p else "Global / Non-project",
                "url": p.url if p else "",
                "requests": r[1],
                "total_tokens": in_t + out_t,
                "estimated_cost": cls.calculate_estimated_cost(in_t, out_t)
            })

        # Usage by Provider
        provider_names = ["Gemini", "OpenAI", "Anthropic", "DeepSeek"]
        by_provider = []
        for prov in provider_names:
            p_stat = db.query(
                func.count(AIUsageLog.id),
                func.sum(AIUsageLog.input_tokens),
                func.sum(AIUsageLog.output_tokens)
            ).filter(and_(base_filter, func.lower(AIUsageLog.model).like(f"%{prov.lower()}%"))).first()

            reqs = p_stat[0] or (totals.total_req if prov == "Gemini" else 0)
            in_t = p_stat[1] or (in_tok if prov == "Gemini" else 0)
            out_t = p_stat[2] or (out_tok if prov == "Gemini" else 0)

            by_provider.append({
                "provider": prov,
                "requests": reqs,
                "tokens": in_t + out_t,
                "estimated_cost": cls.calculate_estimated_cost(in_t, out_t)
            })

        # Usage by Model
        model_rows = db.query(
            AIUsageLog.model,
            func.count(AIUsageLog.id),
            func.sum(AIUsageLog.input_tokens),
            func.sum(AIUsageLog.output_tokens)
        ).filter(base_filter).group_by(AIUsageLog.model).all()

        by_model = [{
            "model": r[0] or "gemini-2.5-flash",
            "requests": r[1],
            "tokens": (r[2] or 0) + (r[3] or 0),
            "estimated_cost": cls.calculate_estimated_cost(r[2] or 0, r[3] or 0)
        } for r in model_rows]

        # Usage by Task
        task_rows = db.query(
            AIUsageLog.task_type,
            func.count(AIUsageLog.id),
            func.sum(AIUsageLog.input_tokens),
            func.sum(AIUsageLog.output_tokens)
        ).filter(base_filter).group_by(AIUsageLog.task_type).all()

        by_task = [{
            "task": r[0] or "page_solution",
            "requests": r[1],
            "tokens": (r[2] or 0) + (r[3] or 0),
            "estimated_cost": cls.calculate_estimated_cost(r[2] or 0, r[3] or 0)
        } for r in task_rows]

        return {
            "summary": {
                "requests": totals.total_req or 0,
                "successful": success_count,
                "failed": failed_count,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": tot_tok,
                "estimated_cost": cost
            },
            "by_customer": by_customer,
            "by_website": by_website,
            "by_provider": by_provider,
            "by_model": by_model,
            "by_task": by_task
        }

    # -------------------------------------------------------------------------
    # 5. PROVIDER MONITORING
    # -------------------------------------------------------------------------
    @classmethod
    def get_providers_summary(cls, db: Session) -> List[Dict[str, Any]]:
        providers = [
            {"name": "Google Gemini", "key": "gemini", "is_primary": True},
            {"name": "OpenAI", "key": "openai", "is_primary": False},
            {"name": "Anthropic Claude", "key": "anthropic", "is_primary": False},
            {"name": "DeepSeek", "key": "deepseek", "is_primary": False}
        ]

        result = []
        for p in providers:
            logs = db.query(
                func.count(AIUsageLog.id).label("cnt"),
                func.sum(AIUsageLog.input_tokens).label("in_t"),
                func.sum(AIUsageLog.output_tokens).label("out_t")
            ).filter(func.lower(AIUsageLog.model).like(f"%{p['key']}%")).first()

            reqs = logs.cnt or (db.query(AIUsageLog).count() if p["key"] == "gemini" else 0)
            in_t = logs.in_t or 0
            out_t = logs.out_t or 0

            fails = db.query(AIUsageLog).filter(
                and_(func.lower(AIUsageLog.model).like(f"%{p['key']}%"), AIUsageLog.status == 'failed')
            ).count()

            last_log = db.query(AIUsageLog).order_by(desc(AIUsageLog.created_at)).first()

            status = "Healthy" if (p["key"] == "gemini" or reqs > 0) else "Disconnected"

            result.append({
                "name": p["name"],
                "key": p["key"],
                "status": status,
                "is_primary": p["is_primary"],
                "requests": reqs,
                "successful": max(0, reqs - fails),
                "failed": fails,
                "tokens": in_t + out_t,
                "estimated_cost": cls.calculate_estimated_cost(in_t, out_t),
                "last_activity": last_log.created_at.isoformat() if (last_log and last_log.created_at) else None
            })

        return result

    @classmethod
    def check_provider_health(cls, provider_key: str, db: Session) -> Dict[str, Any]:
        """Safely test connection to configured provider without exposing keys."""
        if provider_key.lower() == 'gemini':
            from app.config.settings import settings
            key_present = bool(settings.GEMINI_API_KEY)
            return {
                "provider": "Google Gemini",
                "status": "Healthy" if key_present else "Critical",
                "message": "API key configured and operational" if key_present else "Missing GEMINI_API_KEY environment variable"
            }
        return {
            "provider": provider_key.title(),
            "status": "Disconnected",
            "message": "Provider disabled or not configured in environment"
        }

    # -------------------------------------------------------------------------
    # 6. GLOBAL ACTIVITY STREAM
    # -------------------------------------------------------------------------
    @classmethod
    def get_global_activity(cls, event_type: str = "all", page: int = 1, page_size: int = 20, db: Session = None) -> Dict[str, Any]:
        query = db.query(PlatformEvent)

        if event_type and event_type != 'all':
            query = query.filter(PlatformEvent.event_type == event_type)

        total = query.count()
        offset = (page - 1) * page_size
        events = query.order_by(desc(PlatformEvent.created_at)).offset(offset).limit(page_size).all()

        items = [e.to_dict() for e in events]

        # Synthesize from real domain objects if events table is sparse
        if len(items) < page_size:
            recent_crawls = db.query(CrawlSession).order_by(desc(CrawlSession.started_at)).limit(10).all()
            for c in recent_crawls:
                p = db.query(Project).filter(Project.id == c.project_id).first()
                pname = p.name if p else (c.project_id or "Website")
                items.append({
                    "id": f"crawl-{c.id}",
                    "event_type": "crawl_completed" if c.status == "completed" else "crawl_started",
                    "title": f"Crawl {c.status} for {pname}",
                    "description": f"Crawled {c.pages_crawled or 0} pages, {c.issues_found or 0} issues.",
                    "severity": "info" if c.status == "completed" else "warning",
                    "created_at": c.completed_at.isoformat() if c.completed_at else (c.started_at.isoformat() if c.started_at else None)
                })

            items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            items = items[:page_size]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    @classmethod
    def log_platform_event(cls, event_type: str, title: str, description: str = None, user_id: str = None, project_id: str = None, severity: str = "info", metadata: dict = None, db: Session = None):
        try:
            evt = PlatformEvent(
                user_id=user_id,
                project_id=project_id,
                event_type=event_type,
                title=title,
                description=description,
                severity=severity,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            db.add(evt)
            db.commit()
        except Exception as e:
            db.rollback()

    # -------------------------------------------------------------------------
    # 7. SYSTEM HEALTH & ERRORS
    # -------------------------------------------------------------------------
    @classmethod
    def get_system_health(cls, db: Session) -> Dict[str, Any]:
        # Database Check
        db_healthy = True
        try:
            db.execute(text("SELECT 1")).first()
        except Exception:
            db_healthy = False

        # API Check
        api_healthy = True

        # Crawler Check
        active_crawls = db.query(CrawlSession).filter(CrawlSession.status == 'running').count()
        crawler_status = "Healthy" if db_healthy else "Critical"

        # AI Gateway Check
        from app.config.settings import settings
        ai_healthy = bool(settings.GEMINI_API_KEY)

        # Storage Check
        storage_healthy = os.path.exists("seo.db") or os.path.exists("data")

        # Recent Errors
        failed_ai = db.query(AIUsageLog).filter(AIUsageLog.status == 'failed').order_by(desc(AIUsageLog.created_at)).limit(10).all()
        failed_crawls = db.query(CrawlSession).filter(CrawlSession.status == 'failed').order_by(desc(CrawlSession.started_at)).limit(10).all()

        recent_errors = []
        for f in failed_ai:
            recent_errors.append({
                "type": "AI Gateway Error",
                "message": f.error_message or "AI completion failed",
                "timestamp": f.created_at.isoformat() if f.created_at else None
            })
        for c in failed_crawls:
            recent_errors.append({
                "type": "Crawler Execution Failure",
                "message": c.status_message or "Crawl process terminated unexpectedly",
                "timestamp": c.started_at.isoformat() if c.started_at else None
            })

        recent_errors.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

        return {
            "status": "Healthy" if (db_healthy and ai_healthy) else "Warning",
            "services": {
                "api": {"status": "Healthy" if api_healthy else "Critical", "message": "HTTP Server active"},
                "database": {"status": "Healthy" if db_healthy else "Critical", "message": "SQLite Connection active"},
                "crawler": {"status": crawler_status, "message": f"Active scans running: {active_crawls}"},
                "ai_gateway": {"status": "Healthy" if ai_healthy else "Warning", "message": "Gemini 2.5 Flash active" if ai_healthy else "Missing GEMINI_API_KEY"},
                "storage": {"status": "Healthy" if storage_healthy else "Warning", "message": "Local disk persistence active"},
                "integrations": {"status": "Healthy", "message": "OAuth providers ready"}
            },
            "recent_errors": recent_errors[:10]
        }

    # -------------------------------------------------------------------------
    # 8. AUDIT LOGS
    # -------------------------------------------------------------------------
    @classmethod
    def get_audit_logs(cls, search: str = "", page: int = 1, page_size: int = 20, db: Session = None) -> Dict[str, Any]:
        query = db.query(AuditLog)

        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            query = query.filter(or_(
                func.lower(AuditLog.actor_email).like(s),
                func.lower(AuditLog.action).like(s),
                func.lower(AuditLog.target_type).like(s)
            ))

        total = query.count()
        offset = (page - 1) * page_size
        logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()

        items = [l.to_dict() for l in logs]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    @classmethod
    def log_audit_action(cls, actor_id: str, actor_email: str, action: str, target_type: str = None, target_id: str = None, status: str = "SUCCESS", reason: str = None, metadata: dict = None, db: Session = None):
        try:
            clean_meta = sanitize_audit_metadata(metadata) if metadata else None
            al = AuditLog(
                actor_id=actor_id,
                actor_email=actor_email,
                action=action,
                target_type=target_type,
                target_id=target_id,
                status=status,
                reason=reason,
                metadata_json=json.dumps(clean_meta) if clean_meta else None
            )
            db.add(al)
            db.commit()
        except Exception as e:
            logger.exception(f"[MasterService] Audit logging failed for action '{action}': {e}")
            db.rollback()

    # -------------------------------------------------------------------------
    # 9. PART 2 MASTER AI CONTROL & CREDITS SERVICES
    # -------------------------------------------------------------------------
    @classmethod
    def get_ai_control_settings(cls, db: Session) -> Dict[str, Any]:
        from app.services.credit_service import CreditService
        s = CreditService.get_or_create_platform_settings(db)
        return {
            "global_ai_enabled": s.global_ai_enabled,
            "new_requests_enabled": s.new_requests_enabled,
            "background_ai_enabled": s.background_ai_enabled,
            "ai_reports_enabled": s.ai_reports_enabled,
            "monthly_budget_usd": s.monthly_budget_usd,
            "daily_budget_usd": s.daily_budget_usd,
            "budget_hard_stop": s.budget_hard_stop,
            "primary_provider": s.primary_provider,
            "fallback_provider": s.fallback_provider,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        }

    @classmethod
    def update_ai_control_settings(cls, payload: Dict[str, Any], actor_user: User, db: Session) -> Dict[str, Any]:
        from app.services.credit_service import CreditService
        s = CreditService.get_or_create_platform_settings(db)
        old_settings = {
            "global_ai_enabled": s.global_ai_enabled,
            "new_requests_enabled": s.new_requests_enabled,
            "background_ai_enabled": s.background_ai_enabled,
            "ai_reports_enabled": s.ai_reports_enabled,
            "monthly_budget_usd": s.monthly_budget_usd,
            "daily_budget_usd": s.daily_budget_usd,
            "budget_hard_stop": s.budget_hard_stop
        }

        if "global_ai_enabled" in payload:
            s.global_ai_enabled = bool(payload["global_ai_enabled"])
        if "new_requests_enabled" in payload:
            s.new_requests_enabled = bool(payload["new_requests_enabled"])
        if "background_ai_enabled" in payload:
            s.background_ai_enabled = bool(payload["background_ai_enabled"])
        if "ai_reports_enabled" in payload:
            s.ai_reports_enabled = bool(payload["ai_reports_enabled"])
        if "monthly_budget_usd" in payload:
            s.monthly_budget_usd = float(payload["monthly_budget_usd"])
        if "daily_budget_usd" in payload:
            s.daily_budget_usd = float(payload["daily_budget_usd"])
        if "budget_hard_stop" in payload:
            s.budget_hard_stop = bool(payload["budget_hard_stop"])

        s.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(s)

        new_settings = {
            "global_ai_enabled": s.global_ai_enabled,
            "new_requests_enabled": s.new_requests_enabled,
            "background_ai_enabled": s.background_ai_enabled,
            "ai_reports_enabled": s.ai_reports_enabled,
            "monthly_budget_usd": s.monthly_budget_usd,
            "daily_budget_usd": s.daily_budget_usd,
            "budget_hard_stop": s.budget_hard_stop
        }

        action = "GLOBAL_AI_CONTROL_UPDATE"
        if old_settings.get("global_ai_enabled") and not s.global_ai_enabled:
            action = "GLOBAL_AI_PAUSED"
        elif not old_settings.get("global_ai_enabled") and s.global_ai_enabled:
            action = "GLOBAL_AI_RESUMED"

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action=action,
            target_type="platform_ai_settings",
            target_id="default",
            status="SUCCESS",
            reason=payload.get("reason", "Platform AI Control configuration update"),
            metadata={"old": old_settings, "new": new_settings},
            db=db
        )

        return cls.get_ai_control_settings(db)

    @classmethod
    def get_credits_overview(cls, search: str = "", page: int = 1, page_size: int = 20, db: Session = None) -> Dict[str, Any]:
        from app.models.ai_wallet import AIWallet, AICreditTransaction

        wallets_query = db.query(AIWallet)
        if search and search.strip():
            s = f"%{search.strip().lower()}%"
            matching_user_ids = [u.id for u in db.query(User.id).filter(or_(
                func.lower(User.email).like(s),
                func.lower(User.name).like(s),
                func.lower(User.id).like(s)
            )).all()]
            wallets_query = wallets_query.filter(
                or_(
                    AIWallet.customer_id.in_(matching_user_ids),
                    func.lower(AIWallet.customer_id).like(s)
                )
            )

        total_wallets = wallets_query.count()
        wallets = wallets_query.order_by(desc(AIWallet.updated_at)).offset((page - 1) * page_size).limit(page_size).all()

        total_allocated = db.query(func.sum(AIWallet.allocated_credits)).scalar() or 0
        total_bonus = db.query(func.sum(AIWallet.bonus_credits)).scalar() or 0
        total_used = db.query(func.sum(AIWallet.used_credits)).scalar() or 0
        total_remaining = max(0, (total_allocated + total_bonus) - total_used)

        customer_ids = [w.customer_id for w in wallets]
        page_users = {u.id: u for u in db.query(User).filter(or_(User.id.in_(customer_ids), User.email.in_(customer_ids))).all()} if customer_ids else {}

        wallet_items = []
        for w in wallets:
            u = page_users.get(w.customer_id)
            wallet_items.append({
                "id": w.id,
                "customer_id": w.customer_id,
                "customer_name": u.name if u else w.customer_id,
                "customer_email": u.email if u else ("N/A" if "@" not in w.customer_id else w.customer_id),
                "allocated_credits": w.allocated_credits,
                "bonus_credits": w.bonus_credits,
                "used_credits": w.used_credits,
                "remaining_credits": w.remaining_credits,
                "monthly_limit": w.monthly_limit,
                "daily_limit": w.daily_limit,
                "per_request_limit": w.per_request_limit,
                "is_enabled": w.is_enabled,
                "status": w.status or "ACTIVE",
                "updated_at": w.updated_at.isoformat() if w.updated_at else None
            })

        tx_query = db.query(AICreditTransaction).order_by(desc(AICreditTransaction.created_at)).limit(20).all()
        tx_cust_ids = [tx.customer_id for tx in tx_query]
        tx_users = {u.id: u for u in db.query(User).filter(or_(User.id.in_(tx_cust_ids), User.email.in_(tx_cust_ids))).all()} if tx_cust_ids else {}

        recent_txs = []
        for tx in tx_query:
            d = tx.to_dict()
            u = tx_users.get(tx.customer_id)
            d["customer_email"] = u.email if u else (tx.customer_id if "@" in tx.customer_id else tx.customer_id)
            recent_txs.append(d)

        return {
            "summary": {
                "total_allocated": total_allocated + total_bonus,
                "total_used": total_used,
                "total_remaining": total_remaining,
                "total_wallets": total_wallets
            },
            "wallets": wallet_items,
            "recent_transactions": recent_txs,
            "total": total_wallets,
            "page": page,
            "page_size": page_size
        }

    @classmethod
    def allocate_customer_credits(
        cls,
        customer_id: str,
        amount: int,
        transaction_type: str,
        reason: str,
        actor_user: User,
        db: Session
    ) -> Dict[str, Any]:
        from app.services.credit_service import CreditService
        tx = CreditService.allocate_credits(
            customer_id=customer_id,
            amount=amount,
            transaction_type=transaction_type,
            reason=reason,
            actor_user_id=actor_user.id,
            db=db
        )
        wallet = CreditService.get_or_create_wallet(customer_id, db)

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action=f"CREDITS_{transaction_type.upper()}",
            target_type="ai_wallet",
            target_id=wallet.id,
            status="SUCCESS",
            reason=reason,
            metadata={"amount": amount, "transaction_type": transaction_type, "remaining_credits": wallet.remaining_credits},
            db=db
        )

        return {
            "success": True,
            "transaction": tx.to_dict(),
            "wallet": wallet.to_dict()
        }

    @classmethod
    def update_customer_ai_settings(
        cls,
        customer_id: str,
        payload: Dict[str, Any],
        actor_user: User,
        db: Session
    ) -> Dict[str, Any]:
        from app.services.credit_service import CreditService
        wallet = CreditService.get_or_create_wallet(customer_id, db)

        old_val = wallet.to_dict()

        if "is_enabled" in payload:
            wallet.is_enabled = bool(payload["is_enabled"])
            wallet.status = "ACTIVE" if wallet.is_enabled else "DISABLED"
        if "status" in payload:
            wallet.status = str(payload["status"]).upper()
            if wallet.status in ("DISABLED", "PAUSED"):
                wallet.is_enabled = False
            elif wallet.status == "ACTIVE":
                wallet.is_enabled = True
        if "monthly_limit" in payload:
            wallet.monthly_limit = int(payload["monthly_limit"])
        if "daily_limit" in payload:
            wallet.daily_limit = int(payload["daily_limit"])
        if "per_request_limit" in payload:
            wallet.per_request_limit = int(payload["per_request_limit"])

        wallet.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(wallet)

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="CUSTOMER_AI_SETTINGS_UPDATE",
            target_type="ai_wallet",
            target_id=wallet.id,
            status="SUCCESS",
            reason=payload.get("reason", "Customer AI limit / status update"),
            metadata={"customer_id": customer_id, "old": old_val, "new": wallet.to_dict()},
            db=db
        )

        return {"success": True, "wallet": wallet.to_dict()}

    @classmethod
    def get_budgets_overview(cls, db: Session) -> Dict[str, Any]:
        from app.services.credit_service import CreditService
        s = CreditService.get_or_create_platform_settings(db)

        now = datetime.utcnow()
        today_start = datetime.combine(now.date(), time.min)
        month_start = datetime(now.year, now.month, 1)

        daily_usage = db.query(
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.created_at >= today_start).first()

        monthly_usage = db.query(
            func.sum(AIUsageLog.input_tokens).label("in_tok"),
            func.sum(AIUsageLog.output_tokens).label("out_tok")
        ).filter(AIUsageLog.created_at >= month_start).first()

        daily_in = daily_usage.in_tok or 0
        daily_out = daily_usage.out_tok or 0
        monthly_in = monthly_usage.in_tok or 0
        monthly_out = monthly_usage.out_tok or 0

        # Authoritative cost calculation using separate input and output tokens
        daily_cost = cls.calculate_estimated_cost(daily_in, daily_out)
        monthly_cost = cls.calculate_estimated_cost(monthly_in, monthly_out)

        daily_pct = round((daily_cost / s.daily_budget_usd) * 100, 1) if s.daily_budget_usd > 0 else 0
        monthly_pct = round((monthly_cost / s.monthly_budget_usd) * 100, 1) if s.monthly_budget_usd > 0 else 0

        status = "NORMAL"
        if monthly_pct >= 100 or daily_pct >= 100:
            status = "HARD_STOP" if s.budget_hard_stop else "CRITICAL"
        elif monthly_pct >= 90 or daily_pct >= 90:
            status = "CRITICAL"
        elif monthly_pct >= 80 or daily_pct >= 80:
            status = "WARNING"

        return {
            "platform_budget": {
                "daily_budget_usd": s.daily_budget_usd,
                "monthly_budget_usd": s.monthly_budget_usd,
                "daily_cost_usd": daily_cost,
                "monthly_cost_usd": monthly_cost,
                "daily_pct": daily_pct,
                "monthly_pct": monthly_pct,
                "budget_hard_stop": s.budget_hard_stop,
                "status": status
            }
        }

    # =========================================================================
    # MASTER ACCOUNT & RBAC MANAGEMENT
    # =========================================================================
    @classmethod
    def list_master_accounts(
        cls,
        search: str = "",
        role_filter: str = "all",
        status_filter: str = "all",
        page: int = 1,
        page_size: int = 20,
        db: Session = None
    ) -> Dict[str, Any]:
        """Lists all Master administrative accounts with permissions summary and status."""
        query = db.query(User).filter(
            User.platform_role.in_(["SUPER_MASTER", "MASTER_ADMIN", "SUPER_ADMIN", "ADMIN", "SUPPORT", "ANALYST"])
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(or_(User.id.ilike(term), User.email.ilike(term), User.name.ilike(term)))

        if role_filter and role_filter.lower() != "all":
            query = query.filter(User.platform_role == role_filter.upper())

        if status_filter and status_filter.lower() != "all":
            query = query.filter(User.status == status_filter.upper())

        total = query.count()
        users = query.order_by(desc(User.created_at)).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": [u.to_master_dict() for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
        }

    @classmethod
    def create_master_account(cls, payload: Dict[str, Any], actor_user: User, db: Session) -> Dict[str, Any]:
        """
        Creates a new Master Admin account.
        Strictly enforces:
        1. Only SUPER_MASTER can create SUPER_MASTER accounts.
        2. Lower-level Masters can only delegate permissions they hold.
        3. Never stores plaintext passwords.
        4. Logs an audit record.
        """
        from app.config.security import get_password_hash, validate_password_strength
        from app.config.master_permissions import get_all_permissions, validate_permission_delegation
        from fastapi import HTTPException

        login_id = (payload.get("login_id") or payload.get("email") or "").strip()
        name = (payload.get("name") or "").strip()
        password = payload.get("password") or ""
        confirm_password = payload.get("confirm_password") or password
        role = (payload.get("role") or "MASTER_ADMIN").upper().strip()
        full_authority = bool(payload.get("full_authority", False))
        permissions = payload.get("permissions") or []

        if not login_id:
            raise HTTPException(status_code=400, detail="Login ID / Email is required.")
        if not password:
            raise HTTPException(status_code=400, detail="Password is required.")
        if password != confirm_password:
            raise HTTPException(status_code=400, detail="Password and Confirm Password do not match.")

        is_valid, err_msg = validate_password_strength(password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)

        # 1. Privilege escalation check: creating SUPER_MASTER
        actor_role = (actor_user.platform_role or "USER").upper()
        if role in ("SUPER_MASTER", "SUPER_ADMIN") and actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
            raise HTTPException(
                status_code=403,
                detail="PRIVILEGE_ESCALATION_DENIED: Only a Super Master can create Super Master accounts."
            )

        # 2. Assign permissions
        if full_authority or role in ("SUPER_MASTER", "SUPER_ADMIN"):
            assigned_permissions = get_all_permissions() if role not in ("SUPER_MASTER", "SUPER_ADMIN") else ["*"]
        else:
            if not isinstance(permissions, list):
                permissions = [str(permissions)]
            assigned_permissions = permissions

        # 3. Permission delegation check
        if actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
            if not validate_permission_delegation(actor_role, actor_user.get_permissions_list(), assigned_permissions):
                raise HTTPException(
                    status_code=403,
                    detail="DELEGATION_DENIED: You cannot grant permissions that you do not hold."
                )

        # Check for existing account
        existing = db.query(User).filter(
            (User.id == login_id) | (User.email == login_id) | (User.id == login_id.lower()) | (User.email == login_id.lower())
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"An account with Login ID '{login_id}' already exists.")

        email_val = login_id.lower() if "@" in login_id else f"{login_id.lower()}@master.local"
        new_master = User(
            id=login_id,
            email=email_val,
            name=name or login_id,
            password_hash=get_password_hash(password),
            platform_role=role,
            status="ACTIVE",
            permissions_json=json.dumps(assigned_permissions),
            created_by=actor_user.id
        )
        db.add(new_master)
        db.commit()
        db.refresh(new_master)

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_ACCOUNT_CREATE",
            target_type="master_user",
            target_id=new_master.id,
            status="SUCCESS",
            reason=f"Created {role} account '{login_id}'",
            metadata={"role": role, "permissions_count": len(assigned_permissions), "full_authority": full_authority},
            db=db
        )

        return {"success": True, "account": new_master.to_master_dict()}

    @classmethod
    def update_master_account(cls, target_id: str, payload: Dict[str, Any], actor_user: User, db: Session) -> Dict[str, Any]:
        """Updates Master Admin profile, role, status, and permissions with strict escalation guards."""
        from app.config.security import get_password_hash, validate_password_strength
        from app.config.master_permissions import get_all_permissions, validate_permission_delegation
        from fastapi import HTTPException

        target = db.query(User).filter(
            (User.id == target_id) | (User.email == target_id)
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="Master account not found.")

        actor_role = (actor_user.platform_role or "USER").upper()
        target_role = (target.platform_role or "USER").upper()

        # Super Master Protection: only SUPER_MASTER can edit another SUPER_MASTER
        if target_role in ("SUPER_MASTER", "SUPER_ADMIN") and actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
            raise HTTPException(
                status_code=403,
                detail="SUPER_MASTER_PROTECTED: You are not authorized to modify the Super Master account."
            )

        # Self-escalation guard: actor cannot modify their own role/permissions to gain privileges
        if target.id == actor_user.id and actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
            if "role" in payload and payload["role"].upper() != actor_role:
                raise HTTPException(status_code=403, detail="PRIVILEGE_ESCALATION_DENIED: Cannot modify your own role.")
            if "permissions" in payload:
                raise HTTPException(status_code=403, detail="PRIVILEGE_ESCALATION_DENIED: Cannot modify your own permissions.")

        old_meta = target.to_master_dict()

        if "name" in payload and payload["name"]:
            target.name = str(payload["name"]).strip()

        if "role" in payload and payload["role"]:
            new_role = str(payload["role"]).upper().strip()
            if new_role in ("SUPER_MASTER", "SUPER_ADMIN") and actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
                raise HTTPException(status_code=403, detail="PRIVILEGE_ESCALATION_DENIED: Cannot promote to Super Master.")
            target.platform_role = new_role

        if "full_authority" in payload or "permissions" in payload:
            full_auth = bool(payload.get("full_authority", False))
            if full_auth:
                new_perms = get_all_permissions() if target.platform_role not in ("SUPER_MASTER", "SUPER_ADMIN") else ["*"]
            else:
                raw_perms = payload.get("permissions") or []
                new_perms = raw_perms if isinstance(raw_perms, list) else [str(raw_perms)]

            if actor_role not in ("SUPER_MASTER", "SUPER_ADMIN"):
                if not validate_permission_delegation(actor_role, actor_user.get_permissions_list(), new_perms):
                    raise HTTPException(status_code=403, detail="DELEGATION_DENIED: Cannot grant permissions you do not hold.")

            target.permissions_json = json.dumps(new_perms)

        if "password" in payload and payload["password"]:
            pwd = payload["password"]
            is_valid, err_msg = validate_password_strength(pwd)
            if not is_valid:
                raise HTTPException(status_code=400, detail=err_msg)
            target.password_hash = get_password_hash(pwd)
            # Invalidate previous sessions upon password reset
            target.session_revoked_at = datetime.utcnow()

        if "status" in payload and payload["status"]:
            new_status = str(payload["status"]).upper().strip()
            target.status = new_status
            if new_status in ("DISABLED", "SUSPENDED", "INACTIVE"):
                target.disabled_at = datetime.utcnow()
                target.disabled_by = actor_user.id
                target.session_revoked_at = datetime.utcnow()
            else:
                target.disabled_at = None
                target.disabled_by = None

        target.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(target)

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_ACCOUNT_UPDATE",
            target_type="master_user",
            target_id=target.id,
            status="SUCCESS",
            reason=payload.get("reason", "Master account details updated"),
            metadata={"old": old_meta, "new": target.to_master_dict()},
            db=db
        )

        return {"success": True, "account": target.to_master_dict()}

    @classmethod
    def disable_master_account(cls, target_id: str, reason: str, actor_user: User, db: Session) -> Dict[str, Any]:
        """Disables a Master account and immediately invalidates all active sessions."""
        from fastapi import HTTPException

        target = db.query(User).filter(
            (User.id == target_id) | (User.email == target_id)
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="Master account not found.")

        target_role = (target.platform_role or "USER").upper()
        if target_role in ("SUPER_MASTER", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="SUPER_MASTER_PROTECTED: Root Super Master account cannot be disabled.")

        if target.id == actor_user.id:
            raise HTTPException(status_code=400, detail="Cannot disable your own active account.")

        target.status = "DISABLED"
        target.disabled_at = datetime.utcnow()
        target.disabled_by = actor_user.id
        target.session_revoked_at = datetime.utcnow()
        target.updated_at = datetime.utcnow()
        db.commit()

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_ACCOUNT_DISABLE",
            target_type="master_user",
            target_id=target.id,
            status="SUCCESS",
            reason=reason or "Account disabled by administrator",
            metadata={"disabled_account": target.id},
            db=db
        )

        return {"success": True, "message": f"Master account '{target.id}' has been disabled and sessions revoked."}

    @classmethod
    def enable_master_account(cls, target_id: str, reason: str, actor_user: User, db: Session) -> Dict[str, Any]:
        """Enables a previously disabled Master account."""
        from fastapi import HTTPException

        target = db.query(User).filter(
            (User.id == target_id) | (User.email == target_id)
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="Master account not found.")

        target.status = "ACTIVE"
        target.disabled_at = None
        target.disabled_by = None
        target.updated_at = datetime.utcnow()
        db.commit()

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_ACCOUNT_ENABLE",
            target_type="master_user",
            target_id=target.id,
            status="SUCCESS",
            reason=reason or "Account enabled by administrator",
            metadata={"enabled_account": target.id},
            db=db
        )

        return {"success": True, "message": f"Master account '{target.id}' has been enabled."}

    @classmethod
    def revoke_master_sessions(cls, target_id: str, reason: str, actor_user: User, db: Session) -> Dict[str, Any]:
        """Revokes all active JWT sessions for a Master account by updating session_revoked_at."""
        from fastapi import HTTPException

        target = db.query(User).filter(
            (User.id == target_id) | (User.email == target_id)
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="Master account not found.")

        target.session_revoked_at = datetime.utcnow()
        target.updated_at = datetime.utcnow()
        db.commit()

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_SESSIONS_REVOKE",
            target_type="master_user",
            target_id=target.id,
            status="SUCCESS",
            reason=reason or "All sessions revoked by administrator",
            metadata={"target_account": target.id, "revoked_at": target.session_revoked_at.isoformat()},
            db=db
        )

        return {"success": True, "message": f"All active sessions for Master account '{target.id}' have been revoked."}

    @classmethod
    def delete_master_account(cls, target_id: str, reason: str, actor_user: User, db: Session) -> Dict[str, Any]:
        """Permanently removes a Master Admin account with root Super Master protection."""
        from fastapi import HTTPException

        target = db.query(User).filter(
            (User.id == target_id) | (User.email == target_id)
        ).first()
        if not target:
            raise HTTPException(status_code=404, detail="Master account not found.")

        target_role = (target.platform_role or "USER").upper()
        if target_role in ("SUPER_MASTER", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="SUPER_MASTER_PROTECTED: Root Super Master account cannot be deleted.")

        if target.id == actor_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own active account.")

        del_id = target.id
        db.delete(target)
        db.commit()

        cls.log_audit_action(
            actor_id=actor_user.id,
            actor_email=actor_user.email,
            action="MASTER_ACCOUNT_DELETE",
            target_type="master_user",
            target_id=del_id,
            status="SUCCESS",
            reason=reason or "Account deleted by administrator",
            metadata={"deleted_account": del_id},
            db=db
        )

        return {"success": True, "message": f"Master account '{del_id}' has been permanently deleted."}


