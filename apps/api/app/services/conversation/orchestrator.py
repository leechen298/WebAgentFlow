"""Conversation orchestrator / dispatcher for M11.0.

Pure scheduling skeleton: receives user input, parses commands,
performs state transitions, records messages/events, and returns
user-facing response hints. 11.0.6 adds replay hook integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationCommandKind,
    ConversationEventType,
    ConversationReplaySummary,
    ConversationStatus,
)
from app.services.conversation.commands import parse_command
from app.services.conversation.provenance import (
    CODE_PRODUCER_ORCHESTRATOR,
    code_response_provenance,
    metadata_with_response_provenance,
)
from app.services.conversation.state import next_state


@dataclass
class DispatchResult:
    session_id: str
    previous_status: str
    next_status: str
    command_kind: str
    user_response: str
    events_appended: list[str] = field(default_factory=list)
    message_id: str | None = None
    allowed: bool = False
    error: str | None = None
    engine_command: dict[str, Any] | None = None
    replay_result: ConversationReplaySummary | None = None
    planning_result: Any | None = None


class ConversationOrchestrator:
    def __init__(
        self,
        repo: ConversationRepository,
        replay_handler: Any | None = None,
        planning_handler: Any | None = None,
        execution_handler: Any | None = None,
        learning_handler: Any | None = None,
        intake_service: Any | None = None,
    ) -> None:
        self._repo = repo
        self._replay_handler = replay_handler
        self._planning_handler = planning_handler
        self._execution_handler = execution_handler
        self._learning_handler = learning_handler
        self._intake_service = intake_service

    def dispatch_user_input(
        self,
        session_id: str,
        raw_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> DispatchResult:
        """Dispatch a raw user input through the orchestrator.

        Flow:
        1. Load session (raise ValueError if missing).
        2. Append user message.
        3. Parse command.
        4. Compute next state.
        5. Append ``command_parsed`` audit event.
        6. If transition allowed, update session status and append transition
           / ``state_changed`` events.
        7. For replay commands, run the replay hook and record lifecycle.
        8. Return ``DispatchResult``.
        """
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        previous_status = session.status
        current_status = ConversationStatus(previous_status)

        # 1. Record user message
        message = self._repo.append_message(
            session_id=session_id,
            role="user",
            content=raw_input,
            metadata=metadata,
        )

        # 2. Parse command
        command = parse_command(raw_input)

        if (
            session.current_mode == "interactive_chat"
            and command.kind
            in {ConversationCommandKind.CANCEL, ConversationCommandKind.ABORT}
        ):
            self._clear_pending_intake(session_id)

        # 11.3 — Productized interactive chat happy path.
        if (
            session.current_mode == "interactive_chat"
            and command.kind == ConversationCommandKind.FREE_TEXT
        ):
            from app.services.conversation.chat_runtime import InteractiveChatRuntime

            chat_result = InteractiveChatRuntime(
                self._repo,
                learning_handler=self._learning_handler,
                replay_handler=self._replay_handler,
                intake_service=self._intake_service,
            ).try_handle(
                session=session,
                session_id=session_id,
                raw_input=raw_input,
                command=command,
                message_id=message.id,
                metadata=metadata,
            )
            if chat_result is not None:
                return chat_result

        # 11.1.5 — Confirmation gate for awaiting_confirmation
        if previous_status == ConversationStatus.AWAITING_CONFIRMATION.value:
            gate_result = self._handle_awaiting_confirmation_gate(
                session_id=session_id,
                raw_input=raw_input,
                command=command,
                previous_status=previous_status,
                message_id=message.id,
                metadata=metadata,
            )
            if gate_result is not None:
                return gate_result

        # 11.1.6 — Execution gate for plan_confirmed
        if previous_status == ConversationStatus.PLAN_CONFIRMED.value:
            gate_result = self._handle_plan_confirmed_gate(
                session_id=session_id,
                raw_input=raw_input,
                command=command,
                previous_status=previous_status,
                message_id=message.id,
                metadata=metadata,
            )
            if gate_result is not None:
                return gate_result

        # 3. Compute next state
        transition = next_state(current_status, command)

        # 4. Append command_parsed event
        command_parsed_payload: dict[str, Any] = {
            "raw": raw_input,
            "command_kind": command.kind.value,
            "args": command.args,
            "learned_path_id": command.learned_path_id,
            "url": command.url,
            "text": command.text,
            "parse_error": command.error,
            "allowed": transition.allowed,
            "transition_error": transition.error,
            "dispatch_metadata": metadata or {},
        }
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload=command_parsed_payload,
        )
        events_appended: list[str] = [ConversationEventType.COMMAND_PARSED.value]

        next_status_value = transition.next_status.value
        user_response = transition.response_hint
        replay_result: ConversationReplaySummary | None = None

        # 5. Handle allowed transitions
        if transition.allowed:
            if next_status_value != previous_status:
                self._update_session_status(
                    session_id, previous_status, next_status_value, command.kind
                )

            # Append transition event when it is not merely COMMAND_PARSED
            if transition.event_type != ConversationEventType.COMMAND_PARSED:
                transition_payload: dict[str, Any] = {
                    "from": previous_status,
                    "to": next_status_value,
                    "command_kind": command.kind.value,
                    "transition_event_type": transition.event_type.value,
                    "allowed": transition.allowed,
                    "error": transition.error,
                }
                self._repo.append_event(
                    session_id=session_id,
                    type=transition.event_type,
                    payload=transition_payload,
                )
                events_appended.append(transition.event_type.value)

                # Append state_changed when status changed and transition event
                # is not already STATE_CHANGED
                if (
                    next_status_value != previous_status
                    and transition.event_type != ConversationEventType.STATE_CHANGED
                ):
                    state_changed_payload: dict[str, Any] = {
                        "from": previous_status,
                        "to": next_status_value,
                        "command_kind": command.kind.value,
                        "transition_event_type": transition.event_type.value,
                        "allowed": transition.allowed,
                        "error": transition.error,
                    }
                    self._repo.append_event(
                        session_id=session_id,
                        type=ConversationEventType.STATE_CHANGED,
                        payload=state_changed_payload,
                    )
                    events_appended.append(ConversationEventType.STATE_CHANGED.value)

            # 6. Replay hook integration (11.0.6)
            if (
                command.kind == ConversationCommandKind.REPLAY
                and self._replay_handler is not None
            ):
                replay_result, next_status_value = self._execute_replay_hook(
                    session_id=session_id,
                    learned_path_id=command.learned_path_id,
                    url=command.url,
                    current_status=next_status_value,
                )
                events_appended.extend(
                    [
                        ConversationEventType.STATE_CHANGED.value,
                        (
                            ConversationEventType.REPLAY_COMPLETED.value
                            if next_status_value == "completed"
                            else ConversationEventType.REPLAY_FAILED.value
                        ),
                        ConversationEventType.STATE_CHANGED.value,
                    ]
                )
                user_response = (
                    f"Replay completed ({replay_result.replay_status})."
                    if next_status_value == "completed"
                    else f"Replay failed ({replay_result.replay_status})."
                )

        # 11.1.4 — Planning preview integration for ordinary free-text tasks.
        planning_result: Any | None = None
        if (
            command.kind == ConversationCommandKind.FREE_TEXT
            and self._planning_handler is not None
            and transition.allowed
        ):
            preview = self._planning_handler(raw_input)
            planning_result = preview

            # Append assistant message with preview.
            self._repo.append_message(
                session_id=session_id,
                role="agent",
                content=preview.user_response,
                metadata=metadata_with_response_provenance(
                    {"source": "planning_preview"},
                    code_response_provenance(CODE_PRODUCER_ORCHESTRATOR),
                ),
            )

            # Append planning preview event.
            self._repo.append_event(
                session_id=session_id,
                type=ConversationEventType(preview.event_type),
                payload=preview.event_payload,
            )
            events_appended.append(preview.event_type)

            # Transition to awaiting_confirmation when confirmation is required.
            if (
                preview.confirmation_required
                and next_status_value != ConversationStatus.AWAITING_CONFIRMATION.value
            ):
                self._repo.update_session_status(
                    session_id=session_id,
                    status=ConversationStatus.AWAITING_CONFIRMATION.value,
                )
                self._repo.append_event(
                    session_id=session_id,
                    type=ConversationEventType.STATE_CHANGED,
                    payload={
                        "from": next_status_value,
                        "to": ConversationStatus.AWAITING_CONFIRMATION.value,
                        "command_kind": "free_text",
                        "reason": "plan_preview_requires_confirmation",
                    },
                )
                events_appended.append(
                    ConversationEventType.STATE_CHANGED.value
                )
                next_status_value = ConversationStatus.AWAITING_CONFIRMATION.value

            user_response = preview.user_response

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=next_status_value,
            command_kind=command.kind.value,
            user_response=user_response,
            events_appended=events_appended,
            message_id=message.id,
            allowed=transition.allowed,
            error=transition.error,
            replay_result=replay_result,
            planning_result=planning_result,
        )

    def dispatch_engine_event(
        self,
        session_id: str,
        event_type: ConversationEventType,
        payload: dict[str, Any] | None = None,
    ) -> DispatchResult:
        """Placeholder contract for engine event dispatch.

        11.0.5 records the event but does **not** execute engine side effects,
        browser actions, or Agent routing.
        """
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        previous_status = session.status

        self._repo.append_event(
            session_id=session_id,
            type=event_type,
            payload=payload or {},
        )

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=previous_status,
            command_kind="engine_event",
            user_response="Engine event received.",
            events_appended=[event_type.value],
            allowed=True,
        )

    def _update_session_status(
        self,
        session_id: str,
        current_status: str,
        next_status: str,
        command_kind: ConversationCommandKind,
    ) -> None:
        """Update session status with special handling for pause/resume/cancel."""
        if command_kind == ConversationCommandKind.PAUSE:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
                previous_status=current_status,
            )
        elif command_kind in {
            ConversationCommandKind.RESUME,
            ConversationCommandKind.CANCEL,
        }:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
                previous_status=None,
            )
        else:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
            )

    def _execute_replay_hook(
        self,
        session_id: str,
        learned_path_id: str | None,
        url: str | None,
        current_status: str,
    ) -> tuple[ConversationReplaySummary, str]:
        """Execute replay hook and update session status/events.

        Returns ``(summary, final_status)`` where final_status is
        ``completed`` or ``failed``.
        """
        # Move to replay_running
        self._repo.update_session_status(
            session_id=session_id,
            status="replay_running",
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": current_status,
                "to": "replay_running",
                "command_kind": "replay",
            },
        )

        # Run replay
        try:
            if learned_path_id is None or url is None:
                raise ValueError("replay command missing learned_path_id or url")
            summary: ConversationReplaySummary = self._replay_handler(
                learned_path_id, url
            )
        except Exception as exc:
            summary = ConversationReplaySummary(
                learned_path_id=learned_path_id or "",
                url=url or "",
                replay_status="runtime_error",
                drift_status="none",
                error=str(exc),
            )

        # Determine final status
        if summary.replay_status in ("succeeded", "observed"):
            final_status = "completed"
            lifecycle_event = ConversationEventType.REPLAY_COMPLETED
        else:
            final_status = "failed"
            lifecycle_event = ConversationEventType.REPLAY_FAILED

        # Append replay lifecycle event before the final state change so audit
        # order mirrors the execution flow: running -> result -> final status.
        self._repo.append_event(
            session_id=session_id,
            type=lifecycle_event,
            payload=summary.model_dump(mode="json"),
        )

        # Move to final status
        self._repo.update_session_status(
            session_id=session_id,
            status=final_status,
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": "replay_running",
                "to": final_status,
                "command_kind": "replay",
            },
        )

        return summary, final_status

    # ── 11.1.5 Confirmation gate helpers ───────────────────────────────────────

    def _handle_awaiting_confirmation_gate(
        self,
        session_id: str,
        raw_input: str,
        command: Any,
        previous_status: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> DispatchResult | None:
        """Route input while session is in ``awaiting_confirmation``.

        Returns a ``DispatchResult`` when the gate handles the input
        (confirmation text / slash confirmation commands / ``REPLAY``).
        Returns ``None`` for other commands so the normal state machine can
        process them.
        """
        if command.kind == ConversationCommandKind.REPLAY:
            return self._block_replay_awaiting_confirmation(
                session_id=session_id,
                raw_input=raw_input,
                command=command,
                previous_status=previous_status,
                message_id=message_id,
                metadata=metadata,
            )

        if command.kind in {
            ConversationCommandKind.FREE_TEXT,
            ConversationCommandKind.CANCEL,
            ConversationCommandKind.ABORT,
        }:
            return self._process_confirmation_input(
                session_id=session_id,
                raw_input=raw_input,
                command=command,
                previous_status=previous_status,
                message_id=message_id,
                metadata=metadata,
            )

        return None

    def _block_replay_awaiting_confirmation(
        self,
        session_id: str,
        raw_input: str,
        command: Any,
        previous_status: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> DispatchResult:
        """Block explicit replay while a plan preview is pending."""
        events_appended: list[str] = []

        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload={
                "raw": raw_input,
                "command_kind": command.kind.value,
                "args": command.args,
                "learned_path_id": command.learned_path_id,
                "url": command.url,
                "text": command.text,
                "parse_error": command.error,
                "allowed": False,
                "transition_error": None,
                "dispatch_metadata": metadata or {},
                "gate": "awaiting_confirmation",
            },
        )
        events_appended.append(ConversationEventType.COMMAND_PARSED.value)

        user_response = (
            "A plan is awaiting confirmation. Please confirm, cancel, or reject "
            "the current plan before starting a replay."
        )

        self._repo.append_message(
            session_id=session_id,
            role="agent",
            content=user_response,
            metadata=metadata_with_response_provenance(
                {"source": "confirmation_gate", "decision": "replay_blocked"},
                code_response_provenance(CODE_PRODUCER_ORCHESTRATOR),
            ),
        )

        pending_plan = self._get_pending_plan(session_id)
        payload: dict[str, Any] = {
            "user_input": raw_input,
            "reason": "replay_blocked_by_pending_confirmation",
            "selected_path_id": pending_plan.get("selected_path_id") if pending_plan else None,
            "replay_executed": False,
        }
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.EXPLICIT_REPLAY_BLOCKED_BY_PENDING_CONFIRMATION,
            payload=payload,
        )
        events_appended.append(
            ConversationEventType.EXPLICIT_REPLAY_BLOCKED_BY_PENDING_CONFIRMATION.value
        )

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=previous_status,
            command_kind=command.kind.value,
            user_response=user_response,
            events_appended=events_appended,
            message_id=message_id,
            allowed=False,
            error="Replay is blocked while a plan is awaiting confirmation.",
        )

    def _process_confirmation_input(
        self,
        session_id: str,
        raw_input: str,
        command: Any,
        previous_status: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> DispatchResult:
        """Classify free-text confirmation input and record decision."""
        from app.services.conversation.confirmation import PlanConfirmationService

        events_appended: list[str] = []

        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload={
                "raw": raw_input,
                "command_kind": command.kind.value,
                "args": command.args,
                "learned_path_id": command.learned_path_id,
                "url": command.url,
                "text": command.text,
                "parse_error": command.error,
                "allowed": True,
                "transition_error": None,
                "dispatch_metadata": metadata or {},
                "gate": "awaiting_confirmation",
            },
        )
        events_appended.append(ConversationEventType.COMMAND_PARSED.value)

        service = PlanConfirmationService()
        result = service.process(raw_input)

        self._repo.append_message(
            session_id=session_id,
            role="agent",
            content=result.user_response,
            metadata=metadata_with_response_provenance(
                {"source": "confirmation_gate", "decision": result.decision},
                code_response_provenance(CODE_PRODUCER_ORCHESTRATOR),
            ),
        )

        pending_plan = self._get_pending_plan(session_id)
        payload: dict[str, Any] = {
            "user_decision_input": raw_input,
            "decision": result.decision,
            "selected_path_id": pending_plan.get("selected_path_id") if pending_plan else None,
            "selected_purpose": pending_plan.get("selected_purpose") if pending_plan else None,
            "warnings": pending_plan.get("warnings", []) if pending_plan else [],
            "risk_hints": pending_plan.get("risk_hints", []) if pending_plan else [],
            "confirmation_requirements": pending_plan.get("confirmation_requirements", [])
            if pending_plan
            else [],
            "replay_executed": False,
        }
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType(result.event_type),
            payload=payload,
        )
        events_appended.append(result.event_type)

        next_status = result.next_status
        if next_status != previous_status:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
            )
            self._repo.append_event(
                session_id=session_id,
                type=ConversationEventType.STATE_CHANGED,
                payload={
                    "from": previous_status,
                    "to": next_status,
                    "command_kind": command.kind.value,
                    "reason": f"confirmation_{result.decision}",
                },
            )
            events_appended.append(ConversationEventType.STATE_CHANGED.value)

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=next_status,
            command_kind=command.kind.value,
            user_response=result.user_response,
            events_appended=events_appended,
            message_id=message_id,
            allowed=True,
            error=None,
        )

    def _get_pending_plan(self, session_id: str) -> dict[str, Any] | None:
        """Return the most recent ``plan_preview_proposed`` event payload."""
        events = self._repo.list_events(session_id, limit=100)
        for event in reversed(events):
            if event.type == ConversationEventType.PLAN_PREVIEW_PROPOSED.value:
                return event.payload_json
        return None

    # ── 11.1.6 Execution gate helpers ──────────────────────────────────────────

    def _handle_plan_confirmed_gate(
        self,
        session_id: str,
        raw_input: str,
        command: Any,
        previous_status: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> DispatchResult | None:
        """Route input while session is in ``plan_confirmed``.

        Returns a ``DispatchResult`` when the gate handles the input
        (execution intent). Returns ``None`` for non-execution intent so the
        normal state machine can process it (which will block free text).

        Audit order:
        1. command_parsed
        2. state_changed (plan_confirmed -> executing)
        3. plan_execution_started
        4. replay handler invoked
        5. plan_execution_completed / plan_execution_failed
        6. state_changed (executing -> execution_finished / execution_failed)
        """
        if command.kind != ConversationCommandKind.FREE_TEXT:
            return None
        if self._execution_handler is None:
            return None

        from app.services.conversation.execution import PlanExecutionService

        service = PlanExecutionService()
        decision = service.classify(raw_input)
        if not decision.is_execution_intent:
            return None

        events_appended: list[str] = []

        # Append command_parsed event
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload={
                "raw": raw_input,
                "command_kind": command.kind.value,
                "args": command.args,
                "learned_path_id": command.learned_path_id,
                "url": command.url,
                "text": command.text,
                "parse_error": command.error,
                "allowed": True,
                "transition_error": None,
                "dispatch_metadata": metadata or {},
                "gate": "plan_confirmed",
            },
        )
        events_appended.append(ConversationEventType.COMMAND_PARSED.value)

        # Extract confirmed plan context from events
        all_events = self._repo.list_events(session_id, limit=100)
        confirmed_plan_context = service.extract_confirmed_plan_context(
            all_events
        )

        # Validate preconditions (does NOT call replay)
        validation = service.validate(raw_input, confirmed_plan_context)

        # For blocked executions, record blocked message + event, then report
        if validation.status == "blocked":
            self._repo.append_event(
                session_id=session_id,
                type=ConversationEventType(validation.event_type),
                payload=validation.payload,
            )
            events_appended.append(validation.event_type)

            # 11.1.7 — Result verification and reporting for blocked executions
            from app.services.task_planning.result_reporter import TaskResultReporter

            reporter = TaskResultReporter()
            report = reporter.build_report(
                execution_status=validation.status,
                execution_payload=validation.payload,
                replay_summary=None,
                confirmed_plan_context=confirmed_plan_context,
            )
            self._repo.append_event(
                session_id=session_id,
                type=ConversationEventType.TASK_RESULT_REPORTED,
                payload=report.event_payload,
            )
            events_appended.append(ConversationEventType.TASK_RESULT_REPORTED.value)

            self._repo.append_message(
                session_id=session_id,
                role="agent",
                content=report.user_response,
                metadata=metadata_with_response_provenance(
                    {
                        "source": "execution_gate",
                        "status": validation.status,
                        "verification_outcome": report.outcome,
                        "needs_review": report.needs_review,
                    },
                    code_response_provenance(CODE_PRODUCER_ORCHESTRATOR),
                ),
            )
            return DispatchResult(
                session_id=session_id,
                previous_status=previous_status,
                next_status=previous_status,
                command_kind=command.kind.value,
                user_response=report.user_response,
                events_appended=events_appended,
                message_id=message_id,
                allowed=False,
                error="Execution blocked: required replay context is missing.",
            )

        # Transition to executing BEFORE replay runs (11.1.6 P1)
        self._repo.update_session_status(
            session_id=session_id,
            status="executing",
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": previous_status,
                "to": "executing",
                "command_kind": command.kind.value,
                "reason": "plan_execution_started",
            },
        )
        events_appended.append(ConversationEventType.STATE_CHANGED.value)

        # Record execution started event
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.PLAN_EXECUTION_STARTED,
            payload=validation.payload,
        )
        events_appended.append(
            ConversationEventType.PLAN_EXECUTION_STARTED.value
        )

        # Invoke replay handler
        learned_path_id = validation.payload["learned_path_id"]
        target_url = validation.payload["target_url"]
        try:
            replay_summary: ConversationReplaySummary = (
                self._execution_handler(learned_path_id, target_url)
            )
            result = service.build_result_from_replay(
                raw_input, confirmed_plan_context, replay_summary
            )
        except Exception as exc:
            result = service.build_result_from_error(
                raw_input, confirmed_plan_context, exc
            )
            replay_summary = None  # type: ignore[assignment]

        # Record execution result event
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType(result.event_type),
            payload=result.payload,
        )
        events_appended.append(result.event_type)

        # 11.1.7 — Result verification and reporting
        from app.services.task_planning.result_reporter import TaskResultReporter

        reporter = TaskResultReporter()
        report = reporter.build_report(
            execution_status=result.status,
            execution_payload=result.payload,
            replay_summary=replay_summary,
            confirmed_plan_context=confirmed_plan_context,
        )

        # Append result verification event
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.TASK_RESULT_REPORTED,
            payload=report.event_payload,
        )
        events_appended.append(ConversationEventType.TASK_RESULT_REPORTED.value)

        # Append assistant message with verification report
        self._repo.append_message(
            session_id=session_id,
            role="agent",
            content=report.user_response,
            metadata=metadata_with_response_provenance(
                {
                    "source": "execution_gate",
                    "status": result.status,
                    "verification_outcome": report.outcome,
                    "needs_review": report.needs_review,
                },
                code_response_provenance(CODE_PRODUCER_ORCHESTRATOR),
            ),
        )

        # Transition to final status
        next_status = result.next_status
        self._repo.update_session_status(
            session_id=session_id,
            status=next_status,
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": "executing",
                "to": next_status,
                "command_kind": command.kind.value,
                "reason": result.event_type,
            },
        )
        events_appended.append(ConversationEventType.STATE_CHANGED.value)

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=next_status,
            command_kind=command.kind.value,
            user_response=report.user_response,
            events_appended=events_appended,
            message_id=message_id,
            allowed=True,
            error=None,
            replay_result=replay_summary,
        )

    def _clear_pending_intake(self, session_id: str) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        if "pending_intake" not in metadata:
            return
        metadata.pop("pending_intake", None)
        from app.services.conversation.chat_runtime import (
            clear_pending_sensitive_values,
        )

        clear_pending_sensitive_values(session_id)
        session.metadata_json = metadata
        self._repo.session.commit()
        self._repo.session.refresh(session)
