import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.models.notification import Notification
from app.models.user import User

router = APIRouter()

def get_user_identities(db: Session, user_id: str):
    clean_id = user_id.strip().lower()
    user = db.query(User).filter((User.email.ilike(clean_id)) | (User.id.ilike(clean_id))).first()
    identities = [clean_id]
    if user:
        if user.id:
            identities.append(user.id)
            identities.append(user.id.lower())
        if user.email:
            identities.append(user.email)
            identities.append(user.email.lower())
    return list(set(identities))

@router.get("")
@router.get("/")
def get_notifications(
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns notifications and unread notification count for the authenticated recipient user.
    """
    identities = get_user_identities(db, user_id)

    query = db.query(Notification).filter(Notification.user_id.in_(identities))
    if status and isinstance(status, str) and status.upper() in ["UNREAD", "READ"]:
        query = query.filter(Notification.status == status.upper())

    notifications = query.order_by(Notification.created_at.desc()).all()

    unread_count = db.query(Notification).filter(
        Notification.user_id.in_(identities),
        Notification.status == "UNREAD"
    ).count()

    return {
        "user_id": user_id,
        "unread_count": unread_count,
        "total_count": len(notifications),
        "notifications": [n.to_dict() for n in notifications]
    }

@router.post("/{notification_id}/read")
@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Marks a specific notification as READ for the recipient.
    """
    identities = get_user_identities(db, user_id)
    n = db.query(Notification).filter(Notification.id == notification_id).first()

    if not n:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if n.user_id not in identities and n.user_id.lower() not in [i.lower() for i in identities]:
        raise HTTPException(status_code=403, detail="You are not authorized to view this notification.")

    if n.status != "READ":
        n.status = "READ"
        n.read_at = datetime.utcnow()
        db.commit()

    return {
        "status": "success",
        "message": "Notification marked as read.",
        "notification": n.to_dict()
    }

@router.post("/read-all")
def mark_all_notifications_read(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Marks all unread notifications as READ for the authenticated user.
    """
    identities = get_user_identities(db, user_id)
    unreads = db.query(Notification).filter(
        Notification.user_id.in_(identities),
        Notification.status == "UNREAD"
    ).all()

    now = datetime.utcnow()
    for n in unreads:
        n.status = "READ"
        n.read_at = now

    db.commit()

    return {
        "status": "success",
        "message": f"Marked {len(unreads)} notifications as read.",
        "updated_count": len(unreads)
    }
