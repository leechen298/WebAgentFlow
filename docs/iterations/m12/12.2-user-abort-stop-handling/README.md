# 12.2 · User Abort / Stop Handling

Status: documentation initialized.

## 目标

12.2 定义用户主动 abort / stop 后，WebAgentFlow 应如何收手。它处理的是
runtime user-abort signal，而不是 engine failure。

12.2 的核心问题是：

```text
当用户明确叫停时，系统如何立即停止或暂停继续操作，如何记录当时证据，
如何避免新的浏览器动作，并把后续选择交给后续 M12 包处理？
```

12.2 只定义边界，不实现 runtime stop / pause 代码。

## 和 12.0 / 12.1 的关系

12.0 建立 M12 的总边界：failure recovery / abort / runtime robustness 必须
可解释、可审计，不允许 hidden recovery、hidden relearning，也不能在未经用户
同意时继续操作浏览器。

12.1 已实现 deterministic recovery boundary classifier。它消费 M11.1
execution / Task Result Reporter evidence，输出 classification、reason、
evidence references 和 boundary recommendation。12.1 不处理 user abort。

12.2 接住独立的用户控制权信号：用户要求停止当前自动化继续操作。这个信号
不能被混入 failure classification，也不能直接触发 recovery proposal 或 retry。

## User Abort 定义

`user abort` 是用户明确要求 WebAgentFlow 停止当前自动化继续操作的信号。它
可以来自未来实现中的：

- slash command `/abort`；
- slash command `/stop`；
- 明确表达停止意图的用户消息；
- UI stop button；
- external scheduler cancellation。

本轮不新增 slash command、不改 parser、不改 CLI。这里仅定义未来实现需要识别
的意图边界。

## Stop Handling 定义

`stop handling` 是收到 abort / stop 后的边界处理：

- acknowledge 用户叫停；
- 禁止新的浏览器动作；
- 记录当前已知状态；
- 标记 in-flight action 的不确定性；
- 保留 evidence；
- 把后续选择交给 12.3 / 12.4 / 12.5，而不是自动恢复。

Stop handling 不是 retry、replan、takeover、teaching mode，也不是 recovery
proposal generator。

## Abort / Pause / Cancel / Takeover 区别

| Signal | 含义 | 12.2 边界 |
|---|---|---|
| `abort` / `stop` | 用户要求停止当前自动化继续操作，优先保护用户控制权。 | 12.2 的核心范围。 |
| `pause` | 临时暂停，可能保留恢复运行语义。 | 12.2 可说明边界，但不实现 pause / resume。 |
| `cancel` | 取消计划或确认流程，不一定已有执行中动作。 | 12.2 不重写 confirmation cancel 语义。 |
| `takeover` | 用户接管浏览器或流程，属于后续 handoff。 | 12.2 不实现 takeover。 |

这些信号不能混成一个状态。特别是，confirmation 阶段的 `cancel` 不等于执行期
的 `abort`；用户 takeover 也不等于系统继续自动恢复。

## Abort 与 Engine Failure 的区别

`failure` 表示系统运行或验证产生负面 evidence。`user abort` 表示用户收回控制权。

因此：

- abort 不能被静默转换成 `failure`；
- abort 不能被汇报成 `success`；
- abort 不能触发 hidden recovery；
- abort 不能触发 retry；
- abort 后的下一步必须等待新的用户选择或后续明确策略。

## Hard Rules After Abort

一旦 abort 被接受：

1. 不得继续发起新的浏览器动作。
2. 不得自动 retry。
3. 不得自动 replan。
4. 不得自动生成 recovery proposal。
5. 不得 hidden relearning 或 LearnedPath write-back。
6. 不得把 abort 结果说成 task success。
7. 必须记录可用 evidence 和 stop acknowledgement。

## In-flight Action Caveat

如果 abort 到达时已有浏览器动作正在执行，12.2 只能要求未来实现记录
best-effort stop boundary。系统不能承诺撤销已经发生的外部副作用。

需要记录：

- abort requested at；
- action already in flight；
- known execution / replay status；
- last execution event；
- side effects known / unknown；
- no new browser action after abort accepted。

## Idempotent Abort Handling

重复收到 abort / stop 必须是幂等的：

- 不触发新的浏览器动作；
- 不创建新的 recovery proposal；
- 不重新进入 retry / replan；
- 不重复写入含义不同的状态；
- 返回当前 abort boundary / stop acknowledgement 的稳定状态。

连续两次叫停只能加强“已经停止或正在停止”的事实，不能让系统继续做更多事情。

## Evidence Capture

12.2 要求未来实现保留 interruption time 的 evidence。建议字段包括：

- `abort_requested_at`；
- `source_status`；
- `active_command`；
- `active_plan_id`；
- `active_step_index`；
- `last_execution_event`；
- `known_replay_status`；
- `known_result_reporter_outcome`；
- `user_message`；
- `stop_acknowledged`；
- `no_new_browser_action`；
- `side_effects_unknown`。

这些字段是未来实现设计，不是本轮 schema。

## Stop Handling Decision

未来实现可使用这些 decision 值：

| Decision | 含义 |
|---|---|
| `accepted_stop` | abort 已接受，后续不得继续新浏览器动作。 |
| `already_finished` | abort 到达时任务已经结束，记录 late abort。 |
| `already_failed` | abort 到达时任务已经失败，保留 failure evidence 和 abort signal。 |
| `not_running` | 没有运行中自动化，返回稳定 acknowledgement。 |
| `cannot_interrupt_inflight_action` | 当前动作已发出，无法保证撤销，只能记录 best-effort boundary。 |
| `needs_manual_review` | 状态不清，需要人工查看 evidence。 |

## 与 12.3 / 12.4 / 12.5 的边界

- **12.3 Recovery proposal MVP**：可在 abort 后展示后续选择，但 proposal 不是
  12.2 的职责。
- **12.4 Retry / re-run policy**：定义 retry 是否允许、何时禁止、如何确认。
  12.2 不判断 safe retry。
- **12.5 Recovery conversation flow**：把 abort acknowledgement 和后续选择接入
  runtime conversation。12.2 不实现 conversation flow。

12.2 的输出应是 stop boundary 和 evidence requirement，而不是恢复动作。

## Non-goals

- recovery proposal generation；
- retry / re-run policy；
- retry execution；
- replan execution；
- conversation recovery flow；
- teaching mode；
- takeover implementation；
- LearnedPath write-back；
- M11.2 Runtime Observation / Wait-for-change；
- API endpoint；
- CLI command；
- database migration；
- frontend UI；
- E2E；
- `verify-scenario`。
