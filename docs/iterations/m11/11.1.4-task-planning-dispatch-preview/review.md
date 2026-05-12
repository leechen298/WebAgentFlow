# Review and Reflection

## Scope Review Checklist

- [x] Implementation only connects conversation runtime to planning preview.
- [x] Implementation does not execute replay.
- [x] Implementation does not call autonomous run.
- [x] Implementation does not read raw HTML.
- [x] Implementation does not perform hidden relearning.
- [x] Implementation does not connect an LLM provider.
- [x] Implementation does not implement real slot binding.
- [x] Implementation does not implement result verification, recovery dialogue,
  or teaching mode.
- [x] Implementation does not add user / account / tenant fields.

## Conversation Integration Checklist

- [x] Ordinary free-text task requests can enter the preview path.
- [x] Slash command behavior remains explicit.
- [x] Malformed slash commands do not fall through to task planning preview.
- [x] Conversation message / event records the preview output.
- [x] Planner output remains reviewable by later confirmation / execution
  layers.

## Explicit Replay Compatibility Checklist

- [x] `/replay <learned_path_id> <url>` behavior is unchanged.
- [x] Replay hook is not called for ordinary task preview.
- [x] Task planning preview does not wrap replay result as a plan execution.
- [x] Existing replay tests still pass.

## TaskIntent Construction Checklist

- [x] `raw_text` preserves original user input.
- [x] `normalized_goal` is optional and deterministic-only (not populated).
- [x] No slot binding or business parameter inference occurs.
- [x] No LLM classifier is required.

## Retrieval / Planner Orchestration Checklist

- [x] Retrieval service receives `TaskIntent`.
- [x] Task Path Planner receives ranked candidates from retrieval.
- [x] Dispatcher coordinates retrieval and planning without merging their
  responsibilities.
- [x] Planner does not call retrieval internally.

## Planning Preview Output Checklist

- [x] Preview response includes plan-proposed / confirmation-needed /
  unable-to-plan semantics.
- [x] Selected LearnedPath id is preserved when available.
- [x] Warnings are preserved.
- [x] Risk hints are preserved.
- [x] Match reasons are preserved.
- [x] Confirmation requirements are preserved.
- [x] Preview does not claim execution.

## Confirmation State Checklist

- [x] Confirmation-pending semantics are explicit (`awaiting_confirmation`).
- [x] Execution is blocked until future confirmation / consent logic allows it.
- [x] User cancellation or clarification remains auditable.
- [x] State changes are recorded consistently.

## No-Candidate Checklist

- [x] No candidates returns unable-to-plan.
- [x] No fake `RoutePlan` is generated.
- [x] No autonomous learning starts automatically.
- [x] No hidden relearning starts automatically.
- [x] No browser operation occurs.
- [x] User-facing response is clear and auditable.

## Boundary Checklist

- [x] No replay / autonomous / LLM / raw HTML imports in preview service.
- [x] No new API endpoint is added in 11.1.4.
- [x] Existing conversation dispatch endpoint wired with PlanningPreviewService.
- [x] Dedicated planning preview API remains future scope.
- [x] No CLI command is added.
- [x] No 11.1.5 detail directory is created.
- [x] Existing M11.0 conversation behavior remains compatible (backward
  compatible when `planning_handler=None`).

## Regression Checklist

- [x] Conversation dispatcher / orchestrator tests pass (31 passed).
- [x] Explicit replay hook tests pass.
- [x] Task planning schema tests pass.
- [x] LearnedPath retrieval tests pass.
- [x] Task Path Planner tests pass.
- [x] `git diff --check` is clean.

## Evidence Checklist

- [x] Changed files are listed.
- [x] Dispatch behavior examples are recorded.
- [x] Preview message / event payload examples are recorded.
- [x] Boundary checks are recorded.
- [x] Verification commands and results are recorded.

## Decisions Made in This Implementation

- **Conversation status for planning preview pending**: `awaiting_confirmation`
  (already existed in M11.0 schema).
- **Preview output storage**: Both assistant message and event are stored.
- **Event types**: `PLAN_PREVIEW_PROPOSED` and `PLAN_PREVIEW_UNABLE` added to
  `ConversationEventType`.
- **Retrieved candidates in event payload**: Stored as count + selected path id +
  match reasons summary, not full candidate payloads.
- **Dispatch endpoint**: Ordinary task preview remains behind the existing
  `/conversation/sessions/{id}/dispatch` endpoint. No dedicated preview API.
- **Planning handler injection**: `ConversationOrchestrator` accepts an optional
  `planning_handler` callable, keeping the orchestrator decoupled from
  task-planning module internals.
- **All proposed previews require confirmation**: 11.1.4 boundary is
  "preview then stop and wait for confirmation". Any proposed plan enters
  `awaiting_confirmation`; unable-to-plan remains in `task_intake`.
- **Backward compatibility**: When `planning_handler` is `None`, FREE_TEXT
  behavior is unchanged ("Task input recorded.", `task_intake`).

## Changed Files

- `apps/api/app/schemas/conversation.py` — add `PLAN_PREVIEW_PROPOSED`,
  `PLAN_PREVIEW_UNABLE` event types.
- `apps/api/app/routers/conversation.py` — wire `PlanningPreviewService` into
  `/conversation/sessions/{id}/dispatch` endpoint.
- `apps/api/app/services/task_planning/preview.py` — new
  `PlanningPreviewResult` + `PlanningPreviewService`.
- `apps/api/app/services/task_planning/__init__.py` — export preview types.
- `apps/api/app/services/conversation/orchestrator.py` — integrate optional
  `planning_handler` into FREE_TEXT dispatch flow; append assistant message
  and preview event; transition to `awaiting_confirmation` when required.
- `apps/api/tests/test_task_planning_preview.py` — new (9 tests).
- `apps/api/tests/test_conversation_orchestrator.py` — add 5 planning preview
  integration tests.
- `apps/api/tests/test_conversation_api.py` — update dispatch tests for
  planning preview runtime behavior; add API-level proposed-preview test.

## Verification Commands

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_preview.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py -v
# 34 passed

cd apps/api && ../../.venv/bin/ruff check app/services/task_planning/preview.py app/services/task_planning/__init__.py app/services/conversation/orchestrator.py app/schemas/conversation.py app/routers/conversation.py tests/test_task_planning_preview.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py
# All checks passed!

cd apps/api && ../../.venv/bin/pytest -q
# 962 passed, 65 skipped

git diff --check
# clean
```
