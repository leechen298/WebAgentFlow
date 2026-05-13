# 11.1.6 · 通过 Replay 执行已确认计划

状态：**implementation complete, review passed**。

## 执行前必读

开发本包前，请按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/architecture.md`
6. `docs/iterations/m11/m11-plan.md`
7. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
8. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
9. `docs/iterations/m11/11.1.4-task-planning-dispatch-preview/review.md`
10. `docs/iterations/m11/11.1.5-plan-confirmation-consent-gate/review.md`
11. 本目录的 `intent.md`
12. 本目录的 `plan.md`

## 背景

11.1.4 已经把普通用户任务通过 conversation runtime 暴露为 planning
preview。11.1.5 将 pending preview 转成可审计的用户决策，并引入
`plan_confirmed` 这种“已确认但尚未执行”的语义。

11.1.6 是下一步设计包：通过已有 deterministic replay 能力执行一个已经确认
的 plan。它不重新规划、不学习新路径、不验证业务结果、不汇报最终任务成功，也不
做 failure recovery。

## 当前关系

- 前置：M11.0 conversation runtime foundation、11.1.4 Task Planning
  Dispatch Preview、11.1.5 Plan Confirmation and Consent Gate，以及现有
  M10 replay foundation / 11.0.6 explicit replay hook。
- 本包：设计 confirmed plan 如何通过 deterministic replay 执行。
- 后续：result verification、Task Result Reporter、recovery dialogue、
  teaching mode，以及更完整的 task-to-path evidence。

## 目标

- 定义执行 confirmed plan 的前置条件。
- 定义 execution 如何找到 confirmed plan / selected LearnedPath。
- 定义第一版 replay invocation boundary。
- 定义 execution started / completed / failed / blocked 的 conversation
  event 和 assistant message 语义。
- 保持 explicit `/replay <learned_path_id> <url>` 兼容。
- 将 result verification 和 Task Result Reporter 留在 11.1.6 之外。

## 非目标

- 本轮文档阶段不写实现代码。
- 不修改 11.1.1 schemas。
- 不修改 11.1.2 retrieval implementation。
- 不修改 11.1.3 planner implementation。
- 不修改 11.1.4 preview implementation。
- 不修改 11.1.5 confirmation implementation。
- 不新增 API endpoint 或 CLI command。
- 不调用 autonomous run。
- 不做 hidden relearning。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不实现真实 slot binding 或 form filling。
- 不实现 result verification。
- 不实现 Task Result Reporter。
- 不实现 recovery dialogue 或 teaching mode。
- 不做 browser exploration。
- 不创建 11.1.7 详情目录。

## 文档索引

- `intent.md` —— 为什么 confirmed plan 只能通过 deterministic replay 执行，
  以及为什么 replay completion 不等于业务成功。
- `plan.md` —— 11.1.6 后续实现计划与实现前决策收口。
- `review.md` —— 后续实现 review checklist。

## 后续开发前置条件

未来实现 11.1.6 前，必须确认：

- 工作分支已经具备 11.1.5 `plan_confirmed` 行为。
- 已 inspect 当前 replay service / explicit replay hook。
- 实现可以从可审计 conversation events 中找到 confirmed plan 和 selected
  LearnedPath。
- replay 所需上下文已经显式存在，包括 `learned_path_id` 和 target URL /
  entry context。
- missing context 的 blocked 行为已经在代码前确定。

## 验收摘要

- 核心路径是 `confirmed plan -> deterministic replay execution`。
- 11.1.6 不是 `ordinary task -> autonomous execution`。
- `replay completed` 不等于 `task verified` 或 `business success`。
- 缺 selected path、target URL 或 entry context 时必须 blocked。
- explicit `/replay <learned_path_id> <url>` 仍然是独立入口。
