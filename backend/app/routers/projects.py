import os
import json
import shutil
import re
import io
import uuid
import zipfile
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership, require_project_owner
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.project_invitation import ProjectInvitation
from app.models.user import User
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService

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

def get_project_metrics(domain: str) -> dict:
    safe_domain = get_sanitized_domain(domain)
    website_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
    latest_path = os.path.join(website_dir, "latest.json")
    
    metrics = {
        "last_crawl": None,
        "crawl_status": "Not Crawled",
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

def load_project_full_datasets(domain: str):
    safe_domain = get_sanitized_domain(domain)
    website_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
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
    
    # Auto-assign legacy projects to current user as OWNER if no memberships exist yet
    all_projs = db.query(Project).all()
    for p in all_projs:
        count = db.query(ProjectMembership).filter(
            ProjectMembership.project_id == p.id,
            ProjectMembership.status == "ACTIVE"
        ).count()
        if count == 0:
            m = ProjectMembership(
                user_id=email,
                project_id=p.id,
                role="OWNER",
                status="ACTIVE"
            )
            db.add(m)
    db.commit()

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
        
        metrics = get_project_metrics(p.domain)
        p_dict = {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "description": p.description or "",
            "industry": p.industry or "",
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
    notes = payload.get('notes', '').strip()

    if not url_val:
        raise HTTPException(status_code=400, detail="Website URL or domain is required.")

    if not url_val.startswith(("http://", "https://")):
        url_val = "https://" + url_val

    safe_domain = get_sanitized_domain(url_val)

    existing = db.query(Project).all()
    for proj in existing:
        if get_sanitized_domain(proj.url) == safe_domain or proj.domain == safe_domain:
            # Ensure membership exists for caller
            m = db.query(ProjectMembership).filter(
                ProjectMembership.project_id == proj.id,
                ProjectMembership.user_id == email
            ).first()
            if not m:
                m = ProjectMembership(
                    user_id=email,
                    project_id=proj.id,
                    role="OWNER",
                    status="ACTIVE"
                )
                db.add(m)
                db.commit()

            return {
                "status": "exists",
                "message": f"Project for '{safe_domain}' already exists.",
                "project": {
                    "id": proj.id,
                    "name": proj.name,
                    "url": proj.url,
                    "domain": proj.domain,
                    "user_role": "OWNER",
                    "role_label": "Lead",
                    **get_project_metrics(proj.domain)
                }
            }

    new_proj = Project(
        name=name_val,
        url=url_val,
        description=description,
        industry=industry,
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

@router.post("/{project_id}/team/invite")
def invite_teammate(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Invites a teammate by Google Email.
    OWNER ONLY endpoint. Enforces maximum 2 Team Members limit per project.
    """
    require_project_owner(db, user_id, project_id)

    invited_email = (payload.get("email") or "").strip().lower()
    if not invited_email or "@" not in invited_email:
        raise HTTPException(status_code=400, detail="Valid Google account email is required for invitation.")

    if invited_email == user_id.strip().lower():
        raise HTTPException(status_code=400, detail="You are already the Lead/Owner of this project.")

    # Check team limit (1 Owner + max 2 Members)
    current_members = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.role == "MEMBER",
        ProjectMembership.status == "ACTIVE"
    ).count()

    if current_members >= 2:
        raise HTTPException(
            status_code=400,
            detail="Team member limit reached. Each project supports 1 Lead + max 2 Team Members (Total 3 users per project)."
        )

    # Check existing membership
    existing_m = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == invited_email,
        ProjectMembership.status == "ACTIVE"
    ).first()

    if existing_m:
        raise HTTPException(status_code=400, detail=f"User '{invited_email}' is already an active member of this project.")

    # Upsert pending invitation record
    invitation = db.query(ProjectInvitation).filter(
        ProjectInvitation.project_id == project_id,
        ProjectInvitation.invited_email == invited_email,
        ProjectInvitation.status == "PENDING"
    ).first()

    if not invitation:
        invitation = ProjectInvitation(
            id=str(uuid.uuid4()),
            project_id=project_id,
            invited_email=invited_email,
            invited_by_user_id=user_id,
            role="MEMBER",
            status="PENDING",
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

    return {
        "status": "success",
        "message": f"Invitation sent to Google account {invited_email}.",
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
    Cancels a pending invitation.
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

    invite.status = "REVOKED"
    db.commit()

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
