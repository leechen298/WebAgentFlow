# 11.1.2 LearnedPath Retrieval and Ranking

## 目标

为 M11.1 task-to-path planning 建立第一版 LearnedPath retrieval and
deterministic ranking 能力：输入 `TaskIntent` 和可选 page / scenario hints，
从 LearnedPath catalog 中返回可解释、可排序、可审计的
`LearnedPathCandidate` 列表，为后续 slot binding 和 Task Path Planner
提供候选集合。

## 动机

- 11.1.1 已定义 `TaskIntent` / `LearnedPathCandidate` schema。
- M11.1 不能直接让 Task Path Planner 在全量 LearnedPath catalog 上自由搜索。
- 需要先有一个 deterministic retrieval / ranking 层，把候选路径缩小到
  可解释集合。
- Retrieval / ranking 是代码侧服务，不是 LLM Agent。
- 这一层不执行 replay，不做 slot binding，不生成 route plan。
- 这一层必须保留可解释的 `match_reasons` / `warnings`，供后续 Task Path
  Planner 和用户确认使用。

## 边界（本轮不做）

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
- 不做 Agent routing。
- 不做 API endpoint，除非后续 plan 明确需要；本轮文档不实现。
- 不做 E2E。
- 不加入 user / account / tenant 字段。

## 成功标准

- 有 retrieval service contract。
- 输入使用 11.1.1 `TaskIntent`。
- 输出使用 11.1.1 `LearnedPathCandidate`。
- 有 deterministic ranking score 规划。
- 有 `match_reasons` / `warnings` 规划。
- deprecated LearnedPath 不作为正常候选，第一版默认排除。
- confirmed path 排名优先于 provisional / flaky。
- hit_count 可以作为正向信号，但不能压过 trust / deprecated。
- 不调用 LLM。
- 不调用 replay。
- 不调用 autonomous run。
- 有测试计划。
