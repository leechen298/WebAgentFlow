# 审核与反思

## 规划初始化

- 本目录用于 11.1.1 Task Planning Domain Contract。
- 当前状态：intent / plan / code / tests 已完成。
- 本包是 M11.1 的第一个执行包，用于定义 task-to-path 领域 contract。

## 实现记录

- `apps/api/app/schemas/task_planning.py` — 17 个 schema / contract 定义。
  - TaskInput, TaskIntent
  - LearnedPathCandidate
  - RoutePlan, RouteStep
  - SlotBindingProposal
  - ConfirmationRequirement, RiskHint, ConsentRequirement
  - PostconditionSignal
  - TaskExecutionResult
  - ArtifactReference (placeholder)
  - AgentDPlannerInput / Output, AgentEReporterInput / Output
- `apps/api/tests/test_task_planning_schemas.py` — 24 tests passed。
  - minimal valid data acceptance (16 tests)
  - enum / literal validation (3 tests)
  - structural assertions (2 tests)
  - contract rules (3 tests)
- ruff check clean。

## 已决策

- `TaskIntent.normalized_goal` 在 11.1.1 中定义为 optional field。本包不实现
  deterministic normalizer，也不实现 Task Path Planner / 任务路径规划器（legacy: Agent D）；后续 11.1.4 Task Path Planner / 任务路径规划器（legacy: Agent D） 可以填充或
  改写 `normalized_goal`。schema 必须保留 `raw_text` 作为不可丢失的原始输入，
  并可定义 `normalization_source` optional field，取值规划为
  `none | deterministic | agent_d`。
- `RiskHint` 和 `ConsentRequirement` 保持为两个 schema，不合并。`RiskHint`
  表示系统识别到的风险信号；`ConsentRequirement` 表示执行前必须向用户请求
  确认的门槛。一个 `ConsentRequirement` 可以引用一个或多个 `RiskHint`，但
  11.1.1 只定义字段，不实现 policy engine。初期 risk / consent policy 属于
  11.1.5。
- `TaskExecutionResult.status` 第一版只使用
  `succeeded | failed | uncertain | needs_review`。失败来源通过
  `failure_stage: planning | confirmation | replay | verification | artifact | unknown`
  和 `failure_reason` 表达，不把 replay failure / verification failure 拆成
  status enum。Task Result Reporter / 任务结果汇报器（legacy: Agent E） 后续必须基于 status、failure_stage 和 evidence 汇报，
  不得脑补成功。
- 11.1.1 定义 Task Path Planner / 任务路径规划器和 Task Result Reporter /
  任务结果汇报器的 input / output contract（legacy: Agent D/E），但不定义 prompt，
  不实现 LLM 调用。`AgentDPlannerInput` / `AgentDPlannerOutput` 至少承载
  `TaskIntent`、`LearnedPathCandidate`、`SlotBindingProposal`、`RoutePlan`、
  `ConfirmationRequirement`。`AgentEReporterInput` / `AgentEReporterOutput`
  至少承载 `TaskExecutionResult`、verification signals、artifact
  placeholders、warnings 和 user-facing summary。
- 11.1.1 的 schema 类名可以保留 `AgentD` / `AgentE` 前缀以保持连续性；
  面向用户和后续文档时优先使用 Task Path Planner / Task Result Reporter。
- artifact fields 在 11.1.1 只定义 placeholder / reference shape，不实现
  capture、storage、retention、download、display。`TaskExecutionResult` 可以包含
  `artifacts: list[ArtifactReference]`；`ArtifactReference` 只保留 minimal fields：
  `kind`、`label`、`uri optional`、`status`、`metadata`。

## 待确认问题

- 11.1.2 retrieval ranking 是否需要 first deterministic scoring formula。
- 11.1.4 Task Path Planner / 任务路径规划器（legacy: Agent D） prompt 是否需要独立 prompt doc。
- 11.1.7 Task Result Reporter / 任务结果汇报器（legacy: Agent E） 是否需要和 artifact lifecycle 分离。
