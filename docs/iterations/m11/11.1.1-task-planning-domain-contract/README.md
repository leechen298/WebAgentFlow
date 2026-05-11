# 11.1.1 · Task Planning Domain Contract

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/iterations/m11/m11-plan.md`
5. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
6. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
7. 本目录的 `intent.md`
8. 本目录的 `plan.md`

状态：**当前规划中**。

## 当前关系

- 前置：M11.0 runtime loop。
- 本包：定义 task-to-path 领域语言和 schema。
- 后续：11.1.2 retrieval / ranking。

## 硬边界

- 不做 retrieval。
- 不做 slot binding implementation。
- 不做 Agent D implementation。
- 不做 Agent E implementation。
- 不做 replay execution。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 E2E。

## 目标

定义 M11.1 task-to-path planning 的 domain contract，为 retrieval、slot
binding、Agent D、confirmation、execution、verification、Agent E reporting
提供统一 schema。

## 非目标

- 不做 retrieval / ranking。
- 不做 Agent D / E 实现。
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
- 有 tests plan。
- 不加入 user / account / tenant 字段。
- 不调用 replay / autonomous / LLM。
