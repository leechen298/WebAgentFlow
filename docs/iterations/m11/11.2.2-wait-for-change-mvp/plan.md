# 11.2.2 Wait-for-change MVP 实施计划

状态：后续代码实现计划已准备，能力未实现

本文档是 11.2.2 后续代码实现计划。它不代表 Wait-for-change MVP 已经实现，也不
修改源码、测试、schema 文件或 replay runtime。

## 目标

后续代码实现的目标是为 LearnedPath replay step 生成最小 wait result。

实现后，每个适合等待的 replay action step 应能回答：

- 当前 step 是否进行了等待？
- 等待窗口持续多久？
- 等待过程是否观察到基础页面变化？
- 等待结果是 `observed`、`timeout`、`skipped` 还是 `not_required`？
- 观察到的信号能否作为后续 replay / reporter evidence 的输入？

Wait 层只负责等待、观察和记录。它不判断业务成功，不决定 retry / recovery /
abort，也不调用 Agent 或 Task Result Reporter。

## 计划触及文件

计划修改：

- `apps/api/app/schemas/learned_path_replay.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_learned_path_replay.py`

计划新增：

- `apps/api/app/services/learning/wait_for_change.py`
- `apps/api/tests/test_wait_for_change.py`

计划后续实现完成后再更新：

- `docs/iterations/m11/11.2.2-wait-for-change-mvp/review.md`

不计划修改：

- `docs/roadmap.md`
- `docs/product-model.md`
- `apps/api/app/services/task_planning/`
- `apps/api/app/services/conversation/`
- `apps/api/app/routers/`
- `apps/cli/`
- `package.json`
- `pnpm-lock.yaml`

## 计划 Schema 设计

### 向后兼容的 response schema 扩展

本实现计划不新增 API 路径，不修改数据库 schema，不修改 conversation API，也不新增
runtime public command。

计划只对 replay response 做向后兼容扩展：

```text
ReplayStepLog.wait_result: WaitResult | None = None
```

该字段是可选字段，不能破坏现有不带 `wait_result` 的 replay response、mock result
或 API 测试。

### ObservationSignal

计划在 `apps/api/app/schemas/learned_path_replay.py` 中新增最小
`ObservationSignal` schema。

MVP 计划支持的 signal kind：

```text
url_changed
title_changed
page_load_finished
network_idle_observed
```

11.2.2 当前最小实现不做完整组件库 runtime behavior detection，不识别任意
component-generated runtime surface，也不根据组件库 class 判定 popup / panel 归属。
Common Component Runtime Semantics 记录为 later 11.2.x 增强方向。

计划字段：

- `signal_id`
- `kind`
- `scope`
- `observed_at`
- `source`
- `trigger`
- `related_action_id`
- `related_step_id`
- `url_before`
- `url_after`
- `title_before`
- `title_after`
- `confidence`
- `evidence_weight`
- `is_terminal_candidate`
- `is_error_candidate`
- `notes`

边界：

- 不保存 raw HTML。
- 不保存完整 DOM dump。
- 不保存 LLM reasoning。
- 不保存业务成功结论。
- `network_idle_observed` 只能是 supporting signal。

### WaitResult

计划新增 `WaitResult` schema。

计划字段：

- `wait_id`
- `related_action_id`
- `related_step_id`
- `started_at`
- `ended_at`
- `duration_ms`
- `status`
- `observed_signals`
- `primary_signal`
- `timeout_ms`
- `wait_strategy`
- `notes`

`status` 只允许：

```text
observed
timeout
skipped
not_required
```

语义：

- `observed`：等待窗口内观察到至少一个 primary / target signal。
- `timeout`：等待窗口结束时未观察到 primary / target signal。
- `skipped`：当前 action 不适合主动等待，或 action 失败后不进入 wait。
- `not_required`：调用方或 action 类型明确不需要等待，例如 `observe`。

`timeout`、`skipped`、`not_required` 是 wait outcome，不是 observation signal kind。

## 计划 Wait Service

计划新增：

```text
apps/api/app/services/learning/wait_for_change.py
```

建议接口：

```python
wait_for_change_after_action(
    *,
    page,
    action,
    step_log,
    timeout_ms: int = 1000,
    wait_strategy: str = "short_stability_wait",
) -> WaitResult
```

职责：

- 读取 action 类型和 action execution step log。
- 进行最小 post-action short wait。
- 生成 `WaitResult`。
- 捕获自身异常并返回保守 wait outcome。
- 不改变 replay 主状态。

### Action policy

11.2.2 MVP 计划只对 `click` 启用主动 short wait。

计划行为：

- `click`：运行 `short_stability_wait`。
- `fill`：返回 `skipped`，notes 说明该 MVP 不主动等待纯输入动作。
- `press`：返回 `skipped`，notes 说明 press-triggered submit / search 留给后续增强。
- `observe`：返回 `not_required`。
- action execution failed：返回 `skipped`，notes 说明 action failed before wait。

该策略是 MVP 限制，不表示 `press` 永远不需要 wait。回车触发搜索 / 提交等场景留给后续
增强包处理。

### Exception policy

wait service 异常不能改变 replay status。

如果 wait service 内部失败，计划返回保守结果：

```text
status = skipped 或 timeout
notes = "wait failed: <short error>"
```

不得把原本 action 成功的 replay 改成 failed。

## 计划 Wait Strategy

### short_stability_wait

`short_stability_wait` 是 11.2.2 MVP 唯一必须实现的 wait strategy。

计划逻辑：

1. 从 step log 读取 action 前后的 URL / title。
2. 在短窗口内尝试读取当前 page URL / title。
3. 检测 `url_changed` / `title_changed`。
4. 在有 action-related evidence 时，保守记录 `page_load_finished`。
5. 尝试记录 `network_idle_observed` 作为 supporting signal。
6. 根据 primary / target signal 决定 `status`。

### Primary vs supporting signals

`network_idle_observed` 是 supporting signal only。

它不能作为 `primary_signal`，也不能单独让 wait result 变成业务相关的
`observed`。

11.2.2 MVP 中，`status=observed` 需要至少一个 primary / target signal：

- `url_changed`
- `title_changed`
- `page_load_finished`

如果只观察到 `network_idle_observed`，wait result 必须保持保守，例如：

```text
status = timeout
observed_signals = [network_idle_observed]
primary_signal = None
notes = "network idle observed without primary page-change signal"
```

### Conservative page-load detection

`page_load_finished` 必须保守生成。

调用 `page.wait_for_load_state("load")` 后立即成功，只能说明当前页面已经处于 loaded
状态，不自动证明当前 action 触发了页面加载。

11.2.2 MVP 计划只在有 action-related evidence 时记录 `page_load_finished`：

- URL 变化后观察到页面稳定。
- title 变化后观察到页面稳定。
- 后续实现能够证明 load / navigation completion 与当前 action 相关。

如果没有 URL/title 变化，也没有明确 action-related load evidence，不应单独生成
`page_load_finished`。

## 后续增强：Common Component Runtime Semantics

later 11.2.x 应补充常用组件库运行时语义兼容。它不是 popup support，而是
component-generated runtime surface detection and relation：在 replay action 后，
识别由常用组件库生成或改变的运行时界面片段，并尽可能把新 surface 与触发它的
action / element 关联起来。

runtime surface 包括 dropdown、select option panel、autocomplete panel、cascader
panel、date picker / time picker、popover、tooltip、modal / dialog、drawer、
toast / message、notification、action sheet、bottom sheet、mobile picker、loading
overlay、validation message、virtualized list、inserted option list，以及 active /
selected / checked / disabled / enabled 状态变化。

后续实现原则：

- 优先使用 DOM insertion / removal、visibility change、aria-expanded、
  aria-controls、aria-owns、role=listbox / option / menu / dialog / tooltip、
  selected / checked / disabled / active state、bounding rect proximity、
  insertion timing relative to action、focus movement、active descendant 等通用
  Web 信号。
- 组件库 class 只作为 supporting evidence，不能作为唯一依据。
- 后续兼容范围覆盖 PC / 管理后台组件库：Ant Design、Element Plus、Naive UI、
  Arco Design、TDesign、MUI / Material-ish components、Bootstrap-style components。
- 后续兼容范围覆盖移动端组件库：Ant Design Mobile、Vant、NutUI、Varlet、Ionic、
  Framework7-style mobile components。
- 不调用 Agent 判断业务成功，不让 LLM 进入 L3 per-step execution loop。
- 不阻塞 11.2.2 最小 wait_result / wait_strategy 实现。

## 计划 Replay Integration

计划更新：

```text
apps/api/app/services/learning/learned_path_replay.py
```

计划流程：

```text
for action in precheck.actions:
    log = execute_action(action, runtime)
    wait_result = wait_for_change_after_action(...)
    log["wait_result"] = wait_result
    step_logs.append(log)
```

边界：

- action 失败时仍可记录 `skipped` wait result。
- action 失败仍沿用现有 replay failed 逻辑。
- `observe` action 不强制等待。
- `actions=[]` 的 observational path 保持现状，不生成 step。
- wait result 不改变 replay status 判定。
- 不接 Task Result Reporter。
- 不把 wait result 解释成业务成功。

## 计划测试

### Wait result schema

计划新增或覆盖：

- `observed` 合法。
- `timeout` 合法。
- `skipped` 合法。
- `not_required` 合法。
- 非法 status 被 Pydantic 拒绝。
- `ReplayStepLog.wait_result` 可为空，保持向后兼容。

### Wait service

计划新增 `apps/api/tests/test_wait_for_change.py`，使用 mock page，不启动真实
Playwright。

计划覆盖：

- URL 变化时返回 `status=observed`，`primary_signal=url_changed`。
- title 变化时返回 `status=observed`，`primary_signal=title_changed`。
- URL/title 变化后可保守记录 `page_load_finished`。
- 仅观察到 `network_idle_observed` 时不能返回 `status=observed`。
- `primary_signal` 不能是 `network_idle_observed`。
- 无 primary / target signal 时返回 `timeout` 或其他保守 outcome。
- `observe` action 返回 `not_required`。
- failed action 返回 `skipped`。
- wait service 内部异常返回保守 wait result，不向 replay 主链路抛出。
- signal / wait result 不包含 raw HTML 或 DOM dump。

### Replay integration

计划更新 `apps/api/tests/test_learned_path_replay.py`。

计划覆盖：

- replay 成功 step 中包含 `wait_result`。
- `click` action 后调用 wait-for-change。
- `observe` action 不强制业务等待。
- action 失败时 wait result 不会把 replay 误报为 succeeded。
- wait service 异常不改变 replay 主状态。
- 现有 drift / success / observational path 测试继续通过。

## 计划验证

后续代码实现完成后，计划运行：

```bash
git diff --check
cd apps/api && ../../.venv/bin/pytest tests/test_wait_for_change.py tests/test_learned_path_replay.py -v
cd apps/api && ../../.venv/bin/ruff check app/schemas/learned_path_replay.py app/services/learning/wait_for_change.py app/services/learning/learned_path_replay.py tests/test_wait_for_change.py tests/test_learned_path_replay.py
cd apps/api && ../../.venv/bin/pytest -q
git status --short
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

scoped wait / replay tests 和 ruff 是硬门槛。full API suite 如果环境性失败，必须在
回报中说明失败原因。

## 明确不做

后续代码实现也不得做：

- 不调用 Agent 判断业务成功。
- 不调用 Task Result Reporter。
- 不调用 Page Understanding Agent。
- 不实现 evidence-aware reporter。
- 不做 recovery。
- 不做 retry policy。
- 不做 abort / interruption / user takeover。
- 不实现 Page Context Bridge。
- 不读取 raw HTML。
- 不保存 raw HTML。
- 不创建 M12 / M14 / 11.3 目录。
- 不修改 package 文件。

## 完成措辞

本计划文档完成后只能写：

```text
11.2.2 实施计划已准备，能力未实现。
```

不要写：

- `Wait-for-change MVP implemented`。
- `runtime observation implemented`。
- `page-load waiting implemented`。
- `Task Result Reporter integration complete`。
- `Page Understanding Agent integrated`。
