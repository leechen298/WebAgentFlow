# 实施计划（Implementation Plan）

状态：implementation complete（code review passed，targeted tests passed）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)
- [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)
- [`../11.3.5.6-wagent-chat-records-closed-loop-evaluation/review.md`](../11.3.5.6-wagent-chat-records-closed-loop-evaluation/review.md)

## 文件 / 模块

Planned implementation files:

- `apps/api/app/services/conversation/context.py` - `PendingChoice` / `ActiveTask`
  internal models and context parsing.
- `apps/api/app/services/conversation/entry_gate.py` - pending choice / active task
  forces heavy runtime.
- `apps/api/app/services/conversation/chat_runtime.py` - choice creation, selection,
  active task helpers, cancel cleanup, expiry handling.
- `apps/api/app/services/conversation/router_agent.py` - ensure Router prompt only
  receives safe visible state if touched.
- `apps/api/tests/test_conversation_chat_runtime.py` - primary integration tests.
- `apps/api/tests/test_conversation_entry_gate.py` - entry gate tests if needed.
- `apps/api/tests/test_conversation_router_agent.py` - LLM-facing safety tests if needed.
- `docs/iterations/m11/11.3.5.7-pending-choice-active-task-ledger/review.md` -
  implementation evidence.

## 步骤

### Step 0 · 设计评审

- Review `contract.md` and `technical-design.md`.
- Confirm whether to add new event enum or reuse existing chat progress / trace events.
- Confirm that 11.3.5.7 remains one package; if scope expands, split active_task cleanup into a later package before coding.

### Step 1 · Current-state preflight

Run read-only checks:

```bash
rg -n "pending_intake|pending_target|last_no_path_reason|learned_actions|clear_pending_runtime_context" \
  apps/api/app/services/conversation apps/api/tests
rg -n "pending_choice|active_task" apps/api/app apps/api/tests
```

Expected:

- Existing pending intake / target helpers are present.
- `pending_choice` and `active_task` are not already implemented, or any partial implementation is understood before editing.

### Step 2 · Add internal state models

- Add `PendingChoice`, `PendingChoiceOption`, `ActiveTask` internal models.
- Add parse helpers that ignore / clear malformed metadata safely.
- Extend context bundle with safe visible `pending_choice` and `active_task`.
- Keep private map out of LLM-facing context.

### Step 3 · Entry Gate integration

- Add `pending_choice_exists` and `active_task_exists` to entry gate context.
- Ensure short messages such as `A` enter heavy runtime when `pending_choice` exists.
- Add targeted tests.

### Step 4 · Runtime choice helpers

- Add helpers:

```text
_save_pending_choice()
_clear_pending_choice()
_pending_choice()
_pending_choice_private_map()
_parse_choice_reply()
_decrement_or_expire_pending_choice()
```

- Ensure visible payload has no private id.
- Ensure private map is stored / read internally only.

### Step 5 · Choice creation

- Refactor candidate matching so multiple learned action matches can produce choice.
- Single candidate remains direct execution.
- Multiple candidates create A/B/C response and write `active_task.kind=clarify`.
- Do not call TaskPathPlanner.

### Step 6 · Choice selection and correction

- If pending choice exists and user chooses A/B/C, resolve private map and continue selected branch.
- If input is correction text, clear pending choice and rerun normal intake.
- If invalid answer, decrement turns and ask again.
- If expired, clear and ask user to restate.

### Step 7 · Active task ledger

- Add `_set_active_task()`, `_update_active_task()`, `_clear_active_task()`.
- Insert minimal updates in ask / learning / execution branches.
- On success, failure, and cancel, clean live active task.
- Do not build full event-sourced ledger.

### Step 8 · Cancel cleanup

- Extend `clear_pending_runtime_context()` and runtime cancel branch to clear:

```text
pending_intake
pending_target
pending_choice
pending_choice_private_map
last_no_path_reason
active_task
pending sensitive values
```

- Add `/cancel` and Chinese cancel tests where current command path supports them.

### Step 9 · Regression tests and review

Run targeted tests and scoped lint. Update `review.md` with:

- files changed
- tests run
- pass / fail counts
- not-run boundaries
- any deviation from design

## 验证

验证计划来自 `technical-design.md` 的 high-level Test Matrix 和 `test-plan.md` 的详细测试矩阵。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_entry_gate.py tests/test_conversation_router_agent.py` | pending choice / active task targeted tests pass | Yes | Actual files may be scoped if implementation touches fewer modules |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_task_planning_result_reporter.py tests/test_learned_path_replay.py tests/test_learning_run_service.py` | P0 working loop regression stays green | Yes | No live browser |
| `uv run ruff check ...` | changed Python files are lint-clean | Yes | Use actual changed file list |
| `git diff --check` | whitespace clean | Yes | Required |

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] `pending_choice` visible payload 不包含 `learned_path_id`。
- [ ] private map 不进入 Router prompt / LLM trace / WAgent reply。
- [ ] `A` / `1` / `第一个` deterministic choice parser 可用。
- [ ] correction input 清理旧 choice 并重新 intake。
- [ ] `pending_choice` 过期会清理。
- [ ] `active_task` learning / execution / clarify 写入和清理符合 contract。
- [ ] `/cancel` 和中文取消清理 pending / active state。
- [ ] 单候选 `/records` happy path 不受影响。
- [ ] 未接 TaskPathPlanner。
- [ ] 未实现 failure recovery 菜单。
- [ ] 未运行 `verify-scenario` 或 autonomous run。
- [ ] 验证命令已执行并记录到 `review.md`，或写明 not run / unverified 和原因。
