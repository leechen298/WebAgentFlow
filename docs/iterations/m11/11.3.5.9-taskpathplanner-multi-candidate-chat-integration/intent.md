# 意图（Intent）

状态：ready_for_implementation（design review passed，未开始实现）

## 目标

为 `wagent chat` 接入 TaskPathPlanner 的多候选 planning path：当用户目标模糊或当前
session 中有多个 learned actions 可能匹配时，Runtime 应使用 deterministic
`TaskPathPlanner` 评估 top candidate 的 route plan、risk、warning 和 ambiguity 信号；
A/B/C 候选列表仍由 Runtime 基于 ranked session candidates 生成，再通过 `pending_choice`
让用户选择。

成功状态：

```text
用户：帮我处理一下这个页面
  |
  v
Runtime 识别多个候选 learned actions
  |
  v
Runtime 生成 ranked session candidates
  |
  v
TaskPathPlanner 评估 top candidate / 风险 / 不确定性
  |
  v
Runtime 合并 ranked candidates + planner signals，写 pending_choice（只暴露 A/B/C）
  |
  v
用户选择 A
  |
  v
Runtime 用 private map 解析真实 learned_path_id
  |
  v
执行 selected learned action
```

## 动机

11.3.5.7 已经有 `pending_choice`，但当前多候选展示主要是 runtime 直接把 matching
actions 转成 A/B/C。这样能安全阻断乱猜，但还没有利用已经实现的 L3 deterministic
`TaskPathPlanner`：

- Planner 能消费 ranked `LearnedPathCandidate`。
- Planner 能为 top candidate 生成单一 `RoutePlan`、confirmation requirement、
  risk hint 和 uncertainty。
- Planner 不返回 `ranked_candidates` 或 `alternative_routes`；多候选列表由 Runtime
  基于 session learned actions 生成。
- Planner 已有 task-planning tests 和 preview service，但还没有接入 `wagent chat`
  的 customer-facing choice mode。

11.3.5.9 的目标不是扩大 Agent 图，而是把 Planner 放到它该出现的位置：

```text
多候选 / 模糊目标 / planning preview path
```

而不是：

```text
单路径明确执行 happy path
```

## 为什么现在做

P0 working loop 已经证明系统可以学习一个操作、按新参数执行、采集 evidence 并保守报告。
11.3.5.7 / 11.3.5.8 又补了 choice 和基础失败恢复。实现前必须确认这些前置能力
在当前代码中可用，并且相关 targeted tests 通过。确认后，接 Planner 有真实地基：

- choice mode 可以安全展示候选。
- private map 可以隐藏真实 path id。
- active_task 可以表示等待用户选择。
- single-path `/items` happy path 可以作为回归保护。

## 本包不做

- 不改 `/items` 单路径直接 replay 逻辑。
- 不接 Planner 到所有 execution 分支。
- 不做多步组合 workflow。
- 不新增正式 consent gate。
- 不让 `PlanningPreviewService` 的 raw user_response 进入 `wagent chat`，因为当前 preview 文案会显示 selected path id。
- 不改变 TaskResultReporter / ExecutionEvidence / Failure Recovery 语义。
- 不运行 live `wagent chat`、`verify-scenario` 或 autonomous run。

## 成功标准

- 多个 learned actions 且无法确定唯一执行动作时，Runtime 调用 TaskPathPlanner。
- Runtime 基于 ranked session candidates 生成 sanitized `pending_choice`。
- Planner output 只作为 top candidate 的 route plan / warning / uncertainty 信号，
  不被当作多候选列表来源。
- visible payload / WAgent reply / progress event 不含 `learned_path_id`。
- private map 内部保存真实 path id 和 slot overrides。
- 用户选择 A / 1 / 第一个后，Runtime 执行对应 path。
- 单个明确 learned action 仍直接 replay，不调用 TaskPathPlanner。
- `/items` P0 happy path 回归不受影响。
