from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.project_membership import ProjectMembership

def get_user_membership(db: Session, user_id: str, project_id: str) -> ProjectMembership:
    """
    Enforces project isolation and access control.
    Returns the user's active ProjectMembership for the requested project.
    Raises HTTP 403 Forbidden if the user is not an authorized member.
    """
    if not project_id or project_id == "all":
        return None

    # Check existing membership
    membership = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == user_id,
        ProjectMembership.status == "ACTIVE"
    ).first()

    if membership:
        return membership

    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Backward compatibility migration: If project has no owner memberships yet, assign caller as OWNER
    existing_memberships = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project_id,
        ProjectMembership.status == "ACTIVE"
    ).count()

    if existing_memberships == 0:
        new_membership = ProjectMembership(
            user_id=user_id,
            project_id=project_id,
            role="OWNER",
            status="ACTIVE"
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        return new_membership

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
