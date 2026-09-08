import unittest
import os
import shutil
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.llm.context_builder import LLMContextBuilder

class TestSecurityAndStorage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import uuid
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"sec_usera_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"sec_userb_{uuid.uuid4().hex[:6]}@example.com"

        # Create User A
        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="User A")
        cls.db.add(cls.user_a)
        
        # Create User B
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="User B")
        cls.db.add(cls.user_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(cls.user_b.id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        # Project A owned by User A
        cls.project_a = Project(name="Project A", domain="sec-test.com", url="https://sec-test.com")
        cls.db.add(cls.project_a)
        cls.db.commit()

        cls.membership_a = ProjectMembership(user_id=cls.user_a.id, project_id=cls.project_a.id, role="OWNER", status="ACTIVE")
        cls.db.add(cls.membership_a)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.project_a.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.project_a.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id.in_([cls.user_a.id, cls.user_b.id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

    def test_01_datasources_authorization(self):
        # User A can access Project A datasources
        res_a = self.client.get(f"/api/projects/{self.project_a.id}/datasources", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)

        # User B CANNOT access Project A datasources (Forbidden 403)
        res_b = self.client.get(f"/api/projects/{self.project_a.id}/datasources", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 403)

    def test_02_imports_authorization(self):
        # User B CANNOT import data into Project A (Forbidden 403)
        payload = {
            "filename": "test.csv",
            "source": "Manual Test",
            "data_type": "keywords",
            "records": [{"keyword": "test", "search_volume": 100}]
        }
        res_b = self.client.post(f"/api/projects/{self.project_a.id}/imports/", json=payload, headers=self.headers_b)
        self.assertEqual(res_b.status_code, 403)

        # User A CAN import data into Project A
        res_a = self.client.post(f"/api/projects/{self.project_a.id}/imports/", json=payload, headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)

    def test_03_context_builder_project_id_scoping(self):
        builder = LLMContextBuilder(base_dir="data/test_websites")
        folder = builder.get_website_folder(self.project_a.id, self.project_a.domain)
        self.assertTrue(self.project_a.id in folder or "sec-test" in folder)

if __name__ == '__main__':
    unittest.main()
