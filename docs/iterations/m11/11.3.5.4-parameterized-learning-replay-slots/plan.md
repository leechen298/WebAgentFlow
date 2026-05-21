# 实施计划（Plan）

状态：ready_for_implementation（design review passed，未开始实现）

## 前置检查

1. 阅读本目录：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
review.md
```

2. 阅读父包：

```text
../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md
../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md
```

3. 确认 11.3.5.3 `/items` 页面基座已完成。

## 实施步骤

### Step 1：Intake 支持 `item_name`

- 在 `ConversationIntake` deterministic fallback 中抽取 `/items` 新增项目名。
- 保持 LLM schema 可返回 arbitrary slot。
- 增加 tests 覆盖 `名称叫`、`项目名是`、`新增测试项目A`、`name 是`。

### Step 2：Runtime fill values 支持 `item_name`

- 扩展 `_fill_values_from_intake()`。
- 保持 username / password regression。
- 确认 `item_name` 非敏感，credential 仍脱敏。

### Step 3：学习后参数绑定

- 在 learning result 写入 LearnedPath 前后选择最小侵入点。
- 对 fill action value 等于 `fill_values.item_name` 的 action 写入 `value_slot=item_name`。
- 返回 binding report，并在失败时不宣称路径完整可参数化。
- 如遇 dedup existing path，只做 metadata-only merge 或返回 warning。

### Step 4：Replay schema 扩展

- `ReplayRequest` 增加 `slot_overrides` 默认 `{}`。
- `ReplayAction` 增加 `value_slot`。
- `_build_replay_actions()` 读取 raw `value_slot`。
- 如需要，扩展 `ReplayStepLog` 记录 override 证据。

### Step 5：Replay service 应用 override

- 增加 internal `apply_replay_slot_overrides()`。
- 执行前生成 `effective_action`。
- `execute_action()` 使用 `effective_action`。
- `wait_for_change_after_action()` 使用同一个 `effective_action`。
- step log 记录 `value_slot`、`override_applied`、`effective_value`。

### Step 6：Replay hook 传播 `slot_overrides`

- 扩展 `ReplayHandler` protocol。
- 扩展 `run_explicit_replay()` 参数。
- 保持 slash replay 旧调用兼容，默认 `{}`。

### Step 7：Chat runtime execute branch

- execute intent 提取本轮 `fill_values.item_name`。
- matched path 支持 `value_slot=item_name` 时构造 `slot_overrides` 并传入 replay handler。
- matched path 不支持参数化时阻断，不调用 replay。
- 保持 no matched action 的原有 no-path 行为。

### Step 8：测试与回填 review

- 跑 test-plan 中 targeted tests。
- 跑 `git diff --check`。
- 把命令、exit code、pass / fail、未运行项写入 `review.md`。

## 验证命令

Targeted tests：

```bash
cd apps/api
../../.venv/bin/pytest \
  tests/test_conversation_intake.py \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_learning_run_service.py \
  tests/test_learned_path_replay.py
```

Static check：

```bash
git diff --check
```

按实际影响补充：

```bash
uv run ruff check apps/api/app apps/api/tests
```

## 交付清单

- [ ] `item_name` slot extraction。
- [ ] `_fill_values_from_intake()` 支持 `item_name`。
- [ ] LearnedPath actions 支持 `value_slot=item_name`。
- [ ] `ReplayRequest.slot_overrides`。
- [ ] `ReplayAction.value_slot`。
- [ ] `run_replay(... slot_overrides=...)`。
- [ ] `effective_action` 同时用于 execute 和 wait-for-change。
- [ ] step log 证明 override applied。
- [ ] chat runtime execute branch 传递 `slot_overrides`。
- [ ] path 无参数绑定时 runtime 阻断。
- [ ] targeted tests 通过。
- [ ] `review.md` 写入验证证据。

## 明确不做

- 不实现 ExecutionEvidence。
- 不接 TaskResultReporter。
- 不采集 DOM text。
- 不跑 `verify-scenario` / autonomous run。
- 不接 TaskPathPlanner。
- 不做 `pending_choice` / `active_task`。
- 不做 failure recovery 菜单。
