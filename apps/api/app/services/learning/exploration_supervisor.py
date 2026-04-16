"""Exploration supervisor — post-run LLM summary and assessment.

After an exploration run completes, the supervisor:
  1. Builds a structured prompt from the step logs
  2. Calls the LLM for a human-readable summary
  3. Returns a SupervisorAssessment with verdict, findings, and suggestions

This is Layer 2 supervision (post-hoc). Layer 1 (real-time per-step
supervision) is not yet implemented.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas.exploration_run import ExplorationResult, ExplorationStepLog
from app.schemas.llm import LlmMessage, LlmRequest
from app.schemas.task_definition import TaskDefinition
from app.services.llm_provider import generate_structured

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Output schema
# ───────────────────────────────────────────────────────────────────

SUPERVISOR_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["success", "partial_success", "failure", "uncertain"],
            "description": "Overall assessment of the exploration run.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "summary": {
            "type": "string",
            "description": "2-4 sentence human-readable summary of what happened.",
        },
        "step_assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_index": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "enum": ["ok", "warning", "failed", "skipped"],
                    },
                    "note": {"type": "string"},
                },
                "required": ["step_index", "status", "note"],
            },
            "description": "Per-step assessment.",
        },
        "anomalies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anything unexpected or concerning.",
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Actionable suggestions for improving the task definition or criteria.",
        },
        "should_save_path": {
            "type": "boolean",
            "description": "Whether this run produced a path worth saving.",
        },
    },
    "required": [
        "verdict", "confidence", "summary", "step_assessments",
        "anomalies", "suggestions", "should_save_path",
    ],
}


class SupervisorAssessment:
    """Structured output from the supervisor."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.verdict: str = data.get("verdict", "uncertain")
        self.confidence: str = data.get("confidence", "low")
        self.summary: str = data.get("summary", "")
        self.step_assessments: list[dict[str, Any]] = data.get("step_assessments", [])
        self.anomalies: list[str] = data.get("anomalies", [])
        self.suggestions: list[str] = data.get("suggestions", [])
        self.should_save_path: bool = data.get("should_save_path", False)
        self._raw = data

    def to_dict(self) -> dict[str, Any]:
        return self._raw


# ───────────────────────────────────────────────────────────────────
# Prompt construction
# ───────────────────────────────────────────────────────────────────

def _build_step_summary(step: ExplorationStepLog) -> dict[str, Any]:
    """Extract the key info from a step log for the prompt."""
    summary: dict[str, Any] = {
        "step_index": step.step_index,
        "intent": step.intent,
        "action_type": step.action_type,
        "target_summary": step.target_summary,
    }

    if step.value:
        summary["value"] = step.value

    if step.execution_result:
        summary["execution_ok"] = step.execution_result.ok
        summary["error"] = step.execution_result.error
        if step.execution_result.page_change:
            pc = step.execution_result.page_change
            summary["url_before"] = pc.url_before
            summary["url_after"] = pc.url_after

    if step.observation:
        summary["url_changed"] = step.observation.url_changed
        summary["title_changed"] = step.observation.title_changed
        summary["html_changed"] = step.observation.html_changed
        summary["final_url"] = step.observation.url
        summary["final_title"] = step.observation.title

    if step.success_evaluation:
        summary["eval_satisfied"] = step.success_evaluation.satisfied
        summary["eval_confidence"] = step.success_evaluation.confidence
        summary["eval_matched"] = step.success_evaluation.matched_conditions
        summary["eval_failed"] = step.success_evaluation.failed_conditions
        if step.success_evaluation.uncertain_reason:
            summary["eval_uncertain_reason"] = step.success_evaluation.uncertain_reason

    return summary


def _build_prompt(
    task: TaskDefinition,
    result: ExplorationResult,
) -> str:
    """Build the user message for the supervisor LLM call."""
    step_summaries = [_build_step_summary(s) for s in result.steps]

    prompt_data = {
        "task": {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "target_url": task.target_url,
            "variables": task.variables,
            "total_steps_defined": len(task.steps),
        },
        "result": {
            "success": result.success,
            "total_steps_executed": result.total_steps,
            "final_url": result.final_url,
            "final_title": result.final_title,
            "elapsed_ms": result.elapsed_ms,
        },
        "steps": step_summaries,
    }

    return json.dumps(prompt_data, ensure_ascii=False, indent=2)


SYSTEM_PROMPT = """\
You are a supervisor agent reviewing the results of an automated web exploration run.

Your job:
1. Assess whether the exploration achieved its goal
2. Identify any anomalies or unexpected behavior
3. Provide actionable suggestions for improving the task definition
4. Decide if the discovered path is worth saving

Be concise and specific. Focus on facts from the step logs, not speculation.
When assessing each step, note what actually happened vs what was intended.
If the URL or title didn't change as expected, flag it clearly.

Respond in the same language as the task name and description.\
"""


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

def summarize_exploration(
    task: TaskDefinition,
    result: ExplorationResult,
) -> SupervisorAssessment:
    """Generate a post-run supervisor assessment using LLM.

    Returns a SupervisorAssessment. If the LLM call fails, returns
    a fallback assessment based on rule-based signals.
    """
    prompt = _build_prompt(task, result)

    request = LlmRequest(
        system=SYSTEM_PROMPT,
        messages=[LlmMessage(role="user", content=prompt)],
        response_schema=SUPERVISOR_RESPONSE_SCHEMA,
        temperature=0.3,
        metadata={"source": "exploration_supervisor", "task_id": task.id},
    )

    response = generate_structured(request)

    if response.ok and response.parsed:
        logger.info("Supervisor assessment: verdict=%s", response.parsed.get("verdict"))
        return SupervisorAssessment(response.parsed)

    # Fallback: rule-based assessment
    logger.warning(
        "LLM supervisor call failed, using fallback: %s",
        response.error.message if response.error else "unknown",
    )
    return _fallback_assessment(task, result)


def _fallback_assessment(
    task: TaskDefinition,
    result: ExplorationResult,
) -> SupervisorAssessment:
    """Rule-based fallback when LLM is unavailable."""
    step_assessments = []
    for step in result.steps:
        if step.execution_result and step.execution_result.error:
            status = "failed"
            note = f"Error: {step.execution_result.error}"
        elif step.success_evaluation and not step.success_evaluation.satisfied:
            status = "warning"
            note = f"Evaluation failed: {step.success_evaluation.failed_conditions}"
        else:
            status = "ok"
            note = "Completed without error"
        step_assessments.append({
            "step_index": step.step_index,
            "status": status,
            "note": note,
        })

    failed_steps = [s for s in step_assessments if s["status"] == "failed"]
    warning_steps = [s for s in step_assessments if s["status"] == "warning"]

    if result.success and not failed_steps:
        verdict = "success"
        confidence = "medium"
        summary = f"Task '{task.name}' completed successfully in {result.total_steps} steps."
    elif failed_steps:
        verdict = "failure"
        confidence = "high"
        summary = (
            f"Task '{task.name}' failed. "
            f"{len(failed_steps)} step(s) had errors."
        )
    elif warning_steps:
        verdict = "partial_success"
        confidence = "low"
        summary = (
            f"Task '{task.name}' completed but {len(warning_steps)} "
            f"step(s) had evaluation warnings."
        )
    else:
        verdict = "uncertain"
        confidence = "low"
        summary = f"Task '{task.name}' completed but outcome is unclear."

    return SupervisorAssessment({
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "step_assessments": step_assessments,
        "anomalies": [],
        "suggestions": ["(LLM unavailable — no suggestions generated)"],
        "should_save_path": result.success,
    })
