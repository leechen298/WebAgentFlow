"""Tests for M12.1 recovery boundary classifier."""

from __future__ import annotations

import copy
import inspect

from app.services.recovery import classifier as classifier_module
from app.services.recovery.classifier import RecoveryBoundaryClassifier, classify_recovery_boundary


def classify(evidence: dict[str, object]):
    return classify_recovery_boundary(evidence)


def test_success_returns_no_recovery_needed() -> None:
    result = classify(
        {
            "task_verified": True,
            "postcondition_evidence": [
                {
                    "source": "task_result_reporter",
                    "key": "success_marker",
                    "value": "saved",
                }
            ],
        }
    )

    assert result.classification == "success_no_recovery_needed"
    assert result.recommendation == "no_recovery_needed"
    assert result.reason == "task_succeeded"


def test_replay_failed_returns_failure_stop() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "failed",
            "drift_status": "none",
        }
    )

    assert result.classification == "failure"
    assert result.recommendation == "stop"
    assert result.reason == "replay_failed"


def test_target_missing_drift_suggests_reteach() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "succeeded",
            "drift_status": "target_missing",
            "drift_reasons": ["target_missing"],
        }
    )

    assert result.classification == "failure"
    assert result.recommendation == "suggest_reteach"
    assert result.reason == "target_missing"


def test_missing_context_blocks_and_asks_user() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "blocked_reason": "missing_context",
            "missing_fields": ["target_url"],
        }
    )

    assert result.classification == "blocked"
    assert result.recommendation == "ask_user"
    assert result.reason == "missing_context"


def test_unsupported_action_blocks_and_stops_even_if_retry_candidate() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "blocked_reason": "unsupported_action",
            "retry_candidate": True,
        }
    )

    assert result.classification == "blocked"
    assert result.recommendation == "stop"
    assert result.reason == "unsupported_action"


def test_insufficient_postcondition_evidence_returns_uncertain_needs_review() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "succeeded",
            "drift_status": "none",
            "task_verified": False,
        }
    )

    assert result.classification == "uncertain"
    assert result.recommendation == "needs_review"
    assert result.reason == "insufficient_postcondition_evidence"


def test_explicit_needs_review_marker_returns_needs_review() -> None:
    result = classify({"verification_outcome": "needs_review", "needs_review": True})

    assert result.classification == "needs_review"
    assert result.recommendation == "needs_review"
    assert result.reason == "explicit_needs_review"


def test_blocked_beats_failure() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "verification_outcome": "failed",
            "blocked_reason": "missing_context",
            "replay_status": "failed",
        }
    )

    assert result.classification == "blocked"
    assert result.reason == "missing_context"


def test_failure_beats_uncertain() -> None:
    result = classify(
        {
            "verification_outcome": "failed",
            "replay_status": "succeeded",
            "drift_status": "none",
        }
    )

    assert result.classification == "failure"
    assert result.reason == "result_reporter_failed"


def test_uncertain_beats_needs_review_marker() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "observed",
            "drift_status": "none",
            "needs_review": True,
        }
    )

    assert result.classification == "uncertain"
    assert result.reason == "insufficient_postcondition_evidence"
    assert any(ref.key == "needs_review" for ref in result.evidence)


def test_retry_candidate_returns_boundary_marker_without_execution() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "failed",
            "retry_candidate": True,
        }
    )

    assert result.classification == "failure"
    assert result.recommendation == "retry_possible_requires_confirmation"
    assert result.reason == "replay_failed"
    assert "retry" in result.message.lower()
    for forbidden in ("retry execution", "execute retry", "executes retry", "executing retry"):
        assert forbidden not in result.message.lower()


def test_retry_candidate_never_overrides_permission_block() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "blocked_reason": "permission_or_auth_blocked",
            "retry_candidate": True,
        }
    )

    assert result.classification == "blocked"
    assert result.recommendation == "ask_user"
    assert result.reason == "permission_or_auth_blocked"
    for forbidden in ("retry execution", "execute retry", "executes retry", "executing retry"):
        assert forbidden not in result.message.lower()


def test_classifier_does_not_mutate_input_evidence() -> None:
    evidence = {
        "execution_status": "completed",
        "replay_status": "failed",
        "drift_reasons": ["button_missing"],
        "missing_fields": ["target_url"],
    }
    original = copy.deepcopy(evidence)

    classify(evidence)

    assert evidence == original


def test_evidence_references_preserve_structured_inputs() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "blocked_reason": "missing_context",
            "missing_fields": ["target_url"],
            "learned_path_id": "lp-001",
            "target_url": "http://example.com/users",
            "final_url": "http://example.com/login",
        }
    )

    pairs = {(ref.source, ref.key): ref.value for ref in result.evidence}
    assert pairs[("execution", "execution_status")] == "blocked"
    assert pairs[("execution", "missing_fields")] == ["target_url"]
    assert pairs[("context", "learned_path_id")] == "lp-001"
    assert pairs[("context", "target_url")] == "http://example.com/users"
    assert pairs[("context", "final_url")] == "http://example.com/login"


def test_service_class_matches_function_entrypoint() -> None:
    evidence = {"verification_outcome": "needs_review", "needs_review": True}

    function_result = classify_recovery_boundary(evidence)
    service_result = RecoveryBoundaryClassifier().classify(evidence)

    assert service_result == function_result


def test_retry_candidate_with_replay_drifted_returns_suggest_reteach() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "succeeded",
            "drift_status": "element_mismatch",
            "drift_reasons": ["stale_path"],
            "retry_candidate": True,
        }
    )

    assert result.classification == "failure"
    assert result.recommendation == "suggest_reteach"
    assert result.reason == "stale_or_missing_path_coverage"
    assert "retry" not in result.message.lower()


def test_retry_candidate_with_target_missing_returns_suggest_reteach() -> None:
    result = classify(
        {
            "execution_status": "completed",
            "replay_status": "succeeded",
            "drift_status": "target_missing",
            "drift_reasons": ["target_missing"],
            "retry_candidate": True,
        }
    )

    assert result.classification == "failure"
    assert result.recommendation == "suggest_reteach"
    assert result.reason == "target_missing"
    assert "retry" not in result.message.lower()


def test_unknown_side_effects_blocked_and_stops() -> None:
    result = classify(
        {
            "execution_status": "blocked",
            "blocked_reason": "unknown side effects",
        }
    )

    assert result.classification == "blocked"
    assert result.recommendation == "stop"
    assert result.reason == "unsafe_or_unknown_state"


def test_classifier_module_has_no_forbidden_dependencies() -> None:
    source = inspect.getsource(classifier_module)
    import app.services.recovery as recovery_module

    init_source = inspect.getsource(recovery_module)
    combined = source + init_source
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "sqlalchemy",
        "Session",
        "playwright",
        "requests",
        "httpx",
        "ConversationOrchestrator",
    ]
    for token in forbidden_tokens:
        assert token not in combined
