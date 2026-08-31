import os
import json
import shutil
import re
import io
import uuid
import copy
import zipfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body, Response, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership, require_project_owner
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.project_invitation import ProjectInvitation
from app.models.user import User
from app.models.notification import Notification
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.config.settings import settings
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService

from app.services.audit_rules import evaluate_site_audit_rules

router = APIRouter()
pdf_gen = PDFReportGenerator()

def get_export_timestamp() -> str:
    return datetime.now().strftime("%d-%m-%y-%I-%M-%p")

def sanitize_filename_part(name: str) -> str:
    if not name:
        return "SEO-Project"
    cleaned = re.sub(r'[^\w\s-]', '', name).strip()
    result = re.sub(r'[-\s]+', '-', cleaned)
    return result or "SEO-Project"

def get_project_metrics(domain: str, project_id: Optional[str] = None) -> dict:
    website_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
    latest_path = os.path.join(website_dir, "latest.json")
    
    metrics = {
        "last_crawl": None,
        "crawl_status": "Not Crawled",
        "health_score": None,
        "pages_count": 0,
        "issues_count": 0,
        "critical_issues": 0,
        "warnings": 0,
        "keywords_count": 0,
        "backlinks_count": 0,
        "internal_links_count": 0,
        "has_crawled": False
    }

    if not os.path.exists(latest_path):
        return metrics

    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
        
        crawl_dir = normalize_stored_path(latest.get("path"))
        if crawl_dir and os.path.exists(crawl_dir):
            metadata_path = os.path.join(crawl_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as mf:
                    meta = json.load(mf)
                    metrics["last_crawl"] = meta.get("timestamp")
                    metrics["crawl_status"] = "Completed"
                    metrics["pages_count"] = meta.get("pages_crawled", 0)
                    metrics["issues_count"] = meta.get("total_issues", 0)
                    metrics["critical_issues"] = meta.get("critical_issues", 0)
                    metrics["warnings"] = meta.get("warning_issues", 0)
                    metrics["internal_links_count"] = meta.get("internal_links_count", 0)
                    metrics["has_crawled"] = True

            pages_path = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_path):
                with open(pages_path, "r") as pf:
                    pages_data = json.load(pf)
                eval_res = evaluate_site_audit_rules(pages_data)
                metrics["health_score"] = eval_res.get("health_score")
                metrics["issues_count"] = len(eval_res.get("issues", []))
                metrics["critical_issues"] = eval_res.get("summary", {}).get("critical_errors", 0)
                metrics["warnings"] = eval_res.get("summary", {}).get("warnings", 0)

            keywords_path = os.path.join(crawl_dir, "keywords.json")
            if os.path.exists(keywords_path):
                with open(keywords_path, "r") as kf:
                    kw_data = json.load(kf)
                    metrics["keywords_count"] = len(kw_data) if isinstance(kw_data, list) else 0

            backlinks_path = os.path.join(crawl_dir, "backlinks.json")
            if os.path.exists(backlinks_path):
                with open(backlinks_path, "r") as bf:
                    bl_data = json.load(bf)
                    metrics["backlinks_count"] = len(bl_data) if isinstance(bl_data, list) else 0
    except Exception as e:
        print(f"[PROJECTS ROUTER] Exception loading metrics for {domain}: {e}", flush=True)

    return metrics

def load_project_full_datasets(domain: str, project_id: Optional[str] = None):
    website_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
    latest_path = os.path.join(website_dir, "latest.json")

    metadata, pages, keywords, rankings, backlinks, internal_links, competitors, issues, crawls = {}, [], [], [], [], [], [], [], []

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            if crawl_dir and os.path.exists(crawl_dir):
                meta_p = os.path.join(crawl_dir, "metadata.json")
                pages_p = os.path.join(crawl_dir, "pages.json")
                issues_p = os.path.join(crawl_dir, "issues.json")
                links_p = os.path.join(crawl_dir, "internal_links.json")
                kw_p = os.path.join(crawl_dir, "keywords.json")
                bl_p = os.path.join(crawl_dir, "backlinks.json")
                rk_p = os.path.join(crawl_dir, "rankings.json")
                comp_p = os.path.join(crawl_dir, "competitors.json")

                if os.path.exists(meta_p): metadata = json.load(open(meta_p))
                if os.path.exists(pages_p): pages = json.load(open(pages_p))
                if os.path.exists(issues_p): issues = json.load(open(issues_p))
                if os.path.exists(links_p): internal_links = json.load(open(links_p))
                if os.path.exists(kw_p): keywords = json.load(open(kw_p))
                if os.path.exists(bl_p): backlinks = json.load(open(bl_p))
                if os.path.exists(rk_p): rankings = json.load(open(rk_p))
                if os.path.exists(comp_p): competitors = json.load(open(comp_p))
        except Exception as e:
            print(f"[PROJECT DATASET LOAD ERROR] {e}", flush=True)

    crawls_dir = os.path.join(website_dir, "crawls")
    if os.path.exists(crawls_dir):
        try:
            for folder in os.listdir(crawls_dir):
                meta_path = os.path.join(crawls_dir, folder, "metadata.json")
                if os.path.exists(meta_path):
                    crawls.append(json.load(open(meta_path)))
        except Exception:
            pass

    return metadata, pages, keywords, rankings, backlinks, internal_links, competitors, issues, crawls

@router.get("")
@router.get("/")
def get_projects(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns ONLY authorized projects for the authenticated user based on ProjectMemberships.
    Categorizes role into OWNER ('Lead') and MEMBER ('Team Member').
    """
    email = user_id.strip().lower()
    
    # Query active memberships for this user
    memberships = db.query(ProjectMembership).filter(
        ProjectMembership.user_id == email,
        ProjectMembership.status == "ACTIVE"
    ).all()

    result = []
    for m in memberships:
        p = db.query(Project).filter(Project.id == m.project_id).first()
        if not p:
            continue
        
        metrics = get_project_metrics(p.domain, project_id=p.id)
        p_dict = {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "description": p.description or "",
            "industry": p.industry or "",
            "services": getattr(p, "services", "") or "",
            "service_areas": getattr(p, "service_areas", "") or "",
            "notes": p.notes or "",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "user_role": m.role, # OWNER or MEMBER
            "role_label": "Lead" if m.role == "OWNER" else "Team Member",
            **metrics
        }
        result.append(p_dict)

    return result

@router.post("")
@router.post("/")
def create_project(
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Creates a new project and assigns the creator user as OWNER.
    """
    email = user_id.strip().lower()
    url_val = (payload.get('url') or payload.get('domain') or '').strip()
    name_val = (payload.get('name') or 'New SEO Project').strip()
    description = payload.get('description', '').strip()
    industry = payload.get('industry', '').strip()
    services = payload.get('services', '').strip()
    service_areas = payload.get('service_areas', '').strip()
    notes = payload.get('notes', '').strip()

    if not url_val:
        raise HTTPException(status_code=400, detail="Website URL or domain is required.")

    if not url_val.startswith(("http://", "https://")):
        url_val = "https://" + url_val

    safe_domain = get_sanitized_domain(url_val)

    # Check if caller already has a project matching this domain
    user_memberships = db.query(ProjectMembership).filter(
        ProjectMembership.user_id == email,
        ProjectMembership.status == "ACTIVE"
    ).all()

    for m in user_memberships:
        proj = db.query(Project).filter(Project.id == m.project_id).first()
        if proj and (get_sanitized_domain(proj.url) == safe_domain or proj.domain == safe_domain):
            return {
                "status": "exists",
                "message": f"Project for '{safe_domain}' already exists in your workspace.",
                "project": {
                    "id": proj.id,
                    "name": proj.name,
                    "url": proj.url,
                    "domain": proj.domain,
                    "industry": proj.industry or "",
                    "services": getattr(proj, "services", "") or "",
                    "service_areas": getattr(proj, "service_areas", "") or "",
                    "user_role": m.role,
                    "role_label": "Lead" if m.role == "OWNER" else "Team Member",
                    **get_project_metrics(proj.domain)
                }
            }

    new_proj = Project(
        name=name_val,
        url=url_val,
        description=description,
        industry=industry,
        services=services,
        service_areas=service_areas,
        notes=notes
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)

    # Assign caller as OWNER
    membership = ProjectMembership(
        user_id=email,
        project_id=new_proj.id,
        role="OWNER",
        status="ACTIVE"
    )
    db.add(membership)
    db.commit()

    m = get_project_metrics(new_proj.domain)
    return {
        "status": "created",
        "message": "Project created successfully.",
        "project": {
            "id": new_proj.id,
            "name": new_proj.name,
            "url": new_proj.url,
            "domain": new_proj.domain,
            "description": new_proj.description or "",
            "industry": new_proj.industry or "",
            "services": getattr(new_proj, "services", "") or "",
            "service_areas": getattr(new_proj, "service_areas", "") or "",
            "user_role": "OWNER",
            "role_label": "Lead",
            "created_at": new_proj.created_at.isoformat() if new_proj.created_at else None,
            **m
        }
    }

@router.get("/{project_id}")
def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    membership = get_user_membership(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()

    m = get_project_metrics(p.domain)
    return {
        "id": p.id,
        "name": p.name,
        "url": p.url,
        "domain": p.domain,
        "description": p.description or "",
        "industry": p.industry or "",
        "services": getattr(p, "services", "") or "",
        "service_areas": getattr(p, "service_areas", "") or "",
        "notes": p.notes or "",
        "user_role": membership.role,
        "role_label": "Lead" if membership.role == "OWNER" else "Team Member",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        **m
    }

# TEAM MANAGEMENT ENDPOINTS
@router.get("/{project_id}/team")
def get_project_team(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns active team members and pending invitations for a project.
    Allowed for both Lead (OWNER) and Team Members (MEMBER).
    """
    membership = get_user_membership(db, user_id, project_id)
    
    # Active memberships
    memberships = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.status == "ACTIVE"
    ).all()

    members = []
    for m in memberships:
        u = db.query(User).filter(User.email == m.user_id).first()
        masked = m.user_id[0] + "***" + m.user_id[m.user_id.find("@"):] if "@" in m.user_id else "user***@gmail.com"
        members.append({
            "membership_id": m.id,
            "user_id": m.user_id,
            "email": m.user_id,
            "masked_email": masked,
            "name": u.name if u else "SEO Team Member",
            "picture": u.picture if u else None,
            "role": m.role, # OWNER or MEMBER
            "role_label": "Lead (Owner)" if m.role == "OWNER" else "Team Member",
            "status": m.status,
            "joined_at": m.created_at.isoformat() if m.created_at else None
        })

    # Pending invitations
    invitations = db.query(ProjectInvitation).filter(
        ProjectInvitation.project_id == project_id,
        ProjectInvitation.status == "PENDING"
    ).all()

    invites = [inv.to_dict() for inv in invitations]

    return {
        "project_id": project_id,
        "caller_role": membership.role,
        "is_owner": membership.role == "OWNER",
        "total_members": len(members),
        "member_count": len([m for m in members if m["role"] == "MEMBER"]),
        "max_team_members": 2,
        "members": members,
        "pending_invitations": invites
    }

@router.get("/users/search")
def search_users(
    q: str = Query(""),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Searches registered platform accounts by name or email.
    Does NOT search external Google Search Console or third-party identities.
    """
    clean_q = (q or "").strip().lower()
    if len(clean_q) < 2:
        return {"users": []}

    matching = db.query(User).filter(
        (User.email.ilike(f"%{clean_q}%")) | (User.name.ilike(f"%{clean_q}%"))
    ).limit(10).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name or u.email.split("@")[0],
                "picture": u.picture
            } for u in matching
        ]
    }


@router.post("/{project_id}/team/invite")
def invite_teammate(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Invites an existing registered platform account to a project internally.
    No email is sent.
    """
    require_project_owner(db, user_id, project_id)

    invited_email = (payload.get("email") or "").strip().lower()
    if not invited_email or "@" not in invited_email:
        raise HTTPException(status_code=400, detail="A valid platform account email is required.")

    caller_email = user_id.strip().lower()
    if invited_email == caller_email:
        raise HTTPException(status_code=400, detail="You cannot invite yourself.")

    # 1. Search target account in registered User database
    target_user = db.query(User).filter(
        (User.email.ilike(invited_email)) | (User.id.ilike(invited_email))
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="Account not found. The user must create an SEO Intelligence Platform account before they can be invited to a project."
        )

    if target_user.id.lower() == caller_email or target_user.email.lower() == caller_email:
        raise HTTPException(status_code=400, detail="You cannot invite yourself.")

    # 2. Check existing active project membership
    existing_m = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        (ProjectMembership.user_id == target_user.email) | (ProjectMembership.user_id == target_user.id),
        ProjectMembership.status == "ACTIVE"
    ).first()

    if existing_m:
        raise HTTPException(status_code=400, detail="This user is already a member of this project.")

    # 3. Check team member limit (1 Lead + max 2 Members)
    current_members = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.role == "MEMBER",
        ProjectMembership.status == "ACTIVE"
    ).count()

    if current_members >= 2:
        raise HTTPException(
            status_code=400,
            detail="Team member limit reached. Each project supports 1 Lead + max 2 Team Members."
        )

    # 4. Check for existing pending invitation
    existing_inv = db.query(ProjectInvitation).filter(
        ProjectInvitation.project_id == project_id,
        (ProjectInvitation.invited_email == target_user.email) | (ProjectInvitation.invited_user_id == target_user.id),
        ProjectInvitation.status == "PENDING"
    ).first()

    if existing_inv:
        raise HTTPException(status_code=400, detail="Invitation already pending.")

    assigned_role = payload.get("role", "MEMBER")
    permissions_data = payload.get("permissions")
    permissions_str = json.dumps(permissions_data) if permissions_data else None

    project = db.query(Project).filter(Project.id == project_id).first()
    project_name = project.name if project else "SEO Project"

    inviter_user = db.query(User).filter((User.id == user_id) | (User.email == user_id)).first()
    inviter_name = inviter_user.name if inviter_user else (user_id or "Project Owner")

    # Atomic Transaction: Create ProjectInvitation AND Notification together
    try:
        invitation = ProjectInvitation(
            id=str(uuid.uuid4()),
            project_id=project_id,
            invited_email=target_user.email,
            invited_user_id=target_user.id,
            invited_by_user_id=user_id,
            role=assigned_role,
            permissions_json=permissions_str,
            status="PENDING",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invitation)
        db.flush()

        # Create persistent Notification for recipient target_user.id
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=target_user.id,
            project_id=project_id,
            invitation_id=invitation.id,
            title="Project Team Invitation",
            message=f"You have been invited to join '{project_name}' by {inviter_name}.",
            type="TEAM_INVITATION",
            status="UNREAD",
            data_json=json.dumps({
                "invitation_id": invitation.id,
                "project_id": project_id,
                "project_name": project_name,
                "inviter_user_id": user_id,
                "inviter_name": inviter_name,
                "inviter_email": inviter_user.email if inviter_user else user_id,
                "role": assigned_role
            })
        )
        db.add(notif)
        db.commit()
        db.refresh(invitation)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create internal team invitation and notification: {str(exc)}"
        )

    return {
        "status": "success",
        "message": f"Team invitation sent to {target_user.name or target_user.email}.",
        "invitation": invitation.to_dict()
    }


@router.post("/{project_id}/team/remove")
def remove_teammate(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Revokes access for a teammate from the project.
    OWNER ONLY endpoint.
    """
    require_project_owner(db, user_id, project_id)

    target_user_id = (payload.get("user_id") or payload.get("email") or "").strip().lower()
    if not target_user_id:
        raise HTTPException(status_code=400, detail="Target user email is required.")

    if target_user_id == user_id.strip().lower():
        raise HTTPException(status_code=400, detail="Project Owner access cannot be removed. Transfer ownership first if needed.")

    m = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == target_user_id,
        ProjectMembership.status == "ACTIVE"
    ).first()

    if not m:
        raise HTTPException(status_code=404, detail="Active membership for this user was not found on this project.")

    m.status = "REVOKED"
    db.commit()

    return {
        "status": "success",
        "message": f"Project access for '{target_user_id}' has been revoked cleanly."
    }


@router.post("/{project_id}/team/cancel-invite")
def cancel_invitation(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Cancels a pending invitation and updates corresponding notification state.
    OWNER ONLY endpoint.
    """
    require_project_owner(db, user_id, project_id)
    invitation_id = payload.get("invitation_id")
    
    invite = db.query(ProjectInvitation).filter(
        ProjectInvitation.id == invitation_id,
        ProjectInvitation.project_id == project_id
    ).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Pending invitation not found.")

    invite.status = "CANCELLED"

    # Also update any associated notification records
    notifs = db.query(Notification).filter(Notification.invitation_id == invitation_id).all()
    for n in notifs:
        if n.data_json:
            try:
                d = json.loads(n.data_json)
                d["status"] = "CANCELLED"
                n.data_json = json.dumps(d)
            except Exception:
                pass

    db.commit()

    return {
        "status": "success",
        "message": "Invitation cancelled successfully."
    }

    return {"status": "success", "message": "Pending invitation cancelled."}

@router.put("/{project_id}")
def update_project(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    require_project_owner(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()

    if 'name' in payload and payload['name'].strip():
        p.name = payload['name'].strip()
    if 'url' in payload and payload['url'].strip():
        new_url = payload['url'].strip()
        if not new_url.startswith(("http://", "https://")):
            new_url = "https://" + new_url
        p.url = new_url
    if 'description' in payload:
        p.description = payload['description'].strip()
    if 'industry' in payload:
        p.industry = payload['industry'].strip()
    if 'services' in payload:
        p.services = payload['services'].strip()
    if 'service_areas' in payload:
        p.service_areas = payload['service_areas'].strip()
    if 'notes' in payload:
        p.notes = payload['notes'].strip()

    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)

    m = get_project_metrics(p.domain)
    return {
        "status": "updated",
        "project": {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "description": p.description or "",
            "industry": p.industry or "",
            "services": getattr(p, "services", "") or "",
            "service_areas": getattr(p, "service_areas", "") or "",
            "notes": p.notes or "",
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            **m
        }
    }

@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    require_project_owner(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()

    domain = p.domain
    safe_domain = get_sanitized_domain(domain)

    db.delete(p)
    db.commit()

    website_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
    if os.path.exists(website_dir):
        try:
            shutil.rmtree(website_dir)
        except Exception as e:
            print(f"[PROJECTS API] Error deleting storage directory {website_dir}: {e}", flush=True)

    return {"status": "success", "message": f"Project '{p.name}' deleted cleanly."}

@router.get("/{project_id}/summary")
def get_project_summary(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()

    safe_domain = get_sanitized_domain(p.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        return {"status": "empty", "message": "No crawl data available yet."}
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
        crawl_dir = normalize_stored_path(latest.get("path"))
        metadata_path = os.path.join(crawl_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as mf:
                return {"status": "success", "latest_crawl": json.load(mf)}
    except Exception as e:
        print(f"[PROJECTS API] Exception reading snapshot: {e}", flush=True)
        
    return {"status": "error", "message": "Failed to read crawl data"}


DEFAULT_CRAWL_CONFIG = {
    "ignore_tracking_parameters": True,
    "target_countries": [],
    "audit_modules": {
        "technical_http": True,
        "metadata": True,
        "headings": True,
        "images": True,
        "links": True,
        "canonicals_robots": True
    },
    "performance_analysis": {
        "available": False,
        "reason": "Core Web Vitals and Lighthouse performance analysis are currently unavailable for this crawl run."
    },
    "scope_type": "entire_domain",
    "custom_path": "",
    "max_pages": 5000,
    "max_depth": 0,
    "request_timeout": 20.0,
    "crawl_delay_ms": 500,
    "respect_robots_txt": True,
    "discover_sitemap": True,
    "discover_internal_links": True,
    "user_agent": "SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)",
    "follow_redirects": True,
    "exclude_patterns": ["/admin/*", "/login/*", "/cart/*"]
}

@router.get("/{project_id}/crawl-config")
def get_crawl_config(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    config = copy.deepcopy(DEFAULT_CRAWL_CONFIG)
    if p.crawl_config:
        try:
            saved_cfg = json.loads(p.crawl_config)
            if isinstance(saved_cfg, dict):
                for k, v in saved_cfg.items():
                    if k == "audit_modules" and isinstance(v, dict):
                        config["audit_modules"].update(v)
                    else:
                        config[k] = v
        except Exception:
            pass

    return {
        "status": "success",
        "project_id": project_id,
        "config": config
    }

@router.patch("/{project_id}/crawl-config")
@router.put("/{project_id}/crawl-config")
def update_crawl_config(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    current_config = copy.deepcopy(DEFAULT_CRAWL_CONFIG)
    if p.crawl_config:
        try:
            saved_cfg = json.loads(p.crawl_config)
            if isinstance(saved_cfg, dict):
                for k, v in saved_cfg.items():
                    if k == "audit_modules" and isinstance(v, dict):
                        current_config["audit_modules"].update(v)
                    else:
                        current_config[k] = v
        except Exception:
            pass

    for k, v in payload.items():
        if k == "audit_modules" and isinstance(v, dict):
            current_config["audit_modules"].update(v)
        else:
            current_config[k] = v

    p.crawl_config = json.dumps(current_config)
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)

    return {
        "status": "success",
        "project_id": project_id,
        "config": current_config
    }

