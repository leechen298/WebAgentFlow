# Replay Integration with Observation Contract

状态：文档级 contract proposal，能力未实现

本文档定义 11.2.3 的 replay-level observation evidence aggregation contract。它不
创建代码 schema，不修改 API，不修改 replay execution，也不接入 Task Result
Reporter。

## 定义

Replay Observation Evidence 是从 replay steps 的 `wait_result` / observation
signals 聚合出来的 replay-level evidence summary。

它用于回答：

- 整个 replay 执行过程中观察到了哪些变化？
- 哪些 step 有 `observed` wait result？
- 哪些 step 是 `timeout`、`skipped` 或 `not_required`？
- 是否出现 primary observation signal？
- 是否只有 supporting signal？
- 是否存在 uncertainty flags？
- 这些 evidence 能否给后续 Task Result Reporter 消费？

它不是：

- 业务成功判断。
- Task Result Reporter。
- recovery plan。
- retry decision。
- abort decision。
- user takeover。
- Page Understanding Agent。
- Page Context Bridge。
- 完整组件库 runtime semantics。

## Replay Observation Summary

Replay Observation Summary 是文档级 proposal，不是已实现 schema。

建议字段：

| 字段 | 含义 | 边界 |
|---|---|---|
| `observation_summary_id` | summary 唯一标识。 | 11.2.3 不规定格式。 |
| `replay_id` | 关联 replay execution。 | 可为空；不改变现有 replay contract。 |
| `learned_path_id` | 关联 LearnedPath。 | 仅用于追溯路径资产。 |
| `status` | replay observation status。 | 不是 `ReplayResult.status`，也不是业务状态。 |
| `step_count` | replay step 总数。 | 用于统计，不代表完成质量。 |
| `wait_result_count` | 带 `wait_result` 的 step 数。 | 少于 step_count 时仍保持向后兼容。 |
| `observed_step_count` | `wait_result.status=observed` 的 step 数。 | observed 不等于任务成功。 |
| `timeout_step_count` | `wait_result.status=timeout` 的 step 数。 | timeout 不等于应该 retry。 |
| `skipped_step_count` | `wait_result.status=skipped` 的 step 数。 | skipped 可能是 action policy。 |
| `not_required_step_count` | `wait_result.status=not_required` 的 step 数。 | 常见于 observe 或无需等待的 step。 |
| `primary_signal_kinds` | 聚合出的 primary signal kind。 | 当前 11.2.2 MVP 主要是 `url_changed` / `title_changed`。 |
| `supporting_signal_kinds` | 聚合出的 supporting signal kind。 | `network_idle_observed` 只能作为 supporting evidence。 |
| `has_primary_observation` | 是否有 primary observation。 | 不等于任务成功。 |
| `has_timeout` | 是否有 step timeout。 | 不等于应该 retry。 |
| `has_only_supporting_observation` | 是否只有 supporting signal。 | 只在没有 primary signal、但存在 supporting signal 时为 true，例如只观察到 `network_idle_observed`。后续 reporter 必须保守消费。 |
| `has_uncertain_observation` | 是否存在不确定观察状态。 | 只表示 evidence 不足或混合，不触发 M12 决策。 |
| `observation_notes` | 简短摘要备注。 | 不写 raw HTML，不写 LLM reasoning。 |
| `step_observation_refs` | step / wait result 引用。 | 只引用 step index、wait_id、signal_id 和最小 signal kind，不复制完整 step log、截图、raw HTML、DOM dump 或 reporter 文案。 |

Replay Observation Summary 不保存 raw HTML，不保存完整 DOM dump，不保存 LLM
chain-of-thought，不保存业务成功结论。

`has_only_supporting_observation` 只在没有 primary signal、但存在 supporting signal
时为 true，例如只观察到 `network_idle_observed`。如果同时存在 `url_changed` 或
`title_changed` 等 primary signal，该字段必须为 false。

`step_observation_refs` 只引用 step index、wait_id、signal_id 和最小 signal kind。
它不复制完整 step log、截图、raw HTML、DOM dump 或 reporter 文案。

## Replay Observation Status

建议 `status` 收敛为：

```text
observed
no_primary_observation
partial_observation
not_applicable
```

语义：

- `observed`：至少一个 step 有 primary observation signal，例如 `url_changed` /
  `title_changed`。
- `no_primary_observation`：没有 primary signal，可能只有 timeout / skipped /
  supporting signals。
- `partial_observation`：部分 step observed，部分 step timeout / skipped，适合后续
  reporter 保守表达。
- `not_applicable`：没有可观察 steps，例如 observational path `actions=[]` 或全部
  step 不需要 wait。

这些是 observation summary status，不是 replay status，也不是业务成功 status。
11.2.3 不修改现有 `ReplayResult.status` 语义。

### Status derivation priority

Replay observation status 应保守推导：

1. `not_applicable`：没有 replay action steps，或者所有 wait results 都是
   `not_required`。
2. `partial_observation`：至少一个 step 有 primary observation signal，同时其他
   step 存在 `timeout`、`skipped` 或 uncertainty。
3. `observed`：至少一个 step 有 primary observation signal，且没有 timeout /
   skipped / uncertainty materially weaken 这组 observation。
4. `no_primary_observation`：不存在 primary observation signal。只存在
   `network_idle_observed` 等 supporting signals 时也属于这一类。

这些 status 只描述 observation evidence，不修改 `ReplayResult.status`，也不暗示
业务成功。

## 与 WaitResult 的关系

11.2.3 对齐：

- [`../11.2.2-wait-for-change-mvp/contract.md`](../11.2.2-wait-for-change-mvp/contract.md)
- [`../11.2.2-wait-for-change-mvp/plan.md`](../11.2.2-wait-for-change-mvp/plan.md)

关系：

- ObservationSignal 是 observed evidence atom。
- WaitResult 是 step-level outcome。
- Replay Observation Evidence 是 replay-level aggregation。

示例：

```text
Step 0 wait_result.status = observed
Step 0 primary_signal = url_changed
Step 1 wait_result.status = skipped

Replay observation summary:
  status = partial_observation
  has_primary_observation = true
  observed_step_count = 1
  skipped_step_count = 1
  primary_signal_kinds = ["url_changed"]
```

纯 `observed` 示例：

```text
Step 0 wait_result.status = observed
Step 0 primary_signal = url_changed

Replay observation summary:
  status = observed
  has_primary_observation = true
  observed_step_count = 1
  skipped_step_count = 0
  timeout_step_count = 0
  primary_signal_kinds = ["url_changed"]
```

如果 replay 只观察到 `network_idle_observed`：

```text
Step 0 wait_result.status = timeout
Step 0 observed_signals = [network_idle_observed]
Step 0 primary_signal = None

Replay observation summary:
  status = no_primary_observation
  has_primary_observation = false
  supporting_signal_kinds = ["network_idle_observed"]
  has_only_supporting_observation = true
```

`network_idle_observed` 不能单独让 replay-level summary 变成业务相关成功。

## 与 Task Result Reporter 的关系

11.2.3 不接 Task Result Reporter。

11.2.3 只是为 11.2.5 准备输入：

```text
11.2.3 produces replay-level observation evidence.
11.2.5 lets Task Result Reporter consume it.
```

Reporter 未来可以表达：

- replay 执行过程中观察到 URL 变化。
- replay 执行过程中观察到 title 变化。
- replay 执行过程中有 step timeout。
- replay 执行过程中只观察到 network idle supporting signal。
- 当前 evidence 不足以确认业务成功。

Reporter 不能仅凭 11.2.3 evidence 推断：

- 任务一定成功。
- 业务一定完成。
- timeout 后应该 retry。
- timeout 后应该 abort。
- 系统已经恢复。

## 与 Common Component Runtime Semantics 的关系

Common Component Runtime Semantics 是 later 11.2.x 增强方向。11.2.3 不实现完整
组件库 runtime behavior detection。

11.2.3 可以为未来保留 notes 或 uncertainty flags，但不能实现：

- popup / panel relation resolver。
- mobile picker relation。
- component class based runtime semantics。
- Ant Design Select option panel relation。
- Vant / NutUI / Ionic runtime surface detection。

组件库 class 未来也只能作为 supporting evidence，不能成为业务成功判断。

## 与 M12 的边界

11.2.3 不做：

- recovery。
- retry。
- abort。
- user takeover。
- failure dialogue。

如果 replay observation summary 发现 timeout、no primary observation 或 only supporting
observation，11.2.3 只能记录 evidence / uncertainty，不能做决策。

## 保守解释边界

Replay Observation Evidence 可以支持保守表达：

- replay 期间至少一个 step 观察到 URL 变化。
- replay 期间至少一个 step 观察到 title 变化。
- replay 期间某些 step timeout。
- replay 期间某些 step skipped 或 not_required。
- replay 期间只有 supporting signal，当前 evidence 不足。

Replay Observation Evidence 不能直接推断：

- replay 成功等于任务成功。
- observed 等于业务成功。
- URL/title 变化等于用户目标完成。
- timeout 等于应该 retry。
- no primary observation 等于应该 abort。
