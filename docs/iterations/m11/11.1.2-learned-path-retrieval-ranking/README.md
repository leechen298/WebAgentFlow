# 11.1.2 · LearnedPath Retrieval and Ranking

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/iterations/m11/m11-plan.md`
5. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
6. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
7. `docs/iterations/m11/11.1.1-task-planning-domain-contract/review.md`
8. 本目录的 `intent.md`
9. 本目录的 `plan.md`

状态：**当前规划中**。

## 当前关系

- 前置：11.1.1 Task Planning Domain Contract。
- 本包：从 LearnedPath catalog 中检索和排序候选路径。
- 后续：11.1.3 Slot Binding。
- 本包只输出候选路径，不生成 route plan。

## 硬边界

- 不调用 Task Path Planner。
- 不调用 LLM provider。
- 不做 slot binding。
- 不生成 RoutePlan。
- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不做 hidden relearning。
- 不创建 11.1.3 详情目录。

## 目标

为 M11.1 task-to-path planning 建立第一版 LearnedPath retrieval and
deterministic ranking 能力：输入 `TaskIntent` 和可选 page / scenario hints，
从 LearnedPath catalog 中返回可解释、可排序、可审计的
`LearnedPathCandidate` 列表，为后续 slot binding 和 Task Path Planner
提供候选集合。

## 非目标

- 不实现 Task Path Planner。
- 不实现 Task Result Reporter。
- 不调用 LLM provider。
- 不做 slot binding。
- 不生成 RoutePlan。
- 不做 confirmation gate。
- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不做 hidden relearning。
- 不做 API endpoint。
- 不做 E2E。
- 不加入 user / account / tenant 字段。

## 成功标准

- 有 retrieval service contract。
- 输入使用 11.1.1 `TaskIntent`。
- 输出使用 11.1.1 `LearnedPathCandidate`。
- 有 deterministic ranking score 规划。
- 有 match_reasons / warnings 规划。
- deprecated LearnedPath 默认不作为正常候选。
- confirmed path 排名优先于 provisional / flaky。
- hit_count 可以作为正向信号，但不能压过 trust / deprecated。
- 不调用 LLM。
- 不调用 replay。
- 不调用 autonomous run。
- 有测试计划。
