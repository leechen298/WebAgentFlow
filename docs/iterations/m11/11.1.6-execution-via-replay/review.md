# Review and Reflection

## 11.1.6 Execution via Replay Implementation Report

### Changed files

| File | Change |
|---|---|
| `apps/api/app/schemas/conversation.py` | Add `EXECUTING`, `EXECUTION_FINISHED`, `EXECUTION_FAILED` to `ConversationStatus`; add `PLAN_EXECUTION_STARTED`, `PLAN_EXECUTION_COMPLETED`, `PLAN_EXECUTION_FAILED`, `PLAN_EXECUTION_BLOCKED` to `ConversationEventType` |
| `apps/api/app/services/conversation/execution.py` | **New.** `PlanExecutionService` deterministic classifier + context extractor + result builders; replay invocation is caller-side (orchestrator) so `executing` / `started` are recorded before replay runs |
| `apps/api/app/services/conversation/orchestrator.py` | Add execution gate: `_handle_plan_confirmed_gate`, inject `execution_handler`, state transitions through `executing` -> `execution_finished` / `execution_failed` |
| `apps/api/app/services/conversation/__init__.py` | Export `PlanExecutionDecision`, `PlanExecutionResult`, `PlanExecutionService` |
| `apps/api/app/routers/conversation.py` | Wire `execution_handler=replay_handler` into `ConversationOrchestrator` |
| `apps/api/tests/test_conversation_execution.py` | **New.** Service-level tests for classification, context extraction, confirmed-preview binding, blocked cases, replay result builders, payload boundaries, forbidden imports |
| `apps/api/tests/test_conversation_orchestrator.py` | Integration tests for execution gate covering success, blocked, failure, non-execution text, explicit replay compatibility, handler-after-executing audit order, missing-confirmed-event blocked, mismatch-path-id blocked, unconfirmed-preview ignored |
| `apps/api/tests/test_conversation_api.py` | API-level tests for blocked execution, successful execution, explicit replay compatibility |

### Implemented behavior

- `plan_confirmed` + execution intent (`execute`, `run`, `start`, `执行`, `开始`) → deterministic replay execution.
- Execution context recovered from audited conversation events; **both** `plan_preview_proposed` and `plan_confirmed` events are required, bound by matching `selected_path_id`, with preview chronologically preceding confirm (P2).
- Missing context → `plan_execution_blocked` event, session stays `plan_confirmed`.
- Successful replay → `plan_execution_started` recorded **before** replay runs (P1), then `plan_execution_completed`, session becomes `execution_finished`.
- Failed replay → `plan_execution_started` recorded **before** replay runs (P1), then `plan_execution_failed`, session becomes `execution_failed`.
- Multi-step routes → blocked.
- Non-execution free text in `plan_confirmed` → not intercepted by execution gate, falls through to state machine (blocked).

### Execution trigger

Exact-match tokens only (strip, lowercase for ASCII; strip for CJK):
- `execute`
- `run`
- `start`
- `执行`
- `开始`

No LLM classifier, no fuzzy inference, no new API endpoint or CLI command.

### Missing context behavior

When `learned_path_id` or `target_url` is missing from the confirmed plan context:
- No replay invocation.
- `plan_execution_blocked` event recorded.
- Assistant message: "The confirmed plan is not executable because required replay context is missing."
- Session stays `plan_confirmed`.

### Replay invocation boundary

- Reuses existing `run_explicit_replay` / `replay_handler` deterministic capability.
- `learned_path_id` and `target_url` must come from confirmed plan event context.
- No autonomous run, no raw HTML, no LLM, no slot binding, no invented actions.

### Events / states

New statuses:
- `executing`
- `execution_finished` (does NOT mean task succeeded)
- `execution_failed`

New event types (all ≤ 24 chars, fit in `String(64)`):
- `plan_execution_started`
- `plan_execution_completed`
- `plan_execution_failed`
- `plan_execution_blocked`

Event payloads consistently include:
- `no_result_verification: true`
- `no_autonomous: true`
- `task_verified: false` (completed / failed events)

### Explicit replay compatibility

- Explicit `/replay` remains compatible in states where the existing state machine already allows explicit replay (e.g. `idle`, `task_intake`).
- `/replay` while `awaiting_confirmation` or `plan_confirmed` is not allowed to bypass the pending / confirmed plan flow.
- Confirmed-plan execution and explicit replay are separate entry paths sharing the same underlying deterministic replay handler.

### Result verification boundary

- `plan_execution_completed` means replay invocation completed, NOT task succeeded.
- No business result verified, no artifact produced, no form submission confirmed.
- No Task Result Reporter, no recovery, no teaching mode.

### Tests

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_conversation_execution.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py \
  tests/test_conversation_replay_hook.py \
  tests/test_conversation_confirmation.py -q
```
Result: `175 passed`

```bash
cd apps/api && ../../.venv/bin/pytest -q
```
Result: `1074 passed, 65 skipped`

```bash
cd apps/api && ../../.venv/bin/ruff check \
  app/schemas/conversation.py \
  app/services/conversation/orchestrator.py \
  app/services/conversation/execution.py \
  app/routers/conversation.py \
  tests/test_conversation_execution.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py
```
Result: `All checks passed!`

```bash
cd apps/api && ../../.venv/bin/alembic heads
```
Result: `df9ed1494afd (head)` — no new migration needed, all event types fit in `String(64)`.

```bash
git diff --check
```
Result: clean

### Verification

- [x] Implementation only executes already confirmed plans.
- [x] Implementation does not execute from raw user text.
- [x] Implementation does not call Task Path Planner for re-planning.
- [x] Implementation does not call autonomous run.
- [x] Implementation does not read raw HTML.
- [x] Implementation does not perform hidden relearning.
- [x] Implementation does not connect an LLM provider.
- [x] Implementation does not implement slot binding, result verification, Task Result Reporter, recovery dialogue, or teaching mode.
- [x] Missing LearnedPath id records execution-blocked semantics.
- [x] Missing target URL records execution-blocked semantics.
- [x] Missing `plan_confirmed` event records execution-blocked semantics (P2).
- [x] Confirmed and preview `selected_path_id` mismatch records execution-blocked semantics (P2).
- [x] Newer unconfirmed preview is ignored; execution binds to the confirmed preview (P2).
- [x] Replay completed is not reported as task succeeded.
- [x] `plan_execution_started` and `executing` state are recorded **before** replay handler runs (P1).
- [x] Explicit `/replay` compatibility preserved in allowed states.
- [x] `/replay` while `awaiting_confirmation` still blocked by 11.1.5.
- [x] No new API endpoint or CLI command added.

### Non-goals preserved

- Result verification: future scope.
- Task Result Reporter: future scope.
- Recovery dialogue: future scope.
- Teaching mode: future scope.
- Slot binding / form filling: future scope.
- Multi-step route execution: future scope.
- 11.1.7 directory: not created.
