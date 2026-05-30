# Review and Reflection

## Implementation Decision Closure

These decisions close the initial 11.1.5 open questions before implementation.

- Confirmed-but-not-executed status: `plan_confirmed`. It means user consent is recorded and the plan is ready for a future execution package, but replay has not run.
- Confirm transition: `awaiting_confirmation -> plan_confirmed`.
- Cancel transition: `awaiting_confirmation -> task_intake`, with a `plan_cancelled` event and an assistant message that no execution occurred.
- Reject transition: `awaiting_confirmation -> task_intake`, with a `plan_rejected` event and an assistant message that the plan was not accepted or executed.
- Ambiguous input: keep `awaiting_confirmation`, record `confirmation_clarification_requested`, and ask the user for explicit confirm / cancel / reject. Ambiguous input is never consent.
- New task while awaiting confirmation: do not silently replace the pending preview and do not re-run planning. Record clarification / revision intent, ask the user to cancel or reject the current plan first, and keep `awaiting_confirmation`.
- `/replay` while awaiting confirmation: block it until the pending preview is resolved. Do not call the replay handler. Record `explicit_replay_blocked_by_pending_confirmation` or equivalent event semantics and keep `awaiting_confirmation`.
- Event semantics: `plan_confirmed`, `plan_cancelled`, `plan_rejected`, `confirmation_clarification_requested`, and `explicit_replay_blocked_by_pending_confirmation`.
  `plan_revision_requested` remains optional future scope.
- Implementation boundary: `apps/api/app/services/conversation/confirmation.py` with `PlanConfirmationDecision`, `PlanConfirmationResult`, and `PlanConfirmationService` contracts. That service only classifies awaiting-confirmation input and must not call replay, retrieval, the Task Path Planner, autonomous run, raw HTML readers, or an LLM provider.
- Orchestrator boundary: the confirmation branch runs before planning preview for sessions already in `awaiting_confirmation`, and it blocks `/replay` from bypassing the pending preview.
- Router boundary: continue using the existing dispatch endpoint. Do not add an API endpoint or CLI command in 11.1.5.

## Changed Files

| File | Change |
|---|---|
| `apps/api/app/schemas/conversation.py` | Add `PLAN_CONFIRMED` to `ConversationStatus`; add `PLAN_CONFIRMED`, `PLAN_CANCELLED`, `PLAN_REJECTED`, `CONFIRMATION_CLARIFICATION_REQUESTED`, `EXPLICIT_REPLAY_BLOCKED_BY_PENDING_CONFIRMATION` to `ConversationEventType` |
| `apps/api/app/services/conversation/confirmation.py` | **New.** `PlanConfirmationService` with deterministic keyword classification |
| `apps/api/app/services/conversation/orchestrator.py` | Add confirmation gate: `_handle_awaiting_confirmation_gate`, `_process_confirmation_input`, `_block_replay_awaiting_confirmation`, `_get_pending_plan` |
| `apps/api/app/services/conversation/__init__.py` | Export `PlanConfirmationDecision`, `PlanConfirmationResult`, `PlanConfirmationService` |
| `apps/api/tests/test_conversation_confirmation.py` | **New.** 9 tests for classification, process results, and boundary checks |
| `tests/test_conversation_orchestrator.py` | Add 7 integration tests for confirm, cancel, reject, ambiguous, replay blocked, normal commands, and no-replay marker |
| `tests/test_conversation_api.py` | Add 3 API-level tests for confirm, cancel, and replay blocked through the dispatch endpoint |

## Input Classification Examples

| Input | Decision | Next Status | Event |
|---|---|---|---|
| `confirm` | confirm | `plan_confirmed` | `plan_confirmed` |
| `yes` | confirm | `plan_confirmed` | `plan_confirmed` |
| `proceed` | confirm | `plan_confirmed` | `plan_confirmed` |
| `继续` | confirm | `plan_confirmed` | `plan_confirmed` |
| `/confirm` | confirm | `plan_confirmed` | `plan_confirmed` |
| `cancel` | cancel | `task_intake` | `plan_cancelled` |
| `abort` | cancel | `task_intake` | `plan_cancelled` |
| `stop` | cancel | `task_intake` | `plan_cancelled` |
| `取消` | cancel | `task_intake` | `plan_cancelled` |
| `/cancel` | cancel | `task_intake` | `plan_cancelled` |
| `/abort` | cancel | `task_intake` | `plan_cancelled` |
| `/stop` | cancel | `task_intake` | `plan_cancelled` |
| `reject` | reject | `task_intake` | `plan_rejected` |
| `no` | reject | `task_intake` | `plan_rejected` |
| `不要` | reject | `task_intake` | `plan_rejected` |
| `/reject` | reject | `task_intake` | `plan_rejected` |
| `maybe` | ambiguous | `awaiting_confirmation` | `confirmation_clarification_requested` |
| `looks ok?` | ambiguous | `awaiting_confirmation` | `confirmation_clarification_requested` |
| `run export` | ambiguous | `awaiting_confirmation` | `confirmation_clarification_requested` |

## State Transition Behavior

- `awaiting_confirmation + confirm -> plan_confirmed` (STATE_CHANGED recorded)
- `awaiting_confirmation + cancel -> task_intake` (STATE_CHANGED recorded)
- `awaiting_confirmation + reject -> task_intake` (STATE_CHANGED recorded)
- `awaiting_confirmation + /confirm -> plan_confirmed` (STATE_CHANGED recorded)
- `awaiting_confirmation + /cancel -> task_intake` (plan cancel, not legacy cancel-to-idle)
- `awaiting_confirmation + /abort -> task_intake` (plan cancel, not global abort)
- `awaiting_confirmation + /reject -> task_intake` (plan reject)
- `awaiting_confirmation + ambiguous -> awaiting_confirmation` (no STATE_CHANGED)
- `awaiting_confirmation + /replay -> awaiting_confirmation` (blocked, no STATE_CHANGED)
- `awaiting_confirmation + /status -> awaiting_confirmation` (normal command, falls through)

## Event Payload Examples

**plan_confirmed:**
```json
{
  "user_decision_input": "confirm",
  "decision": "confirm",
  "selected_path_id": "lp-001",
  "selected_purpose": "Export users",
  "warnings": [],
  "risk_hints": [],
  "confirmation_requirements": [],
  "replay_executed": false
}
```

**explicit_replay_blocked_by_pending_confirmation:**
```json
{
  "user_input": "/replay 11111111-1111-1111-1111-111111111111 https://example.invalid/records",
  "reason": "replay_blocked_by_pending_confirmation",
  "selected_path_id": "lp-001",
  "replay_executed": false
}
```

## Assistant Message Examples

- Confirm: "Plan confirmed. The task is ready for future execution. Replay has not run yet."
- Cancel: "The pending plan has been cancelled. No execution occurred."
- Reject: "The plan was not accepted and was not executed. Please describe a revised task."
- Ambiguous: "Please confirm, cancel, reject, or describe a revised task explicitly."
- Replay blocked: "A plan is awaiting confirmation. Please confirm, cancel, or reject the current plan before starting a replay."

## Replay Non-Execution Evidence

- All confirmation gate event payloads set `replay_executed: false`.
- The replay handler is never called while a session is in `awaiting_confirmation`.
- `/replay` while awaiting confirmation returns `allowed: false` with a specific error message.

## Scope Review Checklist

- [x] Implementation only handles confirmation / consent decisions.
- [x] Implementation does not execute replay.
- [x] Implementation does not call autonomous run.
- [x] Implementation does not read raw HTML.
- [x] Implementation does not perform hidden relearning.
- [x] Implementation does not connect an LLM provider.
- [x] Implementation does not implement real slot binding.
- [x] Implementation does not implement result verification, Task Result Reporter, recovery dialogue, or teaching mode.
- [x] Implementation does not add user / account / tenant fields.

## Confirmation Input Checklist

- [x] Confirm inputs are deterministic and explicit.
- [x] Cancel / abort / stop inputs are deterministic and explicit.
- [x] Reject inputs are deterministic and explicit.
- [x] Ambiguous input is not treated as consent.
- [x] Free text while awaiting confirmation follows the chosen revision policy.
- [x] No LLM classifier is required.

## Consent Semantics Checklist

- [x] Confirm records consent or ready-for-execution semantics.
- [x] Confirm does not execute replay.
- [x] Cancel stops the pending preview.
- [x] Reject declines the pending preview.
- [x] High-risk / flaky / provisional plans still require explicit confirmation.
- [x] User decision is auditable.

## State Transition Checklist

- [x] `awaiting_confirmation` is the only entry point for the gate.
- [x] Confirmed-but-not-executed state semantics are explicit (`plan_confirmed`).
- [x] Cancel / reject / revision state semantics are explicit.
- [x] Clarification-needed behavior is explicit.
- [x] State changes are recorded consistently.

## Event Recording Checklist

- [x] Plan confirmation event is recorded.
- [x] Plan cancellation event is recorded.
- [x] Plan rejection event is recorded.
- [x] Clarification-requested event is recorded.
- [x] Event payloads preserve selected path, route summary, warnings, risk hints, confirmation requirements, and user decision input.
- [x] Event payloads explicitly indicate that replay was not executed.

## Assistant Message Checklist

- [x] Confirm response says the plan is confirmed for future execution, not executed.
- [x] Cancel response says the pending plan is cancelled.
- [x] Reject response says the plan was not accepted and was not executed.
- [x] Ambiguous response asks for explicit confirm / cancel / reject / revision.
- [x] Revision response follows the chosen pending-preview policy.

## Explicit Replay Compatibility Checklist

- [x] Existing explicit replay command behavior remains compatible.
- [x] `/replay` while awaiting confirmation follows the documented policy.
- [x] Confirmation input cannot bypass consent and execute replay.
- [x] Existing explicit replay tests still pass.

## Boundary Checklist

- [x] No replay / autonomous / LLM / raw HTML imports are introduced.
- [x] No new API endpoint is added in 11.1.5.
- [x] No CLI command is added.
- [x] No 11.1.6 detail directory is created.
- [x] Existing 11.1.4 planning preview behavior remains compatible.

## Regression Checklist

- [x] Conversation dispatcher / orchestrator tests pass.
- [x] Explicit replay hook tests pass.
- [x] Task planning preview tests pass.
- [x] Conversation API / CLI tests pass if touched.
- [x] `git diff --check` is clean.

## Evidence Checklist

- [x] Changed files are listed.
- [x] Input classification examples are recorded.
- [x] State transition examples are recorded.
- [x] Event payload examples are recorded.
- [x] Replay non-execution evidence is recorded.
- [x] Verification commands and results are recorded.

## Post-Review Fix: Event Type Column Width (P1)

**Issue:** `conversation_events.type` was `String(32)`, but two new event types exceeded this:
- `confirmation_clarification_requested` = 36 chars
- `explicit_replay_blocked_by_pending_confirmation` = 47 chars

SQLite tests passed because SQLite does not enforce `varchar` length, but PostgreSQL would reject these inserts at runtime.

**Fix:**
- Widened `ConversationEvent.type` in ORM from `String(32)` to `String(64)` (`app/models/conversation.py`)
- Added Alembic migration `df9ed1494afd` to `ALTER COLUMN conversation_events.type` from 32 to 64
- Added regression test `test_all_event_type_values_fit_in_database_column` that persists every `ConversationEventType` through the repository to verify database compatibility

## Post-Review Fix: Slash Confirmation Commands (P1)

**Issue:** slash decision commands in `awaiting_confirmation` did not all enter the 11.1.5 confirmation gate:
- `/cancel` parsed as `ConversationCommandKind.CANCEL` and fell through to the legacy state machine, resulting in `idle` instead of `task_intake + plan_cancelled`
- `/abort` parsed as `ConversationCommandKind.ABORT` and fell through to global abort behavior
- `/confirm` and `/reject` parsed as free text but were classified as ambiguous because the classifier did not normalize a leading slash

**Fix:**
- `PlanConfirmationService.classify()` now normalizes a single leading slash before exact keyword matching
- `ConversationOrchestrator._handle_awaiting_confirmation_gate()` now routes `FREE_TEXT`, `CANCEL`, and `ABORT` through the confirmation gate while still blocking `REPLAY`
- `/cancel`, `/abort`, and `/stop` now produce `plan_cancelled` and return to `task_intake`
- `/confirm` now produces `plan_confirmed`
- `/reject` now produces `plan_rejected`
- Added service, orchestrator, and API regression tests so slash decision commands cannot fall back to the legacy state machine

## Verification Commands

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_confirmation.py -v
# 41 passed

cd apps/api && ../../.venv/bin/pytest tests/test_conversation_orchestrator.py -v
# 35 passed

cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py -v
# 37 passed

cd apps/api && ../../.venv/bin/pytest tests/test_conversation_confirmation.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py -q
# 113 passed

cd apps/api && ../../.venv/bin/pytest -q
# 1021 passed, 65 skipped

cd apps/api && ../../.venv/bin/ruff check app/services/conversation/confirmation.py \
  app/services/conversation/orchestrator.py app/schemas/conversation.py \
  app/models/conversation.py alembic/versions/df9ed1494afd_widen_conversation_events_type_to_64_.py \
  tests/test_conversation_confirmation.py tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py
# All checks passed!

git diff --check
# clean
```
