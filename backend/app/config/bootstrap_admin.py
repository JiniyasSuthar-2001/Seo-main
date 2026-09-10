"""
Explicit Administrative Bootstrap Module.
Enables server administrators to safely assign SUPER_ADMIN platform role to an initial account.
Must be run explicitly via CLI command or explicit administrative initialization.
NEVER runs automatically during routine HTTP API requests.

Usage:
    python -m app.config.bootstrap_admin admin@yourdomain.com
"""
import sys
from app.config.database import SessionLocal
from app.models.user import User

def bootstrap_super_admin(email_or_id: str) -> bool:
    if not email_or_id or not email_or_id.strip():
        print("[BOOTSTRAP ADMIN] Error: Email or User ID is required.")
        return False

    clean_target = email_or_id.strip().lower()
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == clean_target) | (User.id == clean_target) | (User.id == email_or_id)
        ).first()

        if not user:
            user = User(
                id=clean_target,
                email=clean_target if "@" in clean_target else f"{clean_target}@admin.local",
                name="Platform Super Admin",
                platform_role="SUPER_ADMIN",
                status="ACTIVE"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[BOOTSTRAP ADMIN] Created new account '{user.email}' with platform_role='SUPER_ADMIN'.")
            return True
        else:
            old_role = user.platform_role
            user.platform_role = "SUPER_ADMIN"
            user.status = "ACTIVE"
            db.commit()
            print(f"[BOOTSTRAP ADMIN] Promoted existing account '{user.email}' from '{old_role}' to 'SUPER_ADMIN'.")
            return True
    except Exception as e:
        db.rollback()
        print(f"[BOOTSTRAP ADMIN] Failed to assign administrator role: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.config.bootstrap_admin <admin_email_or_user_id>")
        sys.exit(1)
    target = sys.argv[1]
    success = bootstrap_super_admin(target)
    sys.exit(0 if success else 1)
