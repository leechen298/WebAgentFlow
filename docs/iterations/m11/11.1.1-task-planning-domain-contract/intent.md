# 11.1.1 Task Planning Domain Contract

## 目标

定义 M11.1 task-to-path planning 的 domain contract，为 retrieval、slot
binding、Task Path Planner / 任务路径规划器（legacy: Agent D）、confirmation、execution、verification、Task Result Reporter / 任务结果汇报器（legacy: Agent E） reporting
提供统一 schema。

## 动机

- 没有 domain contract，Task Path Planner / 任务路径规划器（legacy: Agent D） / execution / verification 会各自发明字段。
- M11.1 涉及多个阶段，必须先定义数据结构。
- 先做 schema / contract，避免马上接 LLM 或 replay side effect。

## 边界（本包不做）

- 不做 retrieval / ranking。
- 不做 Task Path Planner / 任务路径规划器和 Task Result Reporter / 任务结果汇报器（legacy: Agent D/E） 实现。
- 不做 slot binding。
- 不做 execution。
- 不做 result verification。
- 不做 risk gate。
- 不做 artifact lifecycle。
- 不调用 autonomous run。
- 不依赖 LLM provider。

## 成功标准

- 有 TaskInput / TaskIntent schema。
- 有 LearnedPathCandidate schema。
- 有 RoutePlan / RouteStep schema。
- 有 SlotBindingProposal schema。
- 有 ConfirmationRequirement schema。
- 有 RiskHint / ConsentRequirement schema。
- 有 PostconditionSignal schema。
- 有 TaskExecutionResult schema。
- 有 AgentDPlannerInput / AgentDPlannerOutput schema contract。
- 有 AgentEReporterInput / AgentEReporterOutput schema contract。
- Task Path Planner / 任务路径规划器和 Task Result Reporter / 任务结果汇报器（legacy: Agent D/E） 只定义 input / output contract，不实现 prompt、provider 或运行逻辑。
- 11.1.1 的 schema 类名可以保留 `AgentD` / `AgentE` 前缀以保持连续性；
  面向用户和后续文档时优先使用 Task Path Planner / Task Result Reporter。
- 有 ArtifactReference placeholder schema，但不实现 artifact lifecycle。
- 有 tests plan。
- 不加入 user / account / tenant 字段。
- 不调用 replay / autonomous / LLM。
