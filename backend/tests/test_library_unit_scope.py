import unittest
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Idea, Unit, User
from app.models.idea import IdeaStatus
from app.routers import library


class UnitLibraryScopeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all(
            [
                Unit(id=1, name="Phòng Tổng hợp"),
                Unit(id=2, name="Đơn vị khác"),
                User(employee_code="ADMIN", full_name="Admin", role='["admin"]', unit_id=1),
                User(employee_code="MANAGER", full_name="Manager", role='["dept_manager"]', unit_id=1),
            ]
        )
        self.db.flush()
        self.db.add_all(
            [
                Idea(id=1, unit_id=1, full_name="Người gửi 1", title="Ý tưởng phòng tổng hợp", category="PROCESS", description="Mô tả 1", status=IdeaStatus.SUBMITTED, submitted_at=datetime(2026, 1, 1)),
                Idea(id=2, unit_id=2, full_name="Người gửi 2", title="Ý tưởng đơn vị khác", category="PROCESS", description="Mô tả 2", status=IdeaStatus.SUBMITTED, submitted_at=datetime(2026, 1, 2)),
                Idea(id=3, unit_id=2, full_name="Người gửi 3", title="Ý tưởng nháp", category="PROCESS", description="Mô tả 3", status=IdeaStatus.DRAFT, submitted_at=datetime(2026, 1, 3)),
            ]
        )
        self.db.commit()

        app = FastAPI()
        app.include_router(library.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_admin_sees_all_units_and_can_filter_one_unit(self):
        response = self.client.get("/library/ideas", params={"employee_code": "ADMIN", "library_type": "unit"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({row["id"] for row in response.json()}, {1, 2})

        filtered = self.client.get("/library/ideas", params={"employee_code": "ADMIN", "library_type": "unit", "unit_id": 2})
        self.assertEqual(filtered.status_code, 200, filtered.text)
        self.assertEqual([row["id"] for row in filtered.json()], [2])

    def test_admin_can_open_other_unit_detail(self):
        response = self.client.get("/library/ideas/2", params={"employee_code": "ADMIN", "library_type": "unit"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["unit_id"], 2)

    def test_manager_remains_limited_to_own_unit(self):
        response = self.client.get("/library/ideas", params={"employee_code": "MANAGER", "library_type": "unit"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([row["id"] for row in response.json()], [1])

        detail = self.client.get("/library/ideas/2", params={"employee_code": "MANAGER", "library_type": "unit"})
        self.assertEqual(detail.status_code, 403)


if __name__ == "__main__":
    unittest.main()
