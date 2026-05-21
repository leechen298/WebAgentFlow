# Plan

状态：ready_for_implementation（design review passed，未开始实现）

## 阶段 0：实现前检查

- 阅读本包 `intent.md`、`contract.md`、`technical-design.md`、`test-plan.md`。
- 确认 11.3.5.4 参数化 replay 已经合入或当前工作区具备：
  - `ReplayRequest.slot_overrides`
  - `ReplayAction.value_slot`
  - `run_replay(... slot_overrides=...)`
  - `execute_action()` 和 `wait_for_change_after_action()` 使用 `effective_action`
- 确认 `/items` 页面有 `[data-testid='item-list']`。

验证：

```bash
git status --short
rg -n "slot_overrides|value_slot|effective_action" apps/api/app apps/api/tests
rg -n "item-list" apps/product-test-site/src/pages/ItemsPage.vue
```

## 阶段 1：Schema 扩展

修改：

- `apps/api/app/schemas/learned_path_replay.py`
- `apps/api/app/schemas/conversation.py`

任务：

- 新增 `ExecutionEvidenceTarget`。
- 新增 `ExecutionEvidence`。
- `ReplayRequest` 增加 `evidence_targets`。
- `ReplayResult` 增加 `execution_evidence`。
- `ConversationReplaySummary` 增加 `execution_evidence`。

先写 tests：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_path_replay.py -k "evidence or replay_request" -q
```

预期：新增测试先失败，再实现到通过。

## 阶段 2：Replay Evidence Capture

修改：

- `apps/api/app/services/learning/learned_path_replay.py`

任务：

- 新增 `capture_execution_evidence()`。
- 新增 `_capture_dom_text_present()`。
- `run_replay()` 接收 `evidence_targets`。
- 在 replay actions 完成后、runtime stop 前采集 evidence。
- `ReplayResult.execution_evidence` 带出采集结果。

关键实现要求：

- selector 指定时只查 selector 区域。
- `ExecutionEvidence.target = ExecutionEvidenceTarget.text`。
- capture 异常返回 `unknown`，不能覆盖 replay status。
- runtime stop 顺序必须可通过 mock 断言。

验证：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_path_replay.py -q
```

## 阶段 3：Replay Hook / API Propagation

修改：

- `apps/api/app/services/conversation/replay_hook.py`
- `apps/api/app/routers/conversation.py`
- `apps/api/app/routers/exploration.py`

任务：

- `ReplayHandler` / `run_explicit_replay()` 支持 `evidence_targets`。
- Conversation API replay handler 把 `evidence_targets` 传入 `run_explicit_replay()`。
- Exploration replay endpoint 把 `ReplayRequest.evidence_targets` 传入 `run_replay()`。
- `ConversationReplaySummary.execution_evidence` 与 `ReplayResult.execution_evidence` 对齐。

验证：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_replay_hook.py \
  tests/test_exploration_learned_paths_api.py -k replay
```

## 阶段 4：Reporter Adapter / Verified Path

修改：

- `apps/api/app/services/task_planning/result_reporter.py`
- 可选新增内部 helper module，或放在 `apps/api/app/services/conversation/chat_runtime.py`

任务：

- 让 reporter adapter 把 `execution_evidence` 放入 `confirmed_plan_context` 或
  `execution_payload` 的 structured postcondition evidence。
- 修改 `TaskResultReporter._check_postconditions()`，读取 structured evidence。
- verified 只在 replay succeeded / observed、drift none、no error、`dom_text_present`
  verified 且 target 匹配 `slot_overrides.item_name` 时成立。
- missing target 不得 verified。

验证：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_task_planning_result_reporter.py -q
```

## 阶段 5：Chat Runtime Integration

修改：

- `apps/api/app/services/conversation/chat_runtime.py`
- 对应 conversation runtime tests

任务：

- execute branch 根据 `slot_overrides.item_name` 和 `/items` target 构造
  `ExecutionEvidenceTarget(kind="dom_text_present", selector="[data-testid='item-list']")`。
- 调 replay handler 时传入 `evidence_targets`。
- replay 返回后构造 reporter input。
- 用户回复优先使用 reporter outcome。
- `verified` 回复说明看到目标项目。
- `uncertain` / `needs_review` 不说成功。

验证：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q
```

## 阶段 6：Targeted Regression

运行本包 targeted suite：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_learned_path_replay.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_conversation_chat_runtime.py
```

Replay API 边界：

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py -k replay
```

Scoped ruff：

```bash
uv run ruff check \
  apps/api/app/schemas/learned_path_replay.py \
  apps/api/app/schemas/conversation.py \
  apps/api/app/services/learning/learned_path_replay.py \
  apps/api/app/services/conversation/replay_hook.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/task_planning/result_reporter.py \
  apps/api/tests/test_learned_path_replay.py \
  apps/api/tests/test_conversation_replay_hook.py \
  apps/api/tests/test_task_planning_result_reporter.py \
  apps/api/tests/test_conversation_chat_runtime.py
```

Diff hygiene：

```bash
git diff --check
```

## 阶段 7：Review 记录

实现完成后更新 `review.md`：

- 变更文件。
- 关键实现点。
- targeted test 命令和结果。
- scoped ruff 结果。
- `git diff --check` 结果。
- 未运行项：
  - live UI smoke
  - `verify-scenario`
  - autonomous run
  - 11.3.5.6 closed-loop evaluation

不得在本包 review 中声称完整 `/items` learn A / execute B live closed loop 已通过，除非
11.3.5.6 明确执行并记录对应证据。
