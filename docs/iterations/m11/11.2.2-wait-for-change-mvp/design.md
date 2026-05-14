# Wait-for-change MVP 设计

状态：文档级 design proposal，能力未实现

本文档定义 11.2.2 Wait-for-change MVP 的文档级设计。它不创建代码 schema，不修改
API，不修改 replay execution，也不接入 Task Result Reporter。

## 定义

Wait-for-change MVP 是 replay action 执行后的短窗口观察机制，用于等待并记录页面
是否出现可观察变化。

它用于回答：

- 当前 action 之后是否出现了可观察变化？
- 出现了哪些 observation signals？
- 等待是命中变化、超时、跳过，还是明确不需要？
- 这些结果能否作为后续 replay evidence / reporter evidence 的输入？

它不是：

- retry policy。
- recovery plan。
- abort decision。
- user takeover。
- 最终 result report。
- 业务成功判断。
- 完整 passive runtime observer。
- WebSocket / SSE 专用监听器。

## MVP 范围

11.2.2 MVP 主要处理 replay action 后的短窗口观察，即 `post_action` wait。

`passive_runtime` 变化先保留在 11.2.1 contract 和后续设计中，不在 11.2.2 MVP 中
实现连续后台观察。

### MVP 优先覆盖的 Signal

MVP 优先覆盖这些 11.2.1 signal kind：

```text
url_changed
title_changed
text_appeared
element_appeared
element_enabled
element_disabled
modal_opened
toast_shown
loading_finished
page_load_finished
list_changed
form_validation_message
network_idle_observed
spa_content_changed
```

### 可观察但非 MVP 主目标的 Signal

下列 signal 可以作为后续增强方向，或仅作为非 MVP 观察方向记录：

```text
page_load_started
loading_started
text_disappeared
element_disappeared
modal_closed
passive_dom_mutation
server_push_update
```

`page_load_started` 和 `loading_started` 对诊断有价值，但 MVP 的等待终止通常依赖
`page_load_finished`、`loading_finished` 或其他可见完成信号。

`passive_dom_mutation` 和 `server_push_update` 偏 `passive_runtime`，不作为 11.2.2
MVP 的主要实现目标。

## Wait Result

Wait Result 是文档级 proposal，不是已实现 schema。

建议字段：

| 字段 | 含义 | 边界 |
|---|---|---|
| `wait_id` | wait result 的唯一标识。 | 11.2.2 不规定格式。 |
| `related_action_id` | 关联 replay action。 | 可为空；不代表业务成功。 |
| `related_step_id` | 关联 replay step。 | 可为空；用于后续 replay evidence 关联。 |
| `started_at` | 等待开始时间。 | 用于排序和耗时计算。 |
| `ended_at` | 等待结束时间。 | 不等于任务完成时间。 |
| `duration_ms` | 等待耗时。 | 可由 `started_at` / `ended_at` 推导。 |
| `status` | 等待结果状态。 | 只使用 `observed`、`timeout`、`skipped`、`not_required`。 |
| `observed_signals` | 等待窗口内观察到的 signal 列表。 | 引用 11.2.1 signal，不内嵌 raw HTML。 |
| `primary_signal` | 代表性 signal。 | 只是当前 wait 的主要观察，不等于业务成功。 |
| `timeout_ms` | 等待窗口上限。 | timeout 是 wait outcome，不是 signal kind。 |
| `wait_strategy` | 使用的等待策略。 | 只是后续实现方向，不表示能力已实现。 |
| `notes` | 简短备注。 | 不写 raw HTML，不写 Agent reasoning。 |

### Wait Status

`status` 收敛为：

```text
observed
timeout
skipped
not_required
```

- `observed`：等待窗口内观察到至少一个符合条件的 signal。
- `timeout`：等待窗口结束时没有观察到符合条件的 signal。
- `skipped`：当前 action 不适合等待，例如纯键盘输入、无页面变化预期的 action。
- `not_required`：调用方明确声明本 step 不需要等待变化。

`timeout`、`skipped`、`not_required` 是 wait result，不是 observation signal kind。

`observed_signals` 引用 11.2.1 定义的 signal，不内嵌 raw HTML。`primary_signal`
只是代表性信号，不等于业务成功。

### Wait Result and Reporter Consumption

Wait Result 不是最终任务结果。

Wait Result 只描述某个 replay action 后的等待过程如何结束：

- 是否观察到变化。
- 观察到了哪些 signals。
- 是否超时。
- 是否跳过。
- 是否明确不需要等待。

后续 Task Result Reporter 可以在完整 replay 结束后读取所有 wait results 和
observation signals，用于生成 evidence-aware 的保守汇报。

Reporter 可以表达：

- 当前 action 后观察到 toast 出现。
- 当前 action 后观察到页面加载完成。
- 当前 action 后观察到列表变化。
- 当前 action 后未在等待窗口内观察到目标变化。

Reporter 不能仅凭某个 wait result 直接推断：

- 任务一定成功。
- 业务操作一定成功。
- 用户目标一定完成。
- timeout 后应该 retry。
- timeout 后应该 abort。

## Wait Strategy

Wait Strategy 是文档级实现方向，不是本轮已实现能力。

建议策略：

| 策略 | 用途 | 边界 |
|---|---|---|
| `short_stability_wait` | action 后短暂等待页面稳定。 | 不等于成功判断。 |
| `wait_for_signal` | 等待某类 observation signal。 | signal 命中不等于业务成功。 |
| `wait_for_page_load` | 等待 `page_load_finished`。 | page load 完成不等于业务成功。 |
| `wait_for_loading_to_finish` | 等待页面内 loading UI 结束。 | loading 结束不等于结果正确。 |
| `wait_for_text_or_element` | 等待文本或元素出现。 | 文本 / 元素出现仍需后续 evidence 解释。 |
| `wait_for_network_idle` | 等待网络相对稳定。 | 只能作为辅助信号，不能单独代表业务成功。 |

这些策略只定义后续实现方向。11.2.2 不实现 wait helper，不实现 page-load waiting，
不实现 network observer。

## Observation Signal 与 Wait Result 的关系

11.2.2 对齐
[`contract.md`](../11.2.1-observation-signal-contract/contract.md)。

- Observation Signal 描述“观察到了什么”。
- Wait Result 描述“等待过程如何结束”。
- signal 是 observed evidence。
- `timeout` / `skipped` / `not_required` 是 wait outcome。
- wait result 可以包含多个 observed signals。
- wait result 不能直接推断任务成功。

## Agent / Reporter Boundary

Wait-for-change MVP 不使用 Agent 判断业务是否成功。

wait 层只产出结构化等待结果和 observation signals：

- 页面发生了什么变化。
- 变化什么时候发生。
- 变化关联哪个 action / step。
- 等待结果是 `observed`、`timeout`、`skipped` 还是 `not_required`。

Agent 式解释留给后续 evidence-aware Task Result Reporter，也就是 11.2.5 的集成方向。

Reporter 可以在完整 replay 执行结束后消费 observation signals 和 wait results，
并生成保守的任务结果汇报。

11.2.2 不引入：

- 每一步 wait 后的 Agent 业务判断。
- Agent 驱动的 retry。
- Agent 驱动的 recovery。
- Agent 驱动的 abort。
- Agent 驱动的 user takeover。
- Agent 驱动的 next-step decision。

Wait 层负责“看见和记录”，Reporter 层负责“基于完整 evidence 做保守解释”。

## Page Understanding Agent 边界

11.2.2 不调用 Page Understanding Agent。

Page Understanding Agent 属于 L1 / M14 的页面学习语义理解角色；11.2.2 只处理
replay action 后短窗口 observation signals 和 wait results。

如果后续需要基于完整 replay evidence 做解释，应由 11.2.5 的 evidence-aware
Task Result Reporter 承接，而不是把 Page Understanding Agent 放进 wait loop。

## 与 Realistic Runtime Case Catalog 的关系

11.2.2 对齐
[`docs/testing/scenarios/realistic-web-runtime-cases.md`](../../../testing/scenarios/realistic-web-runtime-cases.md)。

MVP 优先服务这些场景：

- toast after submit。
- delayed button enabled。
- search result after network delay。
- loading skeleton then content。
- delayed full page reload after action。
- partial list refresh。
- SPA content update without URL change。
- validation error message。

这些场景不代表已经自动化、人工验证或被 E2E 覆盖。

下列场景偏 `passive_runtime`，不作为 11.2.2 MVP 的主要实现目标：

- server push message。
- WebSocket / SSE / polling update。
- passive DOM mutation。

## 保守汇报边界

Wait-for-change 结果只能支持保守表达：

- 当前 action 后观察到 toast 出现。
- 当前 action 后观察到页面加载完成。
- 当前 action 后观察到 loading UI 结束。
- 当前 action 后观察到列表发生变化。
- 当前 action 后未在等待窗口内观察到目标变化。

不能直接推断：

- 任务一定成功。
- 业务操作一定成功。
- 用户目标一定完成。
- timeout 后应该 retry。
- timeout 后应该 abort。
- 页面加载完成等于业务成功。
- toast 出现等于最终成功。
