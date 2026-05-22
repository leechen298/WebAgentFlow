# 实施计划（Implementation Plan）

状态：draft_docs（待评审，未开始实现）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)
- [`../11.3.5.7-pending-choice-active-task-ledger/review.md`](../11.3.5.7-pending-choice-active-task-ledger/review.md)

## 文件 / 模块

Planned implementation files:

- `apps/api/app/services/conversation/chat_runtime.py` - failure classification、
  recovery offer、retry / relearn / cancel handling。
- `apps/api/app/services/conversation/context.py` - 如需要，扩展 recovery private
  payload parsing。
- `apps/api/app/services/conversation/history.py` - 如 private payload 新字段需要
  public sanitizer 覆盖。
- `apps/api/tests/test_conversation_chat_runtime.py` - 主集成测试。
- `apps/api/tests/test_conversation_api.py` - public sanitizer 回归，如果触及 API payload。
- `docs/iterations/m11/11.3.5.8-basic-failure-recovery/review.md` - 实现证据。

## 步骤

### Step 0 · 设计评审

- Review `contract.md` and `technical-design.md`。
- 确认复用 `pending_choice`，不新增 `pending_recovery` public contract。
- 确认 retry 最大次数和 relearn 是否自动执行。默认：最多自动 retry 一次，relearn 不自动执行。

### Step 1 · Current-state preflight

Run read-only checks:

```bash
rg -n "pending_choice|pending_choice_private_map|active_task" \
  apps/api/app/services/conversation apps/api/tests
rg -n "TaskResultReporter|verification_outcome|execution_evidence|CHAT_EXECUTION_FAILED" \
  apps/api/app/services/conversation apps/api/tests
```

Expected:

- 11.3.5.7 choice / active task helpers 已存在。
- 11.3.5.7 private map 不会通过 session public API / Router payload / LLM trace 外泄。
- 11.3.5.5 reporter / evidence paths 已存在。

Before implementation, run or confirm the 11.3.5.7 targeted tests that cover:

```text
pending choice creation
choice selection
choice miss / expiry
cancel cleanup
active_task updates
session public payload sanitization
slot_overrides preservation through choice selection
```

### Step 2 · Add failure classification helper

Add helper to classify:

```text
replay_failed
blocked
evidence_missing
needs_review
uncertain
```

Do not introduce complex taxonomy.

### Step 3 · Add recovery choice builder

- Build visible A/B/C choices.
- Build private map with retry / relearn / cancel payload.
- Use `重试执行该操作` as the visible retry label.
- Ensure public payload has no `learned_path_id`, `slot_overrides`, selector or replay action.
- Add unit tests.

### Step 4 · Offer recovery from execution failures

- In `_execute_matched_action()`, when replay / reporter result is not verified or safe completion,
  call recovery offer helper.
- Response must preserve conservative failure wording.
- Set active task to waiting for user input.
- Record `failure_recovery_offered`.

### Step 5 · Handle recovery selection

Extend pending choice selection private map handling:

```text
retry_replay -> retry helper
relearn_operation -> learning branch
cancel -> cancel cleanup
learned_action -> existing 11.3.5.7 behavior
```

### Step 6 · Implement retry

- Reuse learned path, target URL, slot overrides and evidence target.
- No Planner.
- No LLM.
- No automatic retry loop.
- Every user choice A triggers at most one replay retry.
- For evidence missing / uncertain / needs_review, user-facing text must say retry executes the operation again and may repeat side effects.
- Add tests proving `slot_overrides.item_name` is preserved.

### Step 7 · Implement relearn

- Start learning for original target/action.
- If target or goal is missing, ask missing info and write pending.
- Do not auto execute after learning.
- Add tests.

### Step 8 · Cancel cleanup

- Ensure recovery choice cancel uses the same cleanup path as runtime cancel.
- Add Chinese cancel regression if not already covered.

### Step 9 · Validation

Run commands from `test-plan.md`:

```bash
cd apps/api

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_api.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py \
  tests/test_learning_run_service.py

uv run ruff check \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/conversation/context.py \
  apps/api/app/services/conversation/history.py \
  apps/api/tests/test_conversation_chat_runtime.py \
  apps/api/tests/test_conversation_api.py

git diff --check
```

### Step 10 · Review update

Implementation agent should not edit iteration docs if using `webagentflow-iteration-dev`.
If performing manual closeout outside that skill, update `review.md` with:

- changed files
- tests run
- skipped live run reasons
- review findings and fixes
