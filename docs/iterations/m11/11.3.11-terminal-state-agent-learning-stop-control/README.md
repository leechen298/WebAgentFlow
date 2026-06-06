# 11.3.11 Terminal State Agent Learning Stop Control

状态：PACKAGE_COMPLETE
里程碑：M11.3 post-closeout
类型：umbrella / campaign

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代
- [x] Umbrella / campaign planning package

本包只定义 M11.3 post-closeout 的 `Terminal State Agent / 终态判断 Agent` 学习停止控制路线、
契约和子包边界，不直接授权 runtime implementation。运行时代码必须从子包七件套开始，
并在对应子包 `review.md` 中记录 `implementation_authorized: yes` 后才能开发。

## 迭代文档

- `README.md` - 父包索引、状态和 child route。
- `intent.md` - 总目标、动机、边界和成功标准。
- `contract.md` - 终态证据、停止控制、Agent 边界和 live-run 边界。
- `test-plan.md` - 父包级测试策略、child test matrix 和 live-run 门禁。
- `plan.md` - planned child packages 的 execution-grade quasi-package spec。
- `review.md` - 父包文档复核、授权状态和后续 route。
- `GOAL_RUNNER.md` - Codex App `/goal` campaign 路由契约。
- `CURRENT_STATE.md` - 当前 active child 和 package queue。

## 背景

`/users` 筛选页暴露的问题不是单个按钮没点对，而是 L1 autonomous exploration 无法可靠判断
“尝试一个操作后何时算结束”。登录 / 创建表单常有跳转或明显提交结果；筛选页、刷新、
导出、弹窗、toast、静默请求则可能没有强视觉变化，导致探索要么过早结束，要么把一个
控制按钮误沉淀成学习路径。

本包把“终态判断”作为 M11.3 URL-only learning 修复路线：Page Understanding Agent 给出页面用途、
页面内容、可能功能和候选终态，浏览器事件记录器补充可审计证据，Terminal State Agent
在探索循环中判断是否已经到达终态以及是否应 stop / wait / continue / unverified，Attempt
Evaluation Agent 再对 attempt 是否可沉淀作评价。

该能力会为未来 M14 Learning Quality / Coverage / Negative Knowledge 提供基础，但当前执行和
文档路由属于 M11.3 post-closeout。

## 子包路线

| Package | Type | Status | Route |
|---|---|---|---|
| `11.3.11.1-terminal-state-agent-contract-taxonomy` | mixed | PACKAGE_COMPLETE | docs/product-model/roadmap alignment |
| `11.3.11.2-browser-event-recorder` | code / mixed | PACKAGE_COMPLETE | redacted attempt-phase browser event timeline |
| `11.3.11.3-page-understanding-terminal-hints` | code / mixed | PACKAGE_COMPLETE | deterministic PageAnalysis terminal hints |
| `11.3.11.4-terminal-state-agent-stop-control` | code / mixed | PACKAGE_COMPLETE | post-action advisory terminal verdict metadata |
| `11.3.11.5-attempt-evaluation-ingest-gate` | code / mixed | PACKAGE_COMPLETE | deterministic ingest gate for LearningRunService and Workbench |
| `11.3.11.6-evidence-console-and-regression-suite` | code / mixed / validation | PACKAGE_COMPLETE | Console evidence summary and non-live regressions |

## 当前状态

当前父包规划文档已完成，child 1
`11.3.11.1-terminal-state-agent-contract-taxonomy` 已完成 docs/product-model/roadmap alignment
closeout，child 2 `11.3.11.2-browser-event-recorder` 已完成 non-live implementation closeout，
child 3 `11.3.11.3-page-understanding-terminal-hints` 已完成 deterministic hints closeout，
child 4 `11.3.11.4-terminal-state-agent-stop-control` 已完成 advisory terminal-state classifier
closeout，child 5 `11.3.11.5-attempt-evaluation-ingest-gate` 已完成 deterministic ingest gate
closeout，child 6 `11.3.11.6-evidence-console-and-regression-suite` 已完成 Console evidence summary
和非 live regressions。父包 campaign closeout 完成。
本轮没有实现真正 in-loop stop controller；`stop_decision=wait/continue/stop` 是 attempt 完成后的
advisory metadata，用于后续入库 gate 和 operator evidence。真正改变探索循环 timing / early stop 的
controller 需要后续单独设计包。没有 live autonomous validation 授权。
