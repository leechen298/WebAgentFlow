# 11.3.5.9 · TaskPathPlanner Multi-candidate Chat Integration

状态：ready_for_implementation（design review passed，未开始实现）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：

- [`11.3.5.6-wagent-chat-items-closed-loop-evaluation`](../11.3.5.6-wagent-chat-items-closed-loop-evaluation/)
- [`11.3.5.7-pending-choice-active-task-ledger`](../11.3.5.7-pending-choice-active-task-ledger/)
- [`11.3.5.8-basic-failure-recovery`](../11.3.5.8-basic-failure-recovery/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包是 11.3.5.x working runtime 的 P2 planning integration 包。它把已经存在的
deterministic `TaskPathPlanner` 接入 `wagent chat` 的多候选 / 模糊目标路径，并复用
11.3.5.7 的 `pending_choice` 私有映射完成用户确认。

## 迭代定位

11.3.5.3 - 11.3.5.6 已跑通 `/items` P0 working loop。11.3.5.7 提供
`pending_choice` / `active_task`，11.3.5.8 提供基础失败恢复。11.3.5.9 只处理
“有多个可能执行路径或用户目标模糊时，如何让 Runtime 基于 ranked session candidates
展示选择，并利用 Planner 对 top candidate 给出 route plan / warning / uncertainty 信号”。

实现前必须 preflight 确认 11.3.5.7 和 11.3.5.8 的实现能力与 targeted tests 仍然通过；
如果 pending choice、private map、active task、recovery choice、retry / relearn / cancel
或 private payload safety 不可用，本包不得进入实现。

关键边界：

```text
单个 learned action 且目标明确
  -> 不进 TaskPathPlanner
  -> 直接 replay

多个 learned actions 或目标模糊
  -> Runtime 生成 ranked session candidates
  -> TaskPathPlanner 评估 top candidate / ambiguity / risk
  -> Runtime 合并 ranked candidates + planner signals
  -> Runtime 写 pending_choice + private map
  -> 用户选择 A/B/C
  -> Runtime 内部解析 learned_path_id 并执行
```

## 本包做什么

- 在 `wagent chat` 多候选 / 模糊目标路径中调用 `TaskPathPlanner`。
- 把当前 session 的 learned actions 转成 planner 可消费的 `LearnedPathCandidate`。
- 把 Intake / raw input / target hint 转成 `TaskIntent`。
- Runtime 基于 ranked session candidates 生成用户可见 A/B/C choice。
- 把 Planner 对 top candidate 的 `route_plan`、warnings、risk hints、uncertainty
  作为 sanitized description / confirmation hint 融入 choice。
- 把真实 `learned_path_id`、slot overrides 和 route-plan metadata 放进 private map。
- 用户选择 choice 后，继续复用 11.3.5.7 的选择解析和 `_execute_matched_action()`。
- 记录 sanitized planning progress event，便于 review，但不泄露 private path id。

## 本包不做

- 不改变 `/items` 单路径 happy path。
- 不让所有 execute_operation 都经过 TaskPathPlanner。
- 不使用 `PlanningPreviewService` 的原始用户文案，因为它会显示 selected path id。
- 不让 Router 输出 `learned_path_id`、selector、browser action 或 planner private payload。
- 不新增正式 risk / consent gate。
- 不接复杂组合任务的多步执行。
- 不做 learn_then_execute。
- 不做 Failure Recovery 扩展；失败后的 A/B/C 仍归 11.3.5.8。
- 不调用 `verify-scenario` 或 autonomous run。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - planner chat 接入、candidate adapter、choice payload 和安全边界。
- `technical-design.md` - runtime 接入点、planner adapter、pending choice 转换和事件设计。
- `test-plan.md` - 多候选 / 模糊目标 / 单路径回归 / 安全测试矩阵。
- `plan.md` - 实施步骤、验证命令和复核清单。
- `review.md` - 设计评审入口和后续实现证据记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。

## 当前状态

文档已生成，等待设计评审。评审通过后才能进入代码实现阶段。
