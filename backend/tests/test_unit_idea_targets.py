import unittest
from datetime import datetime
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Idea, Unit, User, UnitIdeaTarget
from app.models.idea import IdeaStatus
from app.routers import dashboard, settings
from app.seed import migrate_unit_idea_targets_table


class UnitIdeaTargetTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([Unit(id=1, name="A"), Unit(id=2, name="B"), User(employee_code="ADMIN", full_name="Admin", role="admin"), User(employee_code="EMP", full_name="Employee", role="employee")])
        self.db.commit()
        app = FastAPI()
        app.include_router(settings.router)
        app.include_router(dashboard.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def save(self, **kwargs):
        return self.client.put("/settings/admin/unit-idea-targets", json={"employee_code": "ADMIN", "year": 2026, "unit_id": 1, "target_count": 12, **kwargs})

    def test_update_preserves_other_units_and_years_and_zero(self):
        for values in ({}, {"unit_id": 2}, {"year": 2025}, {"target_count": 0}):
            self.assertEqual(self.save(**values).status_code, 200)
        self.assertEqual(self.db.query(UnitIdeaTarget).count(), 3)
        response = self.client.get("/settings/admin/unit-idea-targets", params={"employee_code": "ADMIN", "year": 2026})
        self.assertEqual({x["unit_id"]: x["target_count"] for x in response.json()["items"]}, {1: 0, 2: 12})
        with patch("app.seed.engine", self.engine):
            migrate_unit_idea_targets_table()
            migrate_unit_idea_targets_table()
        self.assertEqual(self.db.query(UnitIdeaTarget).count(), 3)

    def test_permissions_and_validation(self):
        self.assertEqual(self.save(employee_code="EMP").status_code, 403)
        self.assertEqual(self.client.get("/settings/admin/unit-idea-targets?employee_code=EMP&year=2026").status_code, 403)
        for invalid in (-1, 1.5, True, 2147483648):
            self.assertEqual(self.save(target_count=invalid).status_code, 422)
        self.assertEqual(self.save(year=1999).status_code, 422)
        self.assertEqual(self.save(unit_id=999).status_code, 404)
        self.assertEqual(self.db.query(UnitIdeaTarget).count(), 0)

    def test_ie_manager_can_read_and_update_targets(self):
        self.db.add(User(employee_code="IE", full_name="IE Manager", role="ie_manager"))
        self.db.commit()
        self.assertEqual(self.save(employee_code="IE").status_code, 200)
        response = self.client.get("/settings/admin/unit-idea-targets?employee_code=IE&year=2026")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [{"year": 2026, "unit_id": 1, "target_count": 12}])
        self.assertEqual(self.save(employee_code="IE", target_count=20).status_code, 200)
        self.assertEqual(self.db.get(UnitIdeaTarget, (2026, 1)).target_count, 20)
        self.assertEqual(self.db.get(UnitIdeaTarget, (2026, 1)).updated_by, "IE")

    def test_target_year_available_without_ideas(self):
        self.save(year=2027)
        self.assertEqual(self.client.get("/dashboard/idea-years").json(), [2027])

    def test_chart_counts_and_annual_targets_with_month_filter(self):
        self.save()
        for year, month, status in [(2026, 1, IdeaStatus.APPROVED), (2026, 2, IdeaStatus.REWARDED), (2025, 1, IdeaStatus.APPROVED), (2026, 1, IdeaStatus.DRAFT)]:
            self.db.add(Idea(unit_id=1, full_name="User", title="Idea", category="PROCESS", description="Test", status=status, submitted_at=datetime(year, month, 15)))
        self.db.commit()
        annual = self.client.get("/dashboard/ideas-by-unit?year=2026").json()
        self.assertEqual(annual[0]["idea_count"], 2)
        self.assertEqual(annual[0]["target_count"], 12)
        self.assertEqual(annual[1]["idea_count"], 0)
        self.assertIsNone(annual[1]["target_count"])
        monthly = self.client.get("/dashboard/ideas-by-unit?year=2026&month=1").json()
        self.assertEqual(monthly[0]["idea_count"], 1)
        self.assertEqual(monthly[0]["target_count"], 12)
        for params in ("?year=2025", ""):
            self.assertIsNone(self.client.get("/dashboard/ideas-by-unit" + params).json()[0]["target_count"])


if __name__ == "__main__":
    unittest.main()
