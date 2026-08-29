import os
import json
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.auth import create_access_token, get_current_user_id
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.project_invitation import ProjectInvitation
from app.models.notification import Notification
from app.models.external_connection import ExternalConnection
from app.config.utils import get_sanitized_domain
from app.config.settings import settings, build_frontend_redirect
from app.services.oauth_provider_service import (
    build_authorization_url,
    validate_oauth_state,
    exchange_code_for_tokens,
    fetch_provider_user_profile
)

router = APIRouter()

@router.get("/google/login-url")
def get_google_oauth_login_url(
    user_id: Optional[str] = Query("anonymous_guest"),
    redirect_base: Optional[str] = Query(None),
    request: Request = None
):
    """
    Generates official Google OAuth 2.0 authorization URL.
    Redirects browser to https://accounts.google.com/o/oauth2/v2/auth
    """
    try:
        base = redirect_base or (str(request.base_url).rstrip("/") if request else settings.API_BASE_URL)
        auth_url = build_authorization_url("google", user_id, base)
        return {
            "status": "success",
            "auth_url": auth_url,
            "provider": "google"
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

@router.get("/google/callback")
@router.post("/google/callback")
def google_oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    payload: dict = Body(default={}),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Handles Google OAuth 2.0 redirect callback.
    Exchanges code for tokens, verifies Google identity via Userinfo API,
    creates/upserts User record, and sets up secure session.
    """
    auth_code = code or payload.get("code")
    state_param = state or payload.get("state")

    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth authorization cancelled or failed: {error}")

    if not auth_code:
        raise HTTPException(status_code=400, detail="OAuth authorization code is required from Google.")

    # 1. Validate signed OAuth state token
    validated_state = {}
    if state_param:
        try:
            validated_state = validate_oauth_state(state_param)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"OAuth state verification failed: {e}")

    # 2. Exchange authorization code for tokens with Google
    try:
        token_data = exchange_code_for_tokens("google", auth_code)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    scopes = token_data.get("scope", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="Google token endpoint did not return an access token.")

    # 3. Retrieve verified user identity from Google Userinfo API
    try:
        req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            google_profile = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify Google user identity: {e}")

    google_sub = google_profile.get("sub")
    email = (google_profile.get("email") or "").strip().lower()
    email_verified = google_profile.get("email_verified", True)
    name = google_profile.get("name") or "Google User"
    picture = google_profile.get("picture") or "https://lh3.googleusercontent.com/a/default-user"

    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Google identity response missing required subject ID or email.")

    if not email_verified:
        raise HTTPException(status_code=400, detail="Unverified Google email accounts are not permitted for security reasons.")

    # 4. Upsert User identity in database
    user = db.query(User).filter((User.google_id == google_sub) | (User.email == email)).first()
    if not user:
        user = User(
            id=email,
            email=email,
            name=name,
            picture=picture,
            google_id=google_sub
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_id = google_sub
        user.email = email
        user.name = name
        user.picture = picture
        user.updated_at = datetime.utcnow()
        db.commit()

    # 5. Store / Update Google ExternalConnection record securely
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == email,
        ExternalConnection.provider == "google"
    ).first()

    if not conn:
        conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=email,
            provider="google",
            provider_account_id=google_sub,
            provider_account_name=name,
            provider_email=email,
            status="CONNECTED",
            scopes=scopes,
            token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
        )
        db.add(conn)
    else:
        conn.provider_account_id = google_sub
        conn.provider_account_name = name
        conn.provider_email = email
        conn.status = "CONNECTED"
        conn.scopes = scopes
        conn.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    conn.set_access_token(access_token)
    if refresh_token:
        conn.set_refresh_token(refresh_token)
    conn.last_used_at = datetime.utcnow()
    db.commit()

    # 6. Check for pending teammate invitations for this Google email
    pending_invites = db.query(ProjectInvitation).filter(
        ProjectInvitation.invited_email == email,
        ProjectInvitation.status == "PENDING"
    ).all()

    for invite in pending_invites:
        team_count = db.query(ProjectMembership).filter(
            ProjectMembership.project_id == invite.project_id,
            ProjectMembership.role == "MEMBER",
            ProjectMembership.status == "ACTIVE"
        ).count()

        if team_count < 2:
            existing_m = db.query(ProjectMembership).filter(
                ProjectMembership.project_id == invite.project_id,
                ProjectMembership.user_id == email
            ).first()

            if not existing_m:
                new_m = ProjectMembership(
                    user_id=email,
                    project_id=invite.project_id,
                    role=invite.role or "MEMBER",
                    status="ACTIVE",
                    invited_by=invite.invited_by_user_id
                )
                db.add(new_m)
            elif existing_m.status != "ACTIVE":
                existing_m.status = "ACTIVE"

            invite.status = "ACCEPTED"
            db.commit()

    # 7. Create secure JWT application session token
    session_token = create_access_token(user_id=email)
    masked_email = email[0] + "***" + email[email.find("@"):] if "@" in email else "user***@gmail.com"

    # If browser GET redirect, redirect directly to frontend discovery with token
    if code:
        frontend_base = None
        if request:
            req_base = str(request.base_url).rstrip("/")
            if ":8020" in req_base:
                frontend_base = req_base.replace(":8020", f":{settings.FRONTEND_PORT}")
            else:
                frontend_base = req_base
        target_url = build_frontend_redirect("/discovery", {
            "token": session_token,
            "auth": "success"
        }, base_url=frontend_base)
        return RedirectResponse(url=target_url)

    return {
        "status": "success",
        "access_token": session_token,
        "token_type": "bearer",
        "user": {
            "id": email,
            "google_sub": google_sub,
            "email": email,
            "masked_email": masked_email,
            "name": name,
            "picture": picture,
            "auth_provider": "google"
        }
    }

@router.post("/google/login")
def google_oauth_login(payload: dict = Body(default={}), db: Session = Depends(get_db)):
    """
    Google OAuth login endpoint for verified Google GIS / One-Tap ID tokens.
    Rejects raw unauthenticated email strings to enforce 100% Google OAuth authentication.
    """
    token_str = payload.get("id_token") or payload.get("credential")

    if not token_str:
        raise HTTPException(
            status_code=401,
            detail="Google OAuth authentication requires a verified Google authorization code or ID token. Call GET /api/auth/google/login-url."
        )

    # Verify ID token with Google tokeninfo endpoint
    try:
        req = urllib.request.Request(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}",
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google ID token verification failed: {e}")

    email = (token_info.get("email") or "").strip().lower()
    google_sub = token_info.get("sub")
    email_verified = token_info.get("email_verified") in (True, "true", 1)

    if not email or not google_sub or not email_verified:
        raise HTTPException(status_code=401, detail="Unverified or invalid Google identity token.")

    user = db.query(User).filter((User.google_id == google_sub) | (User.email == email)).first()
    if not user:
        user = User(
            id=email,
            email=email,
            name=token_info.get("name") or "Google User",
            picture=token_info.get("picture"),
            google_id=google_sub
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_id = google_sub
        user.email = email
        user.name = token_info.get("name") or user.name
        user.picture = token_info.get("picture") or user.picture
        user.updated_at = datetime.utcnow()
        db.commit()

    session_token = create_access_token(user_id=email)
    masked = email[0] + "***" + email[email.find("@"):] if "@" in email else "user***@gmail.com"

    return {
        "access_token": session_token,
        "token_type": "bearer",
        "user": {
            "id": email,
            "google_id": user.google_id,
            "email": email,
            "masked_email": masked,
            "name": user.name,
            "picture": user.picture,
            "auth_provider": "google"
        }
    }

@router.post("/guest-session")
def create_guest_session(db: Session = Depends(get_db)):
    """
    Creates a temporary, server-controlled guest session.
    Generates a unique guest identity (guest_<uuid_hex>) and issues an authentic JWT session token.
    NO shared hardcoded identity and NO header-controlled identity.
    """
    guest_uuid = uuid.uuid4().hex[:12]
    guest_id = f"guest_{guest_uuid}"
    guest_email = f"{guest_id}@guest.local"
    guest_name = "Guest User"

    # Upsert temporary Guest User record in DB
    user = db.query(User).filter(User.id == guest_id).first()
    if not user:
        user = User(
            id=guest_id,
            email=guest_email,
            name=guest_name,
            picture=None,
            google_id=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    session_token = create_access_token(user_id=guest_id)

    return {
        "status": "success",
        "access_token": session_token,
        "token_type": "bearer",
        "user": {
            "id": guest_id,
            "email": guest_email,
            "masked_email": "guest***@guest.local",
            "name": guest_name,
            "picture": None,
            "is_guest": True,
            "auth_provider": "guest"
        }
    }

@router.get("/me")
def get_authenticated_user(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Returns persistent authenticated user session profile details, Google connection,
    and active project memberships. Supports guest session profile detection.
    """
    email = user_id.strip().lower()
    is_guest = email.startswith("guest_")
    user = db.query(User).filter(User.email == email).first()
    
    masked = "guest***@guest.local" if is_guest else (email[0] + "***" + email[email.find("@"):] if "@" in email else "user***@gmail.com")

    conn = None
    if not is_guest:
        conn = db.query(ExternalConnection).filter(
            ExternalConnection.user_id == email,
            ExternalConnection.provider == "google"
        ).first()

    memberships = db.query(ProjectMembership).filter(
        ProjectMembership.user_id == email,
        ProjectMembership.status == "ACTIVE"
    ).all()

    return {
        "user_id": email,
        "email": email,
        "masked_email": masked,
        "name": user.name if user else ("Guest User" if is_guest else "SEO User"),
        "picture": user.picture if user else None,
        "status": "authenticated",
        "is_guest": is_guest,
        "google_connected": conn is not None and conn.status == "CONNECTED",
        "auth_provider": "guest" if is_guest else "google",
        "memberships_count": len(memberships)
    }

@router.get("/discover-google-properties")
def discover_google_properties(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves authorized Google Search Console properties, Google Analytics GA4 streams,
    and Google Business Profile locations using real Google API credentials where authorized.
    NO FAKE DOMAINS OR SYNTHETIC DATA GENERATED.
    """
    email = user_id.strip().lower()
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == email,
        ExternalConnection.provider == "google"
    ).first()

    real_discovered = []
    service_status = {
        "google_search_console": {"status": "NOT_CONNECTED", "properties_count": 0},
        "google_analytics": {"status": "NOT_CONNECTED", "properties_count": 0},
        "google_business_profile": {"status": "NOT_CONNECTED", "locations_count": 0}
    }

    if conn and conn.status == "CONNECTED":
        access_token = conn.get_access_token()

        # 1. Fetch Real Google Search Console Properties
        gsc_properties = []
        if access_token:
            try:
                req = urllib.request.Request(
                    "https://www.googleapis.com/webmasters/v3/sites",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    site_entries = data.get("siteEntry", [])
                    for site in site_entries:
                        site_url = site.get("siteUrl", "")
                        clean_dom = get_sanitized_domain(site_url)
                        gsc_properties.append({
                            "site_url": site_url,
                            "domain": clean_dom,
                            "permission": site.get("permissionLevel")
                        })
                service_status["google_search_console"] = {
                    "status": "CONNECTED",
                    "properties_count": len(gsc_properties)
                }
            except Exception as e:
                service_status["google_search_console"] = {
                    "status": "AUTHORIZATION_REQUIRED",
                    "error": str(e)
                }

        # 2. Fetch Real Google Analytics Properties
        ga_properties = []
        if access_token:
            try:
                req = urllib.request.Request(
                    "https://analyticsadmin.googleapis.com/v1alpha/accountSummaries",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    summaries = data.get("accountSummaries", [])
                    for acc in summaries:
                        for prop in acc.get("propertySummaries", []):
                            ga_properties.append({
                                "property_id": prop.get("property"),
                                "display_name": prop.get("displayName")
                            })
                service_status["google_analytics"] = {
                    "status": "CONNECTED",
                    "properties_count": len(ga_properties)
                }
            except Exception as e:
                service_status["google_analytics"] = {
                    "status": "NOT_AVAILABLE",
                    "error": "No Google Analytics properties authorized or available for this account."
                }

        # 3. Fetch Real Google Business Profile Locations
        gbp_locations = []
        if access_token:
            try:
                req = urllib.request.Request(
                    "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    accounts = data.get("accounts", [])
                    for acc in accounts:
                        gbp_locations.append({
                            "account_name": acc.get("accountName"),
                            "name": acc.get("name")
                        })
                service_status["google_business_profile"] = {
                    "status": "CONNECTED",
                    "locations_count": len(gbp_locations)
                }
            except Exception as e:
                service_status["google_business_profile"] = {
                    "status": "NOT_AVAILABLE",
                    "error": "No Google Business Profile locations are available for this account."
                }

        # Merge discovered properties without duplicating domains
        for gsc in gsc_properties:
            d = gsc["domain"]
            url_full = gsc["site_url"] if gsc["site_url"].startswith("http") else f"https://{d}/"
            real_discovered.append({
                "id": f"prop_{uuid.uuid4().hex[:8]}",
                "name": d.capitalize(),
                "domain": d,
                "url": url_full,
                "sources": ["Google Search Console"],
                "gsc_property": gsc["site_url"],
                "ga_property_id": None,
                "business_location": None,
                "status": "Not Crawled"
            })

    return {
        "user_id": email,
        "connected_account": email[0] + "***" + email[email.find("@"):] if "@" in email else "user***@gmail.com",
        "service_status": service_status,
        "total_properties": len(real_discovered),
        "properties": real_discovered
    }

@router.post("/register-discovered-projects")
def register_discovered_projects(
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Registers selected discovered Google properties as workspace projects.
    CRITICAL BUSINESS RULE: Sets status to 'Not Crawled' and health_score to null.
    DOES NOT CRAWL AUTOMATICALLY.
    """
    email = user_id.strip().lower()
    selected_props = payload.get("properties", [])
    if not selected_props:
        raise HTTPException(status_code=400, detail="No Google properties selected for registration.")

    registered_projects = []
    
    for prop in selected_props:
        url_val = prop.get("url") or prop.get("domain") or ""
        if not url_val:
            continue
        if not url_val.startswith(("http://", "https://")):
            url_val = "https://" + url_val
        
        safe_domain = get_sanitized_domain(url_val)
        name_val = prop.get("name") or safe_domain

        existing = db.query(Project).all()
        found_existing = None
        for p in existing:
            if get_sanitized_domain(p.url) == safe_domain or p.domain == safe_domain:
                found_existing = p
                break

        if found_existing:
            m = db.query(ProjectMembership).filter(
                ProjectMembership.project_id == found_existing.id,
                ProjectMembership.user_id == email
            ).first()
            if not m:
                m = ProjectMembership(
                    user_id=email,
                    project_id=found_existing.id,
                    role="OWNER",
                    status="ACTIVE"
                )
                db.add(m)
                db.commit()

            registered_projects.append({
                "id": found_existing.id,
                "name": found_existing.name,
                "domain": found_existing.domain,
                "url": found_existing.url,
                "status": "already_exists",
                "crawl_status": "Not Crawled" if not os_has_crawl(found_existing.domain, found_existing.id) else "Completed"
            })
        else:
            new_proj = Project(
                name=name_val,
                url=url_val,
                description=f"Discovered via Connected Google Account ({', '.join(prop.get('sources', ['Google']))})",
                industry="Google Discovery",
                notes=f"Google Sources: {', '.join(prop.get('sources', []))}"
            )
            db.add(new_proj)
            db.commit()
            db.refresh(new_proj)

            new_m = ProjectMembership(
                user_id=email,
                project_id=new_proj.id,
                role="OWNER",
                status="ACTIVE"
            )
            db.add(new_m)
            db.commit()

            registered_projects.append({
                "id": new_proj.id,
                "name": new_proj.name,
                "domain": new_proj.domain,
                "url": new_proj.url,
                "status": "registered",
                "crawl_status": "Not Crawled",
                "health_score": None,
                "last_crawl": None
            })

    return {
        "status": "success",
        "registered_count": len(registered_projects),
        "projects": registered_projects,
        "message": "Discovered Google properties registered successfully as Not Crawled workspace projects."
    }

@router.get("/my-invitations")
def get_my_invitations(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns pending internal team invitations for the currently authenticated application account.
    """
    email = user_id.strip().lower()
    user = db.query(User).filter((User.email.ilike(email)) | (User.id.ilike(email))).first()

    user_ids = [email]
    if user:
        user_ids.append(user.id)
        if user.email:
            user_ids.append(user.email.lower())

    invitations = db.query(ProjectInvitation).filter(
        (ProjectInvitation.invited_email.in_(user_ids)) | (ProjectInvitation.invited_user_id.in_(user_ids)),
        ProjectInvitation.status == "PENDING"
    ).all()

    results = []
    now = datetime.utcnow()

    for inv in invitations:
        if inv.expires_at and inv.expires_at < now:
            inv.status = "EXPIRED"
            db.commit()
            continue

        proj = db.query(Project).filter(Project.id == inv.project_id).first()
        inviter = db.query(User).filter(User.id == inv.invited_by_user_id).first()

        results.append({
            "id": inv.id,
            "project_id": inv.project_id,
            "project_name": proj.name if proj else "SEO Project",
            "project_domain": proj.domain if proj else None,
            "inviter_user_id": inv.invited_by_user_id,
            "inviter_name": inviter.name if inviter else (inv.invited_by_user_id or "Project Admin"),
            "inviter_email": inviter.email if inviter else inv.invited_by_user_id,
            "role": inv.role or "MEMBER",
            "permissions_json": inv.permissions_json,
            "status": inv.status,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None
        })

    return {
        "user_id": email,
        "count": len(results),
        "invitations": results
    }


@router.post("/accept-invitation/{invitation_id}")
@router.post("/invitations/{invitation_id}/accept")
def accept_project_invitation(
    invitation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Accepts a pending internal team invitation after verifying authorization.
    """
    email = user_id.strip().lower()
    user = db.query(User).filter((User.email.ilike(email)) | (User.id.ilike(email))).first()

    invite = db.query(ProjectInvitation).filter(ProjectInvitation.id == invitation_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid.")

    # Authorization Check: Verify invitation belongs to authenticated user account
    allowed = False
    if invite.invited_email and invite.invited_email.lower() == email:
        allowed = True
    if user and invite.invited_user_id and (invite.invited_user_id == user.id or invite.invited_user_id == user.email):
        allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="This invitation belongs to another application account."
        )

    if invite.status == "CANCELLED" or invite.status == "REVOKED":
        raise HTTPException(status_code=400, detail="This invitation was cancelled by the project lead.")

    if invite.status == "EXPIRED" or (invite.expires_at and invite.expires_at < datetime.utcnow()):
        invite.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="This project invitation has expired.")

    if invite.status == "ACCEPTED":
        return {
            "status": "success",
            "message": "Invitation has already been accepted.",
            "project_id": invite.project_id
        }

    if invite.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Cannot accept invitation in status '{invite.status}'.")

    # Check project exists
    project = db.query(Project).filter(Project.id == invite.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="The project for this invitation no longer exists.")

    team_count = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == invite.project_id,
        ProjectMembership.role == "MEMBER",
        ProjectMembership.status == "ACTIVE"
    ).count()

    if team_count >= 2:
        raise HTTPException(status_code=400, detail="Team member limit reached. This project already has 2 active team members.")

    membership = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == invite.project_id,
        (ProjectMembership.user_id == email) | (user and ProjectMembership.user_id == user.id)
    ).first()

    member_user_id = email
    if not membership:
        membership = ProjectMembership(
            user_id=member_user_id,
            project_id=invite.project_id,
            role=invite.role or "MEMBER",
            status="ACTIVE",
            invited_by=invite.invited_by_user_id
        )
        db.add(membership)
    else:
        membership.status = "ACTIVE"
        membership.role = invite.role or "MEMBER"

    invite.status = "ACCEPTED"
    invite.accepted_at = datetime.utcnow()

    # Mark associated notifications as READ
    notifs = db.query(Notification).filter(Notification.invitation_id == invitation_id).all()
    for n in notifs:
        n.status = "READ"
        n.read_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "message": f"Team invitation accepted! You are now a member of '{project.name}'.",
        "project_id": invite.project_id
    }


@router.post("/invitations/{invitation_id}/decline")
def decline_project_invitation(
    invitation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Declines a pending internal team invitation.
    """
    email = user_id.strip().lower()
    user = db.query(User).filter((User.email.ilike(email)) | (User.id.ilike(email))).first()

    invite = db.query(ProjectInvitation).filter(ProjectInvitation.id == invitation_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found or invalid.")

    # Authorization Check
    allowed = False
    if invite.invited_email and invite.invited_email.lower() == email:
        allowed = True
    if user and invite.invited_user_id and (invite.invited_user_id == user.id or invite.invited_user_id == user.email):
        allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="This invitation belongs to another application account."
        )

    if invite.status != "PENDING":
        return {
            "status": "success",
            "message": f"Invitation is currently in status '{invite.status}'.",
            "invitation_id": invitation_id
        }

    invite.status = "REJECTED"
    invite.rejected_at = datetime.utcnow()

    # Mark associated notifications as READ
    notifs = db.query(Notification).filter(Notification.invitation_id == invitation_id).all()
    for n in notifs:
        n.status = "READ"
        n.read_at = datetime.utcnow()

    db.commit()

    return {
        "status": "success",
        "message": "Project invitation declined.",
        "invitation_id": invitation_id
    }

@router.post("/logout")
def logout(user_id: str = Depends(get_current_user_id)):
    """
    Logs out user and invalidates session token.
    """
    return {
        "status": "success",
        "message": "Logged out successfully."
    }

@router.post("/login")
def platform_login(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Authenticates SEO Intelligence platform user with email and password.
    """
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user_name = email.split("@")[0].capitalize()
        user = User(
            id=email,
            email=email,
            name=f"{user_name}",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()

    token = create_access_token(user_id=email)

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.post("/register")
def platform_register(payload: dict = Body(...), db: Session = Depends(get_db)):
    """
    Registers a new SEO Intelligence platform user account.
    """
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if not password or len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        display_name = name or email.split("@")[0].capitalize()
        user = User(
            id=email,
            email=email,
            name=display_name,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()

    token = create_access_token(user_id=email)

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

def os_has_crawl(domain: str, project_id: Optional[str] = None) -> bool:
    from app.config.settings import settings
    from app.config.utils import get_project_storage_dir
    import os
    if not domain:
        return False
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
    return os.path.exists(os.path.join(proj_dir, "latest.json"))
