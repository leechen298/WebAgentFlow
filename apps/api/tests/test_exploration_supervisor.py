"""
Tests for the exploration supervisor (post-run LLM assessment).

Covers:
1. _fallback_assessment with successful result -> verdict=success
2. _fallback_assessment with failed steps -> verdict=failure
3. _fallback_assessment with warning steps -> verdict=partial_success
4. _fallback_assessment with no steps -> uncertain
5. _build_step_summary extracts correct fields from step log
6. _build_prompt produces valid JSON with correct structure
7. SupervisorAssessment.to_dict() round-trips correctly
8. summarize_exploration with mocked LLM -> uses LLM result
9. summarize_exploration with LLM failure -> falls back to rule-based
10. SUPERVISOR_RESPONSE_SCHEMA has correct keys
"""

import json
from unittest.mock import patch

import pytest

from app.schemas.execution import ExecutionResult, PageStateChange
from app.schemas.exploration_run import ExplorationResult, ExplorationStepLog
from app.schemas.llm import LlmError, LlmResponse, LlmUsage
from app.schemas.observation import PostActionObservation
from app.schemas.success_criteria import SuccessEvaluation
from app.schemas.task_definition import TaskDefinition
from app.services.learning.exploration_supervisor import (
    SUPERVISOR_RESPONSE_SCHEMA,
    SupervisorAssessment,
    _build_prompt,
    _build_step_summary,
    _fallback_assessment,
    summarize_exploration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    *,
    task_id: str = "test-task-1",
    name: str = "Test Task",
    description: str = "A test task for unit tests.",
    target_url: str = "https://example.com",
    variables: dict | None = None,
    num_steps: int = 2,
) -> TaskDefinition:
    return TaskDefinition(
        id=task_id,
        name=name,
        description=description,
        target_url=target_url,
        variables=variables or {},
        steps=[
            {"intent": f"step_{i}", "action_type": "click"}
            for i in range(num_steps)
        ],
    )


def _make_step(
    *,
    step_index: int = 0,
    intent: str = "click_submit",
    action_type: str = "click",
    target_summary: str = "Submit button",
    value: str | None = None,
    execution_ok: bool = True,
    execution_error: str | None = None,
    page_change: PageStateChange | None = None,
    observation: PostActionObservation | None = None,
    success_evaluation: SuccessEvaluation | None = None,
) -> ExplorationStepLog:
    exec_result = ExecutionResult(
        ok=execution_ok,
        action_type=action_type,
        target_summary=target_summary,
        error=execution_error,
        page_change=page_change or PageStateChange(),
    )
    return ExplorationStepLog(
        step_index=step_index,
        intent=intent,
        action_type=action_type,
        target_summary=target_summary,
        value=value,
        execution_result=exec_result,
        observation=observation,
        success_evaluation=success_evaluation,
    )


def _make_result(
    *,
    success: bool = True,
    steps: list[ExplorationStepLog] | None = None,
    final_url: str = "https://example.com/done",
    final_title: str = "Done",
    elapsed_ms: int = 3000,
) -> ExplorationResult:
    step_list = steps if steps is not None else []
    return ExplorationResult(
        success=success,
        steps=step_list,
        total_steps=len(step_list),
        final_url=final_url,
        final_title=final_title,
        elapsed_ms=elapsed_ms,
    )


def _make_llm_response(
    *,
    ok: bool = True,
    parsed: dict | None = None,
    error: LlmError | None = None,
) -> LlmResponse:
    return LlmResponse(
        ok=ok,
        parsed=parsed,
        usage=LlmUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
        model="test-model",
        error=error,
    )


# ---------------------------------------------------------------------------
# 1. _fallback_assessment — successful result
# ---------------------------------------------------------------------------

class TestFallbackAssessmentSuccess:
    def test_success_verdict_when_result_success_and_no_failures(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0, intent="fill_search"),
            _make_step(step_index=1, intent="click_submit"),
        ]
        result = _make_result(success=True, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "success"
        assert assessment.confidence == "medium"
        assert assessment.should_save_path is True
        assert "successfully" in assessment.summary

    def test_success_step_assessments_all_ok(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0),
            _make_step(step_index=1),
        ]
        result = _make_result(success=True, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert len(assessment.step_assessments) == 2
        for sa in assessment.step_assessments:
            assert sa["status"] == "ok"
            assert sa["note"] == "Completed without error"

    def test_success_includes_task_name_in_summary(self):
        task = _make_task(name="Login Flow")
        steps = [_make_step(step_index=0)]
        result = _make_result(success=True, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert "Login Flow" in assessment.summary

    def test_success_suggestions_contain_llm_unavailable_notice(self):
        task = _make_task()
        result = _make_result(success=True, steps=[_make_step()])

        assessment = _fallback_assessment(task, result)

        assert len(assessment.suggestions) == 1
        assert "LLM unavailable" in assessment.suggestions[0]

    def test_success_anomalies_empty(self):
        task = _make_task()
        result = _make_result(success=True, steps=[_make_step()])

        assessment = _fallback_assessment(task, result)

        assert assessment.anomalies == []


# ---------------------------------------------------------------------------
# 2. _fallback_assessment — failed steps
# ---------------------------------------------------------------------------

class TestFallbackAssessmentFailure:
    def test_failure_verdict_when_step_has_error(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0, execution_ok=False, execution_error="Element not found"),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "failure"
        assert assessment.confidence == "high"
        assert assessment.should_save_path is False

    def test_failure_counts_failed_steps_in_summary(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0, execution_ok=False, execution_error="Timeout"),
            _make_step(step_index=1, execution_ok=False, execution_error="Not found"),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert "2 step(s) had errors" in assessment.summary

    def test_failure_step_assessment_contains_error_message(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0, execution_ok=False, execution_error="Element not found"),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.step_assessments[0]["status"] == "failed"
        assert "Element not found" in assessment.step_assessments[0]["note"]

    def test_failure_overrides_result_success_flag(self):
        """Even if result.success=True, failed steps yield verdict=failure."""
        task = _make_task()
        steps = [
            _make_step(step_index=0, execution_ok=False, execution_error="oops"),
        ]
        # result.success=True but a step has an error
        result = _make_result(success=True, steps=steps)

        assessment = _fallback_assessment(task, result)

        # Failed steps take precedence over result.success
        assert assessment.verdict == "failure"

    def test_failure_mixed_ok_and_failed_steps(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0),  # ok
            _make_step(step_index=1, execution_ok=False, execution_error="Timeout"),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "failure"
        assert assessment.step_assessments[0]["status"] == "ok"
        assert assessment.step_assessments[1]["status"] == "failed"


# ---------------------------------------------------------------------------
# 3. _fallback_assessment — warning steps
# ---------------------------------------------------------------------------

class TestFallbackAssessmentWarning:
    def test_partial_success_when_evaluation_unsatisfied(self):
        task = _make_task()
        eval_fail = SuccessEvaluation(
            satisfied=False,
            confidence="high",
            failed_conditions=["url_changed"],
        )
        steps = [
            _make_step(step_index=0, success_evaluation=eval_fail),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "partial_success"
        assert assessment.confidence == "low"

    def test_partial_success_step_assessment_is_warning(self):
        task = _make_task()
        eval_fail = SuccessEvaluation(
            satisfied=False,
            confidence="high",
            failed_conditions=["title_contains"],
        )
        steps = [
            _make_step(step_index=0, success_evaluation=eval_fail),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.step_assessments[0]["status"] == "warning"
        assert "title_contains" in assessment.step_assessments[0]["note"]

    def test_partial_success_summary_includes_warning_count(self):
        task = _make_task()
        eval_fail = SuccessEvaluation(
            satisfied=False,
            failed_conditions=["url_changed"],
        )
        steps = [
            _make_step(step_index=0),
            _make_step(step_index=1, success_evaluation=eval_fail),
            _make_step(step_index=2, success_evaluation=eval_fail),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "partial_success"
        assert "2 step(s) had evaluation warnings" in assessment.summary

    def test_error_takes_precedence_over_warning(self):
        """When a step has both an execution error and a failed evaluation,
        the step should be classified as 'failed' not 'warning'."""
        task = _make_task()
        eval_fail = SuccessEvaluation(
            satisfied=False,
            failed_conditions=["url_changed"],
        )
        steps = [
            _make_step(
                step_index=0,
                execution_ok=False,
                execution_error="Timeout",
                success_evaluation=eval_fail,
            ),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = _fallback_assessment(task, result)

        # Error takes precedence; it checks error first in the if-elif chain
        assert assessment.step_assessments[0]["status"] == "failed"
        assert assessment.verdict == "failure"


# ---------------------------------------------------------------------------
# 4. _fallback_assessment — no steps
# ---------------------------------------------------------------------------

class TestFallbackAssessmentNoSteps:
    def test_uncertain_verdict_with_empty_steps(self):
        task = _make_task()
        result = _make_result(success=False, steps=[])

        assessment = _fallback_assessment(task, result)

        assert assessment.verdict == "uncertain"
        assert assessment.confidence == "low"
        assert assessment.should_save_path is False

    def test_uncertain_summary_mentions_unclear(self):
        task = _make_task()
        result = _make_result(success=False, steps=[])

        assessment = _fallback_assessment(task, result)

        assert "unclear" in assessment.summary

    def test_uncertain_step_assessments_empty(self):
        task = _make_task()
        result = _make_result(success=False, steps=[])

        assessment = _fallback_assessment(task, result)

        assert assessment.step_assessments == []

    def test_success_true_but_no_steps_is_still_success(self):
        """If result.success=True and no steps, the fallback still says success."""
        task = _make_task()
        result = _make_result(success=True, steps=[])

        assessment = _fallback_assessment(task, result)

        # success=True with no failed steps -> success verdict
        assert assessment.verdict == "success"


# ---------------------------------------------------------------------------
# 5. _build_step_summary
# ---------------------------------------------------------------------------

class TestBuildStepSummary:
    def test_basic_fields_extracted(self):
        step = _make_step(
            step_index=3,
            intent="fill_email",
            action_type="fill",
            target_summary="email input",
            value="test@example.com",
        )

        summary = _build_step_summary(step)

        assert summary["step_index"] == 3
        assert summary["intent"] == "fill_email"
        assert summary["action_type"] == "fill"
        assert summary["target_summary"] == "email input"
        assert summary["value"] == "test@example.com"

    def test_value_omitted_when_none(self):
        step = _make_step(value=None)

        summary = _build_step_summary(step)

        assert "value" not in summary

    def test_execution_result_fields(self):
        page_change = PageStateChange(
            url_before="https://example.com/form",
            url_after="https://example.com/success",
        )
        step = _make_step(
            execution_ok=True,
            execution_error=None,
            page_change=page_change,
        )

        summary = _build_step_summary(step)

        assert summary["execution_ok"] is True
        assert summary["error"] is None
        assert summary["url_before"] == "https://example.com/form"
        assert summary["url_after"] == "https://example.com/success"

    def test_observation_fields(self):
        obs = PostActionObservation(
            url="https://example.com/result",
            title="Result Page",
            url_changed=True,
            title_changed=True,
            html_changed=True,
        )
        step = _make_step(observation=obs)

        summary = _build_step_summary(step)

        assert summary["url_changed"] is True
        assert summary["title_changed"] is True
        assert summary["html_changed"] is True
        assert summary["final_url"] == "https://example.com/result"
        assert summary["final_title"] == "Result Page"

    def test_success_evaluation_fields(self):
        eval_result = SuccessEvaluation(
            satisfied=True,
            confidence="high",
            matched_conditions=["url_changed", "title_contains"],
            failed_conditions=[],
        )
        step = _make_step(success_evaluation=eval_result)

        summary = _build_step_summary(step)

        assert summary["eval_satisfied"] is True
        assert summary["eval_confidence"] == "high"
        assert summary["eval_matched"] == ["url_changed", "title_contains"]
        assert summary["eval_failed"] == []
        assert "eval_uncertain_reason" not in summary

    def test_success_evaluation_with_uncertain_reason(self):
        eval_result = SuccessEvaluation(
            satisfied=False,
            confidence="low",
            matched_conditions=[],
            failed_conditions=["url_changed"],
            uncertain_reason="Page might still be loading",
        )
        step = _make_step(success_evaluation=eval_result)

        summary = _build_step_summary(step)

        assert summary["eval_uncertain_reason"] == "Page might still be loading"

    def test_no_optional_sections_when_absent(self):
        """Step with no execution_result, observation, or success_evaluation."""
        step = ExplorationStepLog(
            step_index=0,
            intent="test",
            action_type="click",
            target_summary="button",
        )

        summary = _build_step_summary(step)

        assert "execution_ok" not in summary
        assert "url_changed" not in summary
        assert "eval_satisfied" not in summary

    def test_execution_result_without_page_change(self):
        """page_change is None -> no url_before/url_after in summary."""
        step = ExplorationStepLog(
            step_index=0,
            intent="test",
            action_type="click",
            target_summary="button",
            execution_result=ExecutionResult(ok=True, error=None),
        )

        summary = _build_step_summary(step)

        assert summary["execution_ok"] is True
        # page_change defaults to PageStateChange() which has empty strings,
        # so url_before/url_after are present but empty
        assert summary["url_before"] == ""
        assert summary["url_after"] == ""


# ---------------------------------------------------------------------------
# 6. _build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_produces_valid_json(self):
        task = _make_task()
        steps = [_make_step(step_index=0)]
        result = _make_result(success=True, steps=steps, elapsed_ms=5000)

        prompt = _build_prompt(task, result)
        parsed = json.loads(prompt)

        assert isinstance(parsed, dict)

    def test_task_section_structure(self):
        task = _make_task(
            task_id="t-123",
            name="Search Task",
            description="Search something",
            target_url="https://example.com",
            variables={"query": "test"},
            num_steps=3,
        )
        result = _make_result(success=True, steps=[])

        prompt = _build_prompt(task, result)
        parsed = json.loads(prompt)

        assert parsed["task"]["id"] == "t-123"
        assert parsed["task"]["name"] == "Search Task"
        assert parsed["task"]["description"] == "Search something"
        assert parsed["task"]["target_url"] == "https://example.com"
        assert parsed["task"]["variables"] == {"query": "test"}
        assert parsed["task"]["total_steps_defined"] == 3

    def test_result_section_structure(self):
        task = _make_task()
        result = _make_result(
            success=True,
            steps=[],
            final_url="https://example.com/done",
            final_title="Finished",
            elapsed_ms=4500,
        )

        prompt = _build_prompt(task, result)
        parsed = json.loads(prompt)

        assert parsed["result"]["success"] is True
        assert parsed["result"]["total_steps_executed"] == 0
        assert parsed["result"]["final_url"] == "https://example.com/done"
        assert parsed["result"]["final_title"] == "Finished"
        assert parsed["result"]["elapsed_ms"] == 4500

    def test_steps_section_uses_build_step_summary(self):
        task = _make_task()
        steps = [
            _make_step(step_index=0, intent="click_login"),
            _make_step(step_index=1, intent="fill_password", value="secret"),
        ]
        result = _make_result(success=True, steps=steps)

        prompt = _build_prompt(task, result)
        parsed = json.loads(prompt)

        assert len(parsed["steps"]) == 2
        assert parsed["steps"][0]["step_index"] == 0
        assert parsed["steps"][0]["intent"] == "click_login"
        assert parsed["steps"][1]["step_index"] == 1
        assert parsed["steps"][1]["value"] == "secret"

    def test_prompt_handles_unicode(self):
        task = _make_task(name="中文任务", description="测试描述")
        result = _make_result(success=True, steps=[])

        prompt = _build_prompt(task, result)
        parsed = json.loads(prompt)

        assert parsed["task"]["name"] == "中文任务"
        assert parsed["task"]["description"] == "测试描述"


# ---------------------------------------------------------------------------
# 7. SupervisorAssessment.to_dict() round-trip
# ---------------------------------------------------------------------------

class TestSupervisorAssessment:
    def test_to_dict_returns_raw_data(self):
        data = {
            "verdict": "success",
            "confidence": "high",
            "summary": "All good.",
            "step_assessments": [
                {"step_index": 0, "status": "ok", "note": "Fine"},
            ],
            "anomalies": ["minor oddity"],
            "suggestions": ["consider caching"],
            "should_save_path": True,
        }

        assessment = SupervisorAssessment(data)
        roundtrip = assessment.to_dict()

        assert roundtrip == data

    def test_fields_populated_from_data(self):
        data = {
            "verdict": "partial_success",
            "confidence": "medium",
            "summary": "Partially done.",
            "step_assessments": [],
            "anomalies": ["a1", "a2"],
            "suggestions": ["s1"],
            "should_save_path": False,
        }

        assessment = SupervisorAssessment(data)

        assert assessment.verdict == "partial_success"
        assert assessment.confidence == "medium"
        assert assessment.summary == "Partially done."
        assert assessment.step_assessments == []
        assert assessment.anomalies == ["a1", "a2"]
        assert assessment.suggestions == ["s1"]
        assert assessment.should_save_path is False

    def test_defaults_when_data_is_empty(self):
        assessment = SupervisorAssessment({})

        assert assessment.verdict == "uncertain"
        assert assessment.confidence == "low"
        assert assessment.summary == ""
        assert assessment.step_assessments == []
        assert assessment.anomalies == []
        assert assessment.suggestions == []
        assert assessment.should_save_path is False

    def test_defaults_when_data_is_partial(self):
        data = {"verdict": "failure", "summary": "oops"}

        assessment = SupervisorAssessment(data)

        assert assessment.verdict == "failure"
        assert assessment.summary == "oops"
        assert assessment.confidence == "low"  # default
        assert assessment.should_save_path is False  # default

    def test_to_dict_preserves_extra_keys(self):
        """Raw data may contain extra keys from the LLM; they are preserved."""
        data = {
            "verdict": "success",
            "confidence": "high",
            "summary": "ok",
            "step_assessments": [],
            "anomalies": [],
            "suggestions": [],
            "should_save_path": True,
            "extra_field": "some_value",
        }

        assessment = SupervisorAssessment(data)
        roundtrip = assessment.to_dict()

        assert roundtrip["extra_field"] == "some_value"


# ---------------------------------------------------------------------------
# 8. summarize_exploration — mocked LLM success
# ---------------------------------------------------------------------------

class TestSummarizeExplorationLlmSuccess:
    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_uses_llm_parsed_result(self, mock_generate):
        llm_data = {
            "verdict": "success",
            "confidence": "high",
            "summary": "LLM says it went great.",
            "step_assessments": [
                {"step_index": 0, "status": "ok", "note": "good"},
            ],
            "anomalies": [],
            "suggestions": ["optimize step 1"],
            "should_save_path": True,
        }
        mock_generate.return_value = _make_llm_response(ok=True, parsed=llm_data)

        task = _make_task()
        result = _make_result(success=True, steps=[_make_step()])

        assessment = summarize_exploration(task, result)

        assert assessment.verdict == "success"
        assert assessment.confidence == "high"
        assert assessment.summary == "LLM says it went great."
        assert assessment.should_save_path is True
        assert assessment.suggestions == ["optimize step 1"]

    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_llm_called_with_correct_request(self, mock_generate):
        mock_generate.return_value = _make_llm_response(
            ok=True,
            parsed={
                "verdict": "success",
                "confidence": "high",
                "summary": "ok",
                "step_assessments": [],
                "anomalies": [],
                "suggestions": [],
                "should_save_path": True,
            },
        )

        task = _make_task(task_id="task-abc")
        result = _make_result(success=True, steps=[])

        summarize_exploration(task, result)

        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[0][0]  # LlmRequest
        assert call_args.response_schema == SUPERVISOR_RESPONSE_SCHEMA
        assert call_args.temperature == 0.3
        assert call_args.metadata["source"] == "exploration_supervisor"
        assert call_args.metadata["task_id"] == "task-abc"
        assert len(call_args.messages) == 1
        assert call_args.messages[0].role == "user"
        # The user message should be valid JSON
        json.loads(call_args.messages[0].content)

    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_llm_partial_success_verdict(self, mock_generate):
        llm_data = {
            "verdict": "partial_success",
            "confidence": "medium",
            "summary": "Some steps worked.",
            "step_assessments": [
                {"step_index": 0, "status": "ok", "note": "good"},
                {"step_index": 1, "status": "warning", "note": "iffy"},
            ],
            "anomalies": ["unexpected redirect"],
            "suggestions": [],
            "should_save_path": False,
        }
        mock_generate.return_value = _make_llm_response(ok=True, parsed=llm_data)

        task = _make_task()
        result = _make_result(success=False, steps=[_make_step(), _make_step(step_index=1)])

        assessment = summarize_exploration(task, result)

        assert assessment.verdict == "partial_success"
        assert assessment.anomalies == ["unexpected redirect"]
        assert assessment.to_dict() == llm_data


# ---------------------------------------------------------------------------
# 9. summarize_exploration — LLM failure -> fallback
# ---------------------------------------------------------------------------

class TestSummarizeExplorationLlmFailure:
    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_falls_back_when_llm_ok_false(self, mock_generate):
        error = LlmError(kind="provider_error", message="API down", retryable=True)
        mock_generate.return_value = _make_llm_response(ok=False, parsed=None, error=error)

        task = _make_task(name="Fallback Task")
        steps = [_make_step(step_index=0)]
        result = _make_result(success=True, steps=steps)

        assessment = summarize_exploration(task, result)

        # Should be rule-based fallback
        assert assessment.verdict == "success"
        assert "Fallback Task" in assessment.summary
        assert "LLM unavailable" in assessment.suggestions[0]

    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_falls_back_when_parsed_is_none(self, mock_generate):
        """LLM returns ok=True but parsed is None -> fallback."""
        mock_generate.return_value = _make_llm_response(ok=True, parsed=None)

        task = _make_task()
        steps = [
            _make_step(step_index=0, execution_ok=False, execution_error="Timeout"),
        ]
        result = _make_result(success=False, steps=steps)

        assessment = summarize_exploration(task, result)

        # Should fall back to rule-based -> failure
        assert assessment.verdict == "failure"

    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_falls_back_when_both_ok_false_and_parsed_none(self, mock_generate):
        error = LlmError(kind="timeout", message="Request timed out")
        mock_generate.return_value = _make_llm_response(ok=False, parsed=None, error=error)

        task = _make_task()
        result = _make_result(success=False, steps=[])

        assessment = summarize_exploration(task, result)

        assert assessment.verdict == "uncertain"

    @patch("app.services.learning.exploration_supervisor.generate_structured")
    def test_fallback_with_error_none(self, mock_generate):
        """LLM returns ok=False but error is None -> still falls back gracefully."""
        mock_generate.return_value = _make_llm_response(ok=False, parsed=None, error=None)

        task = _make_task()
        steps = [_make_step()]
        result = _make_result(success=True, steps=steps)

        assessment = summarize_exploration(task, result)

        assert assessment.verdict == "success"


# ---------------------------------------------------------------------------
# 10. SUPERVISOR_RESPONSE_SCHEMA correctness
# ---------------------------------------------------------------------------

class TestSupervisorResponseSchema:
    def test_schema_type_is_object(self):
        assert SUPERVISOR_RESPONSE_SCHEMA["type"] == "object"

    def test_schema_has_all_required_keys(self):
        required = SUPERVISOR_RESPONSE_SCHEMA["required"]
        expected_required = {
            "verdict", "confidence", "summary",
            "step_assessments", "anomalies", "suggestions", "should_save_path",
        }
        assert set(required) == expected_required

    def test_schema_properties_match_required(self):
        props = set(SUPERVISOR_RESPONSE_SCHEMA["properties"].keys())
        required = set(SUPERVISOR_RESPONSE_SCHEMA["required"])
        assert required.issubset(props)

    def test_verdict_enum_values(self):
        verdict_prop = SUPERVISOR_RESPONSE_SCHEMA["properties"]["verdict"]
        assert set(verdict_prop["enum"]) == {
            "success", "partial_success", "failure", "uncertain",
        }

    def test_confidence_enum_values(self):
        confidence_prop = SUPERVISOR_RESPONSE_SCHEMA["properties"]["confidence"]
        assert set(confidence_prop["enum"]) == {"high", "medium", "low"}

    def test_step_assessments_is_array(self):
        sa = SUPERVISOR_RESPONSE_SCHEMA["properties"]["step_assessments"]
        assert sa["type"] == "array"

    def test_step_assessment_item_required_fields(self):
        sa_items = SUPERVISOR_RESPONSE_SCHEMA["properties"]["step_assessments"]["items"]
        assert set(sa_items["required"]) == {"step_index", "status", "note"}

    def test_step_assessment_status_enum(self):
        sa_items = SUPERVISOR_RESPONSE_SCHEMA["properties"]["step_assessments"]["items"]
        status_prop = sa_items["properties"]["status"]
        assert set(status_prop["enum"]) == {"ok", "warning", "failed", "skipped"}

    def test_should_save_path_is_boolean(self):
        prop = SUPERVISOR_RESPONSE_SCHEMA["properties"]["should_save_path"]
        assert prop["type"] == "boolean"

    def test_anomalies_is_string_array(self):
        prop = SUPERVISOR_RESPONSE_SCHEMA["properties"]["anomalies"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"

    def test_suggestions_is_string_array(self):
        prop = SUPERVISOR_RESPONSE_SCHEMA["properties"]["suggestions"]
        assert prop["type"] == "array"
        assert prop["items"]["type"] == "string"
