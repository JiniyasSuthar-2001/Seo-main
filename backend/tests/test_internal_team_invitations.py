import pytest
import unittest
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.database import Base
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.project_invitation import ProjectInvitation
from app.routers.projects import search_users, invite_teammate, cancel_invitation
from app.routers.auth import get_my_invitations, accept_project_invitation, decline_project_invitation
from fastapi import HTTPException

class TestInternalTeamInvitations(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

        # Create test users
        self.user_a = User(id="usera@example.com", email="usera@example.com", name="User A")
        self.user_b = User(id="userb@example.com", email="userb@example.com", name="User B")
        self.user_c = User(id="userc@example.com", email="userc@example.com", name="User C")
        self.user_d = User(id="userd@example.com", email="userd@example.com", name="User D")

        self.db.add_all([self.user_a, self.user_b, self.user_c, self.user_d])
        self.db.commit()

        # Create test projects
        self.project_a = Project(id="proj_a", name="Project Alpha", url="https://alpha.com")
        self.project_b = Project(id="proj_b", name="Project Beta", url="https://beta.com")
        self.db.add_all([self.project_a, self.project_b])
        self.db.commit()

        # Owner memberships
        self.mem_a = ProjectMembership(user_id=self.user_a.id, project_id=self.project_a.id, role="OWNER", status="ACTIVE")
        self.mem_a_b = ProjectMembership(user_id=self.user_a.id, project_id=self.project_b.id, role="OWNER", status="ACTIVE")
        self.db.add_all([self.mem_a, self.mem_a_b])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_account_search(self):
        """User account search returns matching registered accounts."""
        res = search_users(q="userb", user_id=self.user_a.id, db=self.db)
        users = res.get("users", [])
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["email"], "userb@example.com")

    def test_02_send_internal_invitation_success(self):
        """User A invites registered User B -> Internal invitation created (no email)."""
        res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com", "role": "MEMBER"},
            user_id=self.user_a.id,
            db=self.db
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("Team invitation sent", res["message"])

        inv = self.db.query(ProjectInvitation).filter_by(project_id=self.project_a.id, invited_email="userb@example.com").first()
        self.assertIsNotNone(inv)
        self.assertEqual(inv.status, "PENDING")

    def test_03_account_not_found(self):
        """Inviting unregistered email raises 404 Account Not Found error."""
        with self.assertRaises(HTTPException) as ctx:
            invite_teammate(
                project_id=self.project_a.id,
                payload={"email": "nonexistent@example.com"},
                user_id=self.user_a.id,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Account not found", ctx.exception.detail)

    def test_04_self_invitation_prevention(self):
        """Prevent self invitation."""
        with self.assertRaises(HTTPException) as ctx:
            invite_teammate(
                project_id=self.project_a.id,
                payload={"email": "usera@example.com"},
                user_id=self.user_a.id,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot invite yourself", ctx.exception.detail)

    def test_05_already_member_prevention(self):
        """Prevent inviting active member."""
        # Add User B to project A
        mem_b = ProjectMembership(user_id=self.user_b.id, project_id=self.project_a.id, role="MEMBER", status="ACTIVE")
        self.db.add(mem_b)
        self.db.commit()

        with self.assertRaises(HTTPException) as ctx:
            invite_teammate(
                project_id=self.project_a.id,
                payload={"email": "userb@example.com"},
                user_id=self.user_a.id,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already a member", ctx.exception.detail)

    def test_06_duplicate_invitation_prevention(self):
        """Prevent duplicate pending invitation."""
        invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        with self.assertRaises(HTTPException) as ctx:
            invite_teammate(
                project_id=self.project_a.id,
                payload={"email": "userb@example.com"},
                user_id=self.user_a.id,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invitation already pending", ctx.exception.detail)

    def test_07_recipient_view_my_invitations(self):
        """Recipient User B views pending invitations."""
        invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        res = get_my_invitations(user_id=self.user_b.id, db=self.db)
        invs = res.get("invitations", [])
        self.assertEqual(len(invs), 1)
        self.assertEqual(invs[0]["project_name"], "Project Alpha")

    def test_08_accept_invitation_flow(self):
        """Recipient User B accepts invitation -> Membership created."""
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com", "role": "MEMBER"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        accept_res = accept_project_invitation(invitation_id=inv_id, user_id=self.user_b.id, db=self.db)
        self.assertEqual(accept_res["status"], "success")

        # Verify membership
        mem = self.db.query(ProjectMembership).filter_by(project_id=self.project_a.id, user_id=self.user_b.id).first()
        self.assertIsNotNone(mem)
        self.assertEqual(mem.status, "ACTIVE")

    def test_09_decline_invitation_flow(self):
        """Recipient User C declines invitation -> Status REJECTED, no membership."""
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userc@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        dec_res = decline_project_invitation(invitation_id=inv_id, user_id=self.user_c.id, db=self.db)
        self.assertEqual(dec_res["status"], "success")

        mem = self.db.query(ProjectMembership).filter_by(project_id=self.project_a.id, user_id=self.user_c.id).first()
        self.assertIsNone(mem)

        inv = self.db.query(ProjectInvitation).filter_by(id=inv_id).first()
        self.assertEqual(inv.status, "REJECTED")

    def test_10_cross_account_accept_security(self):
        """User C trying to accept User B's invitation raises 403 Forbidden."""
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        with self.assertRaises(HTTPException) as ctx:
            accept_project_invitation(invitation_id=inv_id, user_id=self.user_c.id, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_11_cancel_invitation_by_owner(self):
        """Owner cancels invitation -> Status CANCELLED, accept attempt fails."""
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        cancel_invitation(project_id=self.project_a.id, payload={"invitation_id": inv_id}, user_id=self.user_a.id, db=self.db)

        with self.assertRaises(HTTPException) as ctx:
            accept_project_invitation(invitation_id=inv_id, user_id=self.user_b.id, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cancelled", ctx.exception.detail)

    def test_12_project_scope_isolation(self):
        """Accepting Project A does NOT grant access to Project B."""
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        accept_project_invitation(invitation_id=inv_res["invitation"]["id"], user_id=self.user_b.id, db=self.db)

        # Check membership in project B
        mem_b = self.db.query(ProjectMembership).filter_by(project_id=self.project_b.id, user_id=self.user_b.id).first()
        self.assertIsNone(mem_b)

    def test_13_persistent_notification_creation(self):
        """Team invitation atomically creates a persistent Notification for invited recipient."""
        from app.models.notification import Notification
        from app.routers.notifications import get_notifications, mark_notification_read

        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com", "role": "MEMBER"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        # Recipient User B fetches notifications
        res = get_notifications(user_id=self.user_b.id, db=self.db)
        self.assertEqual(res["unread_count"], 1)
        self.assertEqual(len(res["notifications"]), 1)

        n = res["notifications"][0]
        self.assertEqual(n["title"], "Project Team Invitation")
        self.assertIn("Project Alpha", n["message"])
        self.assertEqual(n["invitation_id"], inv_id)
        self.assertEqual(n["status"], "UNREAD")

        # Mark notification as read
        read_res = mark_notification_read(notification_id=n["id"], user_id=self.user_b.id, db=self.db)
        self.assertEqual(read_res["status"], "success")

        # Verify unread count decreases
        res_after = get_notifications(user_id=self.user_b.id, db=self.db)
        self.assertEqual(res_after["unread_count"], 0)

    def test_14_notification_security(self):
        """User C cannot mark User B's notification as read."""
        from app.routers.notifications import mark_notification_read
        inv_res = invite_teammate(
            project_id=self.project_a.id,
            payload={"email": "userb@example.com"},
            user_id=self.user_a.id,
            db=self.db
        )
        inv_id = inv_res["invitation"]["id"]

        from app.models.notification import Notification
        notif = self.db.query(Notification).filter_by(invitation_id=inv_id).first()
        self.assertIsNotNone(notif)

        with self.assertRaises(HTTPException) as ctx:
            mark_notification_read(notification_id=notif.id, user_id=self.user_c.id, db=self.db)
        self.assertEqual(ctx.exception.status_code, 403)

if __name__ == "__main__":
    unittest.main()
