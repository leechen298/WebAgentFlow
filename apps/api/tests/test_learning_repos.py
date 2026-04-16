"""Tests for the four learning repository classes.

Covers: create, get, get-not-found, update, delete,
        list_page, list_page-empty, pagination,
        and repo-specific methods (list_by_recording, get_by_key).
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

# Import learning models so SQLAlchemy creates their tables in the test DB.
from app.models.candidate_feedback import CandidateFeedback, FeedbackJudgment  # noqa: F401
from app.models.exploration_run import ExplorationMode, ExplorationRun, ExplorationRunStatus  # noqa: F401
from app.models.learned_path import LearnedPath, LearnedPathStatus  # noqa: F401
from app.models.success_criteria import (  # noqa: F401
    SuccessCriteria,
    SuccessCriteriaCategory,
    SuccessCriteriaCreatedBy,
    SuccessCriteriaStrength,
)
from app.repos.candidate_feedback_repo import CandidateFeedbackRepository
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_path_repo import LearnedPathRepository
from app.repos.success_criteria_repo import SuccessCriteriaRepository


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def _make_success_criteria(**overrides: object) -> SuccessCriteria:
    defaults: dict = dict(
        name="Submit OK",
        category=SuccessCriteriaCategory.SUBMIT_SUCCESS,
        strength=SuccessCriteriaStrength.STRONG,
        conditions_json=[],
        created_by=SuccessCriteriaCreatedBy.USER,
        enabled=True,
    )
    defaults.update(overrides)
    return SuccessCriteria(**defaults)


def _make_learned_path(**overrides: object) -> LearnedPath:
    defaults: dict = dict(
        page_signature="/form",
        goal_type="submit",
        steps_json=[],
        variable_slots_json=[],
        observed_effects_json=[],
        constraints_json=[],
        user_labels_json=[],
        recommended=False,
        confidence=0.5,
        status=LearnedPathStatus.CANDIDATE,
    )
    defaults.update(overrides)
    return LearnedPath(**defaults)


def _make_exploration_run(**overrides: object) -> ExplorationRun:
    defaults: dict = dict(
        page_signature="/search",
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.PENDING,
        success_criteria_ids_json=[],
        strategy_json={},
    )
    defaults.update(overrides)
    return ExplorationRun(**defaults)


def _make_candidate_feedback(**overrides: object) -> CandidateFeedback:
    defaults: dict = dict(
        recording_id="rec-001",
        element_key="btn-submit",
        judgment=FeedbackJudgment.REASONABLE,
    )
    defaults.update(overrides)
    return CandidateFeedback(**defaults)


# ═════════════════════════════════════════════════════════
# SuccessCriteriaRepository
# ═════════════════════════════════════════════════════════

class TestSuccessCriteriaRepo:
    def test_create_and_get(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        criteria = _make_success_criteria()
        created = repo.create(criteria)

        assert created.id is not None
        assert created.name == "Submit OK"

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_not_found(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        assert repo.get("nonexistent-id") is None

    def test_update(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        criteria = repo.create(_make_success_criteria())

        criteria.name = "Updated Name"
        criteria.enabled = False
        updated = repo.update(criteria)

        assert updated.name == "Updated Name"
        assert updated.enabled is False

    def test_delete(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        criteria = repo.create(_make_success_criteria())
        cid = criteria.id

        repo.delete(criteria)
        assert repo.get(cid) is None

    def test_list_page_empty(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        items, has_next = repo.list_page()

        assert items == []
        assert has_next is False

    def test_list_page_returns_items(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        repo.create(_make_success_criteria(name="C1"))
        repo.create(_make_success_criteria(name="C2"))
        repo.create(_make_success_criteria(name="C3"))

        items, has_next = repo.list_page(limit=10)
        assert len(items) == 3
        assert has_next is False

    def test_list_page_pagination(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        created = []
        for i in range(5):
            created.append(repo.create(_make_success_criteria(name=f"C{i}")))

        # First page: limit=2
        page1, has_next1 = repo.list_page(limit=2)
        assert len(page1) == 2
        assert has_next1 is True

        # Second page using cursor from last item of page 1
        last = page1[-1]
        page2, has_next2 = repo.list_page(
            limit=2,
            cursor_created_at=last.created_at,
            cursor_id=last.id,
        )
        assert len(page2) == 2
        assert has_next2 is True

        # Third page
        last2 = page2[-1]
        page3, has_next3 = repo.list_page(
            limit=2,
            cursor_created_at=last2.created_at,
            cursor_id=last2.id,
        )
        assert len(page3) == 1
        assert has_next3 is False

    def test_list_page_ordered_desc(self, db_session: Session) -> None:
        repo = SuccessCriteriaRepository(db_session)
        base = datetime.now(UTC)
        c1 = repo.create(_make_success_criteria(name="First", created_at=base))
        c2 = repo.create(
            _make_success_criteria(name="Second", created_at=base + timedelta(seconds=1))
        )

        items, _ = repo.list_page()
        # Most recent first — c2 was created after c1
        assert items[0].id == c2.id
        assert items[1].id == c1.id


# ═════════════════════════════════════════════════════════
# LearnedPathRepository
# ═════════════════════════════════════════════════════════

class TestLearnedPathRepo:
    def test_create_and_get(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        path = _make_learned_path()
        created = repo.create(path)

        assert created.id is not None
        assert created.page_signature == "/form"
        assert created.confidence == 0.5

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_not_found(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        assert repo.get("nonexistent-id") is None

    def test_update(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        path = repo.create(_make_learned_path())

        path.confidence = 0.9
        path.status = LearnedPathStatus.APPROVED
        updated = repo.update(path)

        assert updated.confidence == 0.9
        assert updated.status == LearnedPathStatus.APPROVED

    def test_delete(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        path = repo.create(_make_learned_path())
        pid = path.id

        repo.delete(path)
        assert repo.get(pid) is None

    def test_list_page_empty(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        items, has_next = repo.list_page()
        assert items == []
        assert has_next is False

    def test_list_page_returns_items(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        for i in range(3):
            repo.create(_make_learned_path(page_signature=f"/page{i}"))

        items, has_next = repo.list_page(limit=10)
        assert len(items) == 3
        assert has_next is False

    def test_list_page_pagination(self, db_session: Session) -> None:
        repo = LearnedPathRepository(db_session)
        for i in range(4):
            repo.create(_make_learned_path(page_signature=f"/p{i}"))

        page1, has_next1 = repo.list_page(limit=2)
        assert len(page1) == 2
        assert has_next1 is True

        last = page1[-1]
        page2, has_next2 = repo.list_page(
            limit=2,
            cursor_created_at=last.created_at,
            cursor_id=last.id,
        )
        assert len(page2) == 2
        assert has_next2 is False


# ═════════════════════════════════════════════════════════
# ExplorationRunRepository
# ═════════════════════════════════════════════════════════

class TestExplorationRunRepo:
    def test_create_and_get(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        run = _make_exploration_run()
        created = repo.create(run)

        assert created.id is not None
        assert created.mode == ExplorationMode.FORM
        assert created.status == ExplorationRunStatus.PENDING

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_not_found(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        assert repo.get("nonexistent-id") is None

    def test_update(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        run = repo.create(_make_exploration_run())

        run.status = ExplorationRunStatus.COMPLETED
        run.summary = "All steps passed"
        updated = repo.update(run)

        assert updated.status == ExplorationRunStatus.COMPLETED
        assert updated.summary == "All steps passed"

    def test_delete(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        run = repo.create(_make_exploration_run())
        rid = run.id

        repo.delete(run)
        assert repo.get(rid) is None

    def test_list_page_empty(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        items, has_next = repo.list_page()
        assert items == []
        assert has_next is False

    def test_list_page_returns_items(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        for i in range(3):
            repo.create(_make_exploration_run(page_signature=f"/s{i}"))

        items, has_next = repo.list_page(limit=10)
        assert len(items) == 3
        assert has_next is False

    def test_list_page_pagination(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        for i in range(5):
            repo.create(_make_exploration_run(page_signature=f"/s{i}"))

        page1, has_next1 = repo.list_page(limit=2)
        assert len(page1) == 2
        assert has_next1 is True

        last = page1[-1]
        page2, _ = repo.list_page(
            limit=2,
            cursor_created_at=last.created_at,
            cursor_id=last.id,
        )
        assert len(page2) == 2

    def test_update_json_fields(self, db_session: Session) -> None:
        repo = ExplorationRunRepository(db_session)
        run = repo.create(_make_exploration_run())

        run.candidate_elements_json = [{"tag": "button", "score": 0.8}]
        run.interaction_hints_json = [{"action": "click", "target": "submit"}]
        updated = repo.update(run)

        fetched = repo.get(updated.id)
        assert fetched is not None
        assert len(fetched.candidate_elements_json) == 1
        assert fetched.candidate_elements_json[0]["tag"] == "button"
        assert len(fetched.interaction_hints_json) == 1


# ═════════════════════════════════════════════════════════
# CandidateFeedbackRepository
# ═════════════════════════════════════════════════════════

class TestCandidateFeedbackRepo:
    def test_create_and_get(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        fb = _make_candidate_feedback()
        created = repo.create(fb)

        assert created.id is not None
        assert created.recording_id == "rec-001"
        assert created.judgment == FeedbackJudgment.REASONABLE

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_not_found(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        assert repo.get("nonexistent-id") is None

    def test_update(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        fb = repo.create(_make_candidate_feedback())

        fb.judgment = FeedbackJudgment.UNREASONABLE
        fb.comment = "Not a real button"
        updated = repo.update(fb)

        assert updated.judgment == FeedbackJudgment.UNREASONABLE
        assert updated.comment == "Not a real button"

    def test_delete(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        fb = repo.create(_make_candidate_feedback())
        fid = fb.id

        repo.delete(fb)
        assert repo.get(fid) is None

    def test_list_page_empty(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        items, has_next = repo.list_page()
        assert items == []
        assert has_next is False

    def test_list_page_returns_items(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        for i in range(3):
            repo.create(_make_candidate_feedback(element_key=f"btn-{i}"))

        items, has_next = repo.list_page(limit=10)
        assert len(items) == 3
        assert has_next is False

    def test_list_page_pagination(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        for i in range(4):
            repo.create(_make_candidate_feedback(element_key=f"el-{i}"))

        page1, has_next1 = repo.list_page(limit=2)
        assert len(page1) == 2
        assert has_next1 is True

        last = page1[-1]
        page2, has_next2 = repo.list_page(
            limit=2,
            cursor_created_at=last.created_at,
            cursor_id=last.id,
        )
        assert len(page2) == 2
        assert has_next2 is False

    # ── list_by_recording ──

    def test_list_by_recording(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        repo.create(_make_candidate_feedback(recording_id="rec-A", element_key="e1"))
        repo.create(_make_candidate_feedback(recording_id="rec-A", element_key="e2"))
        repo.create(_make_candidate_feedback(recording_id="rec-B", element_key="e3"))

        results = repo.list_by_recording("rec-A")
        assert len(results) == 2
        assert all(r.recording_id == "rec-A" for r in results)

    def test_list_by_recording_with_run_id(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        repo.create(_make_candidate_feedback(
            recording_id="rec-A", element_key="e1", run_id="run-1",
        ))
        repo.create(_make_candidate_feedback(
            recording_id="rec-A", element_key="e2", run_id="run-2",
        ))

        results = repo.list_by_recording("rec-A", run_id="run-1")
        assert len(results) == 1
        assert results[0].run_id == "run-1"

    def test_list_by_recording_empty(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        results = repo.list_by_recording("no-such-rec")
        assert results == []

    # ── get_by_key ──

    def test_get_by_key_no_run_id(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        repo.create(_make_candidate_feedback(
            recording_id="rec-1", element_key="btn-ok", run_id=None,
        ))

        found = repo.get_by_key("rec-1", "btn-ok", run_id=None)
        assert found is not None
        assert found.element_key == "btn-ok"

    def test_get_by_key_with_run_id(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        repo.create(_make_candidate_feedback(
            recording_id="rec-1", element_key="btn-ok", run_id="run-X",
        ))

        found = repo.get_by_key("rec-1", "btn-ok", run_id="run-X")
        assert found is not None
        assert found.run_id == "run-X"

    def test_get_by_key_not_found(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        assert repo.get_by_key("rec-1", "nonexistent") is None

    def test_get_by_key_distinguishes_run_id(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        repo.create(_make_candidate_feedback(
            recording_id="rec-1", element_key="btn-ok", run_id=None,
        ))
        repo.create(_make_candidate_feedback(
            recording_id="rec-1", element_key="btn-ok", run_id="run-1",
        ))

        # Looking for run_id=None should find only the null-run entry
        found_null = repo.get_by_key("rec-1", "btn-ok", run_id=None)
        assert found_null is not None
        assert found_null.run_id is None

        # Looking for run_id="run-1" should find the other
        found_run = repo.get_by_key("rec-1", "btn-ok", run_id="run-1")
        assert found_run is not None
        assert found_run.run_id == "run-1"

    def test_create_with_json_fields(self, db_session: Session) -> None:
        repo = CandidateFeedbackRepository(db_session)
        fb = _make_candidate_feedback(
            candidate_score=0.85,
            inferred_actions_json=["click", "hover"],
            evidence_json={"tag": "button", "visible": True},
        )
        created = repo.create(fb)

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.candidate_score == 0.85
        assert fetched.inferred_actions_json == ["click", "hover"]
        assert fetched.evidence_json == {"tag": "button", "visible": True}
