import unittest
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Idea, IdeaScore, RewardBatch, ScoreCriteria, ScoreCriteriaSet, Unit, User
from app.models.idea import IdeaStatus
from app.models.idea_target_group import IdeaTargetGroup, IdeaTargetGroupMember
from app.models.review import IdeaReview, ReviewAction, ReviewLevel
from app.models.score import K1Type, K3MeasureType
from app.routers import quarterly_reports, reward_batches, reviews


class QuarterlyReportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            Unit(id=1, name="XN1"), Unit(id=2, name="XN2"),
            User(id=1, employee_code="IE", full_name="IE", role="ie_manager"),
            User(id=2, employee_code="EMP", full_name="Employee", role="employee"),
            User(id=3, employee_code="DIGITAL", full_name="Digital", role="digital_manager"),
            User(id=4, employee_code="BOD", full_name="Leadership", role="bod_manager"),
            User(id=5, employee_code="DEPT", full_name="Department", role="dept_manager"),
            User(id=6, employee_code="ADMIN", full_name="Administrator", role="admin"),
            IdeaTargetGroup(id=1, year=2026, name="XN1", target_count=24),
            IdeaTargetGroupMember(year=2026, unit_id=1, group_id=1),
            Idea(id=1, unit_id=1, full_name="A", title="Idea A", category="PROCESS", description="A", status=IdeaStatus.APPROVED, submitted_at=datetime(2026, 3, 31, 18, 30, tzinfo=UTC), approved_at=datetime(2026, 4, 8, tzinfo=UTC), council_final_score=32),
            Idea(id=2, unit_id=2, full_name="B", title="Idea B", category="PROCESS", description="B", status=IdeaStatus.LEADERSHIP_REVIEW, submitted_at=datetime(2026, 4, 12, tzinfo=UTC)),
        ])
        self.db.commit()
        criteria_set = ScoreCriteriaSet(id=1, name="Bộ tiêu chí 2026", effective_from=date(2026, 1, 1))
        self.db.add(criteria_set)
        self.db.add_all([
            ScoreCriteria(criteria_set_id=1, criterion_key="K2", code="B1", label="B1", score=3, sort_order=1),
            ScoreCriteria(criteria_set_id=1, criterion_key="K2", code="B2", label="B2", score=3, sort_order=2),
            IdeaScore(
                idea_id=1, scorer_id=1, k1_type=K1Type.IMPROVEMENT, k1_score=5,
                k2_type="EASY", k2_score=6, k2_selected_codes='["B1", "B2"]',
                k3_measure_type=K3MeasureType.TIME_SAVED, k3_option_code="C3", k3_score=20,
                total_score=31, is_final=True, scored_at=datetime(2026, 4, 8, tzinfo=UTC),
            ),
            IdeaScore(
                idea_id=1, scorer_id=5, k1_type=K1Type.OLD, k1_score=2,
                k2_type="EASY", k2_score=0, k2_selected_codes="[]",
                k3_measure_type=K3MeasureType.UNMEASURABLE, k3_score=0,
                total_score=2, is_final=False, scored_at=datetime(2026, 3, 31, 17, tzinfo=UTC),
            ),
            IdeaScore(
                idea_id=2, scorer_id=5, k1_type=K1Type.OLD, k1_score=2,
                k2_type="EASY", k2_score=0, k2_selected_codes="[]",
                k3_measure_type=K3MeasureType.UNMEASURABLE, k3_score=0,
                total_score=2, is_final=False, scored_at=datetime(2026, 4, 11, tzinfo=UTC),
            ),
            IdeaReview(idea_id=1, reviewer_id=1, level=ReviewLevel.COUNCIL, action=ReviewAction.APPROVE, council_result_type="APPROVED_STANDARDIZATION"),
            IdeaReview(idea_id=2, reviewer_id=1, level=ReviewLevel.COUNCIL, action=ReviewAction.APPROVE, council_result_type="UNIT_REVIEW"),
        ])
        self.db.commit()
        app = FastAPI()
        app.include_router(quarterly_reports.router)
        app.include_router(reward_batches.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def report(self, quarter):
        return self.client.get("/quarterly-reports/", params={"employee_code": "IE", "year": 2026, "quarter": quarter})

    def test_local_date_default_and_move_updates_both_reports(self):
        initial = self.report(2).json()
        self.assertEqual({item["idea_id"] for item in initial["items"]}, {1, 2})
        self.assertEqual(initial["summary"][0]["annual_target"], 24)
        self.assertEqual(sum(row["company_score"] for row in initial["summary"]), 32)
        self.assertEqual(len(self.client.get("/reward-batches/candidates", params={"year": 2026, "quarter": 2}).json()["items"]), 1)
        self.assertEqual(self.client.put("/quarterly-reports/ideas/1/period", json={"employee_code": "IE", "year": 2026, "quarter": 3}).status_code, 422)
        moved = self.client.put("/quarterly-reports/ideas/1/period", json={"employee_code": "IE", "year": 2026, "quarter": 3, "note": "Chuyển kỳ xét"})
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual({item["idea_id"] for item in self.report(2).json()["items"]}, {2})
        q3 = self.report(3).json()
        self.assertEqual(q3["items"][0]["period_note"], "Chuyển kỳ xét")
        self.assertEqual(q3["summary"][0]["annual_target"], 24)
        self.assertEqual(len(self.client.get("/reward-batches/candidates", params={"year": 2026, "quarter": 3}).json()["items"]), 1)

    def test_permission_and_default_verification(self):
        self.assertEqual(self.client.get("/quarterly-reports/", params={"employee_code": "EMP", "year": 2026, "quarter": 2}).status_code, 403)
        self.assertEqual(self.client.put("/quarterly-reports/ideas/1/period", json={"employee_code": "EMP", "year": 2026, "quarter": 2}).status_code, 403)
        verified = self.client.put("/quarterly-reports/ideas/1/period", json={"employee_code": "IE", "year": 2026, "quarter": 2})
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertIsNone(self.report(2).json()["items"][0]["period_verified_at"])
        self.assertIsNone(self.db.get(Idea, 1).report_quarter)
        queue_item = reviews._idea_to_item(self.db.get(Idea, 1), False)
        self.assertEqual((queue_item.report_year, queue_item.report_quarter), (2026, 2))
        digital = self.client.put("/quarterly-reports/ideas/2/period", json={"employee_code": "DIGITAL", "year": 2026, "quarter": 2})
        self.assertEqual(digital.status_code, 200, digital.text)

    def test_report_role_matrix(self):
        for employee_code in ("ADMIN", "IE", "DIGITAL", "BOD"):
            with self.subTest(employee_code=employee_code):
                response = self.client.get("/quarterly-reports/", params={"employee_code": employee_code, "year": 2026, "quarter": 2})
                self.assertEqual(response.status_code, 200, response.text)
        response = self.client.get("/quarterly-reports/", params={"employee_code": "DEPT", "year": 2026, "quarter": 2})
        self.assertEqual(response.status_code, 403, response.text)

    def test_only_council_roles_can_change_report_period(self):
        for employee_code in ("ADMIN", "IE", "DIGITAL", "BOD"):
            with self.subTest(employee_code=employee_code):
                response = self.client.put(
                    "/quarterly-reports/ideas/2/period",
                    json={"employee_code": employee_code, "year": 2026, "quarter": 2},
                )
                self.assertEqual(response.status_code, 200, response.text)
        response = self.client.put(
            "/quarterly-reports/ideas/2/period",
            json={"employee_code": "DEPT", "year": 2026, "quarter": 2},
        )
        self.assertEqual(response.status_code, 403, response.text)

    def test_detail_expands_k1_k2_k3_subcriteria(self):
        item = next(item for item in self.report(2).json()["items"] if item["idea_id"] == 1)
        self.assertEqual(item["criteria_scores"], {"A2": 5, "B1": 3, "B2": 3, "C3": 20})
        self.assertEqual(item["ie_score"], 31)

    def test_not_considered_remains_in_detail_and_batch_locks_period(self):
        self.db.add(Idea(id=3, unit_id=1, full_name="C", title="Idea C", category="PROCESS", description="C", status=IdeaStatus.REJECTED, submitted_at=datetime(2026, 4, 12, tzinfo=UTC)))
        self.db.commit()
        report = self.report(2).json()
        self.assertEqual(len(report["items"]), 3)
        self.assertEqual(next(item for item in report["items"] if item["idea_id"] == 3)["classification"], "not_considered")
        self.assertEqual(sum(row["idea_count"] for row in report["summary"]), 2)
        self.db.add(RewardBatch(year=2026, quarter=2, coefficient=1000, created_by="IE"))
        self.db.commit()
        response = self.client.put("/quarterly-reports/ideas/1/period", json={"employee_code": "IE", "year": 2026, "quarter": 3, "note": "Chuyển kỳ xét"})
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
