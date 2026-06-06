# 11.3.11.1 Terminal State Agent Contract Taxonomy

状态：REVIEW_READY
里程碑：M11.3 post-closeout
类型：mixed
父包：`11.3.11-terminal-state-agent-learning-stop-control`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包是 `11.3.11` campaign 的第一个 child package。它只负责把
`Terminal State Agent / 终态判断 Agent` 作为 M11.3.11 scoped L1 evaluator worker /
terminal evidence contract 的产品模型边界、terminal-state taxonomy、schema / storage
方向、redaction 规则和后续 child implementation gate 钉住。

本包不实现 runtime code，不改 API，不改数据库，不运行 live autonomous validation。

## 依赖关系

必须先阅读父包：

- `../11.3.11-terminal-state-agent-learning-stop-control/README.md`
- `../11.3.11-terminal-state-agent-learning-stop-control/contract.md`
- `../11.3.11-terminal-state-agent-learning-stop-control/plan.md`
- `../11.3.11-terminal-state-agent-learning-stop-control/GOAL_RUNNER.md`
- `../11.3.11-terminal-state-agent-learning-stop-control/CURRENT_STATE.md`

Child 2-6 必须等待本包 `review.md` 给出设计复核结论，并确认没有 P0 / P1 blocker。

## 文档集

- `README.md` - 包索引、状态、父子关系和门禁。
- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - Agent 边界、终态类型、状态、证据强度和兼容性契约。
- `technical-design.md` - product-model / roadmap 文档更新、schema/storage 方案和后续 child 设计边界。
- `test-plan.md` - 文档完整性、产品模型对齐和非 live 复核计划。
- `plan.md` - 实施步骤、stop conditions、验证入口和 handoff。
- `review.md` - 设计复核、实际差异、验证证据和下一步 route。

## 当前状态

本包文档已生成并进入 design review。`docs/product-model.md` 和 `docs/roadmap.md`
允许发生 scoped documentation update，用于承认 terminal-state classification 是 L1 attempt
trial 和 Attempt Evaluation 之间的 evidence contract；如果使用 Terminal State Agent 命名，
它必须是 `no legacy alias`，不是 Agent I，也不是替代 Attempt Evaluation Agent 的顶层角色。

Runtime implementation 仍未授权；下一步只能在 review 通过后进入
`11.3.11.2-browser-event-recorder` 的 child package 文档/实现门禁。
