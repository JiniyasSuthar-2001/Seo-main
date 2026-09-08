import unittest
import os
import sys
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token


class TestWorkspaceTeamFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # 1. Owner User
        cls.owner_email = f"owner_{uuid.uuid4().hex[:6]}@example.com"
        cls.owner_user = User(id=cls.owner_email, email=cls.owner_email, name="Owner Lead")
        cls.db.add(cls.owner_user)

        # 2. Member User
        cls.member_email = f"member_{uuid.uuid4().hex[:6]}@example.com"
        cls.member_user = User(id=cls.member_email, email=cls.member_email, name="Team Member")
        cls.db.add(cls.member_user)

        # 3. Third-party User
        cls.other_email = f"other_{uuid.uuid4().hex[:6]}@example.com"
        cls.other_user = User(id=cls.other_email, email=cls.other_email, name="External User")
        cls.db.add(cls.other_user)

        # Projects
        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="Alpha Corp",
            domain="alpha.com",
            url="https://alpha.com",
            description="Project Alpha"
        )
        cls.proj_b = Project(
            id=str(uuid.uuid4()),
            name="Beta Inc",
            domain="beta.com",
            url="https://beta.com",
            description="Project Beta"
        )
        cls.db.add_all([cls.proj_a, cls.proj_b])

        # Memberships for Proj A
        cls.mem_owner_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.owner_email,
            project_id=cls.proj_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.mem_member_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.member_email,
            project_id=cls.proj_a.id,
            role="MEMBER",
            status="ACTIVE"
        )
        # Membership for Proj B (Owner only)
        cls.mem_owner_b = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.owner_email,
            project_id=cls.proj_b.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add_all([cls.mem_owner_a, cls.mem_member_a, cls.mem_owner_b])
        cls.db.commit()

        cls.owner_token = create_access_token(user_id=cls.owner_email)
        cls.owner_headers = {"Authorization": f"Bearer {cls.owner_token}"}

        cls.member_token = create_access_token(user_id=cls.member_email)
        cls.member_headers = {"Authorization": f"Bearer {cls.member_token}"}

        cls.other_token = create_access_token(user_id=cls.other_email)
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id.in_([cls.proj_a.id, cls.proj_b.id])).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id.in_([cls.proj_a.id, cls.proj_b.id])).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id.in_([cls.owner_email, cls.member_email, cls.other_email])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_owner_can_view_team(self):
        """Owner can view active team members for their project."""
        res = self.client.get(f"/api/projects/{self.proj_a.id}/team", headers=self.owner_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_owner"])
        self.assertEqual(len(data["members"]), 2)

    def test_02_member_can_view_team(self):
        """Team member can view team for authorized project, caller_role is MEMBER."""
        res = self.client.get(f"/api/projects/{self.proj_a.id}/team", headers=self.member_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_owner"])
        self.assertEqual(data["caller_role"], "MEMBER")

    def test_03_unauthorized_user_cannot_view_team(self):
        """External user cannot view team of unauthorized project."""
        res = self.client.get(f"/api/projects/{self.proj_a.id}/team", headers=self.other_headers)
        self.assertEqual(res.status_code, 403)

    def test_04_member_cannot_remove_other_member(self):
        """Team Member cannot remove another member (requires Owner permission)."""
        res = self.client.post(
            f"/api/projects/{self.proj_a.id}/team/remove",
            json={"email": self.owner_email},
            headers=self.member_headers
        )
        self.assertEqual(res.status_code, 403)

    def test_05_owner_cannot_remove_self(self):
        """Owner cannot remove themselves from project team."""
        res = self.client.post(
            f"/api/projects/{self.proj_a.id}/team/remove",
            json={"email": self.owner_email},
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 400)

    def test_06_owner_cannot_leave_own_project(self):
        """Owner cannot leave their own project."""
        res = self.client.post(
            f"/api/projects/{self.proj_a.id}/team/leave",
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 400)

    def test_07_member_can_leave_project(self):
        """Member can successfully leave project membership."""
        res = self.client.post(
            f"/api/projects/{self.proj_a.id}/team/leave",
            headers=self.member_headers
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("success", res.json()["status"])

        # Verify member no longer has access
        res_after = self.client.get(f"/api/projects/{self.proj_a.id}/team", headers=self.member_headers)
        self.assertEqual(res_after.status_code, 403)

        # Verify project and owner are intact
        res_owner = self.client.get(f"/api/projects/{self.proj_a.id}/team", headers=self.owner_headers)
        self.assertEqual(res_owner.status_code, 200)
        self.assertEqual(len(res_owner.json()["members"]), 1)

    def test_08_owner_can_remove_teammate(self):
        """Owner can remove an active teammate."""
        # Add a new teammate to proj_b
        temp_email = f"temp_{uuid.uuid4().hex[:6]}@example.com"
        temp_user = User(id=temp_email, email=temp_email, name="Temp Teammate")
        self.db.add(temp_user)
        temp_mem = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=temp_email,
            project_id=self.proj_b.id,
            role="MEMBER",
            status="ACTIVE"
        )
        self.db.add(temp_mem)
        self.db.commit()

        # Remove teammate
        res = self.client.post(
            f"/api/projects/{self.proj_b.id}/team/remove",
            json={"email": temp_email},
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 200)

        # Verify revoked
        m = self.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == self.proj_b.id,
            ProjectMembership.user_id == temp_email
        ).first()
        self.assertEqual(m.status, "REVOKED")


if __name__ == '__main__':
    unittest.main()
