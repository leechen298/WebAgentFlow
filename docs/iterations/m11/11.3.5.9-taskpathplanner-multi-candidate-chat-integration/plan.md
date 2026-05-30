# 实施计划（Implementation Plan）

状态：implementation complete（code review passed，targeted tests passed）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)
- [`../11.3.5.7-pending-choice-active-task-ledger/review.md`](../11.3.5.7-pending-choice-active-task-ledger/review.md)
- [`../11.3.5.8-basic-failure-recovery/review.md`](../11.3.5.8-basic-failure-recovery/review.md)

## 文件 / 模块

Planned implementation files:

- `apps/api/app/services/conversation/chat_runtime.py`
  - build `TaskIntent`
  - build planner candidates from session learned actions
  - call `TaskPathPlanner`
  - build `pending_choice` from ranked session candidates
  - merge planner top-candidate signals into sanitized choice descriptions
  - support `planner_route_choice` selection
- `apps/api/tests/test_conversation_chat_runtime.py`
  - multi-candidate planner integration
  - private map / public payload safety
  - single-path regression
  - failure recovery regression

Optional, only if implementation needs it:

- `apps/api/app/services/conversation/planner_bridge.py`
  - only create this if helpers become too large for `chat_runtime.py`

Do not modify by default:

- `apps/api/app/services/task_planning/planner.py`
- `apps/api/app/schemas/task_planning.py`
- `apps/api/app/services/task_planning/preview.py`

## 步骤

### Step 0 · 设计评审

- Review `contract.md` and `technical-design.md`。
- 确认本包只接 multi-candidate / vague-goal path。
- 确认不使用 `PlanningPreviewService.preview().user_response` 作为 chat reply。
- 确认 `TaskPathPlanner` 只输出 top route plan / warning / risk / uncertainty，
  不输出多候选列表。
- 确认 single-path `/records` happy path 不经过 Planner。

### Step 1 · Current-state preflight

Run read-only checks:

```bash
rg -n "TaskPathPlanner|PlanningPreviewService|LearnedPathCandidate|TaskIntent" \
  apps/api/app/services apps/api/tests
rg -n "pending_choice|pending_choice_private_map|_build_pending_choice|_handle_pending_choice_selection" \
  apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_conversation_chat_runtime.py
```

Expected:

- `TaskPathPlanner` exists and has `plan(task_intent, candidates)`。
- `TaskPathPlanner.plan()` returns one `route_plan` rather than ranked alternatives。
- `pending_choice` private map exists。
- 11.3.5.7 and 11.3.5.8 targeted tests are available and pass.
- 11.3.5.8 recovery choice、retry / relearn / cancel、private payload safety 可用。

### Step 2 · Write adapter tests first

Add tests in `apps/api/tests/test_conversation_chat_runtime.py`:

- multi-candidate branch calls planner and creates pending choice.
- visible pending choice does not include `learned_path_id`.
- private map includes selected internal path id.
- single candidate does not call planner.
- URL present but action vague still enters planner choice when multiple candidates exist.
- "继续" first respects pending / active / recovery context and does not default to Planner.

Expected first run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  -k "planner"
```

Expected: fail because planner bridge is not implemented.

### Step 3 · Implement TaskIntent / candidate helpers

Add minimal helpers in `chat_runtime.py`:

```text
_build_task_intent_for_planner(...)
_planner_candidates_from_session_actions(...)
_planner_signals_for_top_choice(...)
```

Rules:

- current session learned actions only;
- Runtime builds A/B/C from ranked session candidates, not from Planner output;
- Planner output only annotates the mapped top candidate;
- repo metadata only enriches existing candidates;
- no external catalog expansion;
- no LLM / browser / raw HTML.

### Step 4 · Wire multi-candidate branch

Modify `_handle_execute_task()` multi-candidate branch:

```text
len(candidates) > 1 and cannot_confidently_select_single_action
  -> _handle_planner_pending_choice_question(...)
```

Do not use `not user_url` as a gate. `user_url` is a target hint only; URL + vague action
still requires Planner + pending_choice.

Keep existing direct `_handle_pending_choice_question()` as fallback only if planner is unavailable or
adapter returns no planner candidates. When fallback is used, record sanitized
`planner_fallback_used` / `planner_unavailable` event.

### Step 5 · Add planner private choice selection

Extend `_handle_pending_choice_selection()`:

```text
kind == "planner_route_choice"
  -> resolve learned action by private learned_path_id
  -> execute with private slot_overrides
```

Do not expose `learned_path_id` in user response or public progress event.

### Step 6 · Add sanitized planning events

Add progress events with public diagnostics only:

```text
planner_candidates_generated
planner_choice_created
planner_choice_selected
planner_unable_to_plan
planner_fallback_used
```

Payloads may include counts and choice ids, not private ids, slot values, raw route steps,
or private retry / planner payload.

### Step 7 · Run targeted tests

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  -k "planner or pending_choice or recovery or items"
```

Expected: all selected tests pass.

### Step 8 · Run planner regression

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_task_planning_retrieval.py \
  tests/test_task_planning_preview.py \
  tests/test_task_planning_schemas.py
```

Expected: pass. If failures appear, verify they are caused by this package before editing planner service.

### Step 9 · Run safety slice and lint

Run:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_api.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py

uv run ruff check \
  app/services/conversation/chat_runtime.py \
  tests/test_conversation_chat_runtime.py

git diff --check
```

Expected: pass / clean.

### Step 10 · Fill review

Update `review.md` with:

- implementation summary;
- changed files;
- exact test commands and outputs;
- not-run items;
- remaining non-blocking observations.

Do not claim live `wagent chat` or UI smoke unless actually run and recorded.

## Commit suggestion

```bash
git add \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/tests/test_conversation_chat_runtime.py \
  docs/iterations/m11/11.3.5.9-taskpathplanner-multi-candidate-chat-integration/review.md

git commit -m "feat: add planner-backed chat choices"
```
