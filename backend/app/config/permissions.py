"""
Project authorization and membership verification module.
Enforces strict multi-tenant project isolation and prevents unauthorized cross-tenant data access.
"""
from typing import List
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.user import User

def get_user_id_aliases(db: Session, user_id: str) -> List[str]:
    """Resolves user_id and email aliases for consistent multi-tenant membership lookups."""
    if not user_id:
        return []
    clean_id = str(user_id).strip().lower()
    user_ids = [user_id, clean_id]
    user = db.query(User).filter(
        (User.id == user_id) | (User.email == user_id) | (User.id == clean_id) | (User.email == clean_id)
    ).first()
    if user:
        if user.id:
            user_ids.extend([user.id, user.id.lower()])
        if user.email:
            user_ids.extend([user.email, user.email.lower()])
    return list(set(user_ids))

def get_user_authorized_project_ids(db: Session, user_id: str) -> List[str]:
    """
    Returns list of project IDs the authenticated user owns or is an active member of.
    Guarantees cross-tenant data isolation for aggregated project queries.
    """
    if not user_id:
        return []
    user_ids = get_user_id_aliases(db, user_id)
    memberships = db.query(ProjectMembership.project_id).filter(
        ProjectMembership.user_id.in_(user_ids),
        ProjectMembership.status == "ACTIVE"
    ).all()
    return [m[0] for m in memberships if m[0]]

def get_user_membership(db: Session, user_id: str, project_id: str) -> ProjectMembership:
    """
    Enforces project isolation and access control.
    Returns the user's active ProjectMembership for the requested project.
    Raises HTTP 400 if project_id is missing or 'all'.
    Raises HTTP 404 if the project does not exist.
    Raises HTTP 403 Forbidden if the user is not an authorized active member.
    """
    if not project_id or not str(project_id).strip():
        raise HTTPException(status_code=400, detail="Project ID is required.")
    
    clean_pid = str(project_id).strip()
    if clean_pid == "all":
        raise HTTPException(
            status_code=400,
            detail="Wildcard project access ('all') is not permitted for individual project endpoints."
        )

    user_ids = get_user_id_aliases(db, user_id)

    # Check active membership
    membership = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == clean_pid,
        ProjectMembership.user_id.in_(user_ids),
        ProjectMembership.status == "ACTIVE"
    ).first()

    if membership:
        return membership

    # Check if project exists in database
    project = db.query(Project).filter(Project.id == clean_pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    raise HTTPException(
        status_code=403,
        detail="Access denied. You are not authorized to access this project's SEO data."
    )

def require_project_owner(db: Session, user_id: str, project_id: str) -> ProjectMembership:
    """
    Enforces Owner-only permission check for administrative actions.
    Raises HTTP 403 Forbidden if caller is a Team Member rather than Project Owner.
    """
    membership = get_user_membership(db, user_id, project_id)
    if not membership or membership.role != "OWNER":
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Project Owner permissions required for this administrative action."
        )
    return membership
