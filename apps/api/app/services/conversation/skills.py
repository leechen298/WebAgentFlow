"""M11.3.5 application skill registry and lightweight runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.schemas.conversation_router import ApplicationSkillName
from app.services.conversation.intake import redact_sensitive_payload

SkillExecutor = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ApplicationSkill:
    name: ApplicationSkillName
    input_contract: str
    output_contract: str
    preconditions: tuple[str, ...]
    executor_owner: str
    browser_access: bool = False
    changes_page: bool = False
    writes_learned_path: bool = False
    requesters: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SkillExecutionResult:
    skill_name: ApplicationSkillName
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class SkillRuntimeError(RuntimeError):
    pass


class ApplicationSkillRegistry:
    """Authoritative in-code registry for M11.3.5 application skills."""

    def __init__(self, skills: list[ApplicationSkill] | None = None) -> None:
        self._skills = {
            skill.name: skill for skill in (skills or default_application_skills())
        }

    def get(self, name: str | ApplicationSkillName) -> ApplicationSkill:
        skill_name = ApplicationSkillName(name)
        try:
            return self._skills[skill_name]
        except KeyError as exc:
            raise KeyError(f"application skill is not registered: {skill_name}") from exc

    def list(self) -> list[ApplicationSkill]:
        return [self._skills[name] for name in ApplicationSkillName]

    def menu_for_prompt(self) -> list[dict[str, Any]]:
        return [
            {
                "name": skill.name.value,
                "executor_owner": skill.executor_owner,
                "browser_access": skill.browser_access,
                "changes_page": skill.changes_page,
                "writes_learned_path": skill.writes_learned_path,
            }
            for skill in self.list()
        ]


class SkillRuntime:
    """Small executor wrapper.

    The Router never receives this object. Only code-side orchestration passes
    through it after validating target scope and MVP boundaries.
    """

    def __init__(
        self,
        registry: ApplicationSkillRegistry | None = None,
        executors: dict[ApplicationSkillName, SkillExecutor] | None = None,
    ) -> None:
        self._registry = registry or ApplicationSkillRegistry()
        self._executors = executors or {}

    @property
    def registry(self) -> ApplicationSkillRegistry:
        return self._registry

    def execute(
        self,
        name: str | ApplicationSkillName,
        payload: dict[str, Any],
    ) -> SkillExecutionResult:
        skill = self._registry.get(name)
        executor = self._executors.get(skill.name)
        if executor is None:
            raise SkillRuntimeError(f"executor is not configured: {skill.name.value}")
        try:
            output = executor(redact_sensitive_payload(payload))
        except Exception as exc:
            return SkillExecutionResult(
                skill_name=skill.name,
                status="failed",
                error=str(exc),
            )
        return SkillExecutionResult(
            skill_name=skill.name,
            status="completed",
            output=redact_sensitive_payload(output or {}),
        )


def default_application_skills() -> list[ApplicationSkill]:
    return [
        ApplicationSkill(
            name=ApplicationSkillName.COLLECT_CONVERSATION_CONTEXT,
            input_contract="session_id and current user message",
            output_contract="redacted conversation context bundle",
            preconditions=("interactive_chat session exists",),
            executor_owner="code",
            requesters=("conversation_orchestrator",),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.INSPECT_TARGET_PAGE,
            input_contract="target URL",
            output_contract="page context bundle with AST and analysis summaries",
            preconditions=("target URL is explicit or resolved",),
            executor_owner="runtime_and_code",
            browser_access=True,
            requesters=("customer_facing_agent_router", "worker_agent"),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.UNDERSTAND_PAGE,
            input_contract="page context bundle",
            output_contract="page understanding result",
            preconditions=("page context is available",),
            executor_owner="page_understanding_agent",
            requesters=("customer_facing_agent_router", "learning_agent"),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.LOOKUP_LEARNED_ACTIONS,
            input_contract="session id and target scope",
            output_contract="current-session learned action summary",
            preconditions=("target scope is known or user goal can be matched",),
            executor_owner="code_repository",
            requesters=("customer_facing_agent_router", "web_operation_agent"),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            input_contract="missing fields and context",
            output_contract="user-facing clarification",
            preconditions=("required target, goal, input, or confirmation is missing",),
            executor_owner="conversation_orchestrator",
            requesters=("customer_facing_agent_router",),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.START_LEARNING,
            input_contract="validated target, goal, slots, and runtime policy",
            output_contract="learning result and LearnedPath summary",
            preconditions=("target scope is valid", "MVP boundary allows learning"),
            executor_owner="learning_service",
            browser_access=True,
            changes_page=True,
            writes_learned_path=True,
            requesters=("learning_agent",),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.START_REPLAY,
            input_contract="validated current-session LearnedPath and target URL",
            output_contract="replay summary and observation evidence",
            preconditions=("current-session learned action matches target scope",),
            executor_owner="replay_service",
            browser_access=True,
            changes_page=True,
            requesters=("web_operation_agent",),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.LEARN_THEN_EXECUTE,
            input_contract="validated complete in-scope task request",
            output_contract="learning result followed by replay summary",
            preconditions=("required inputs are complete", "task is not high impact"),
            executor_owner="skill_runtime",
            browser_access=True,
            changes_page=True,
            writes_learned_path=True,
            requesters=("web_operation_agent", "learning_agent"),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.RECORD_PROGRESS_EVENT,
            input_contract="neutral progress state",
            output_contract="conversation progress event",
            preconditions=("event is user-safe and non-misleading",),
            executor_owner="code",
            requesters=("conversation_orchestrator", "skill_runtime"),
        ),
        ApplicationSkill(
            name=ApplicationSkillName.RECORD_AGENT_TRACE,
            input_contract="redacted Agent output and decision context",
            output_contract="conversation evidence event",
            preconditions=("trace is redacted",),
            executor_owner="code",
            requesters=("agent_runtime",),
        ),
    ]
