# 11.3.12.1 LearnedCapability Asset Foundation

状态：PACKAGE_COMPLETE
里程碑：M11
类型：mixed
父包：`../11.3.12-bounded-learning-composable-capability-assets/`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 目标

实现 11.3.12 的第一块可独立验证基础：新增持久化 `LearnedCapability` 资产层，
让后续 bounded learning 和 runtime composition 可以引用原子能力证据。本包只做资产基础，
不改变 LearnedPath schema、API、学习批次、chat timeout、bounded planner、
Page Understanding hints 或 replay 执行选择。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - LearnedCapability asset foundation 的字段、信任、证据、兼容性契约。
- `technical-design.md` - model / migration / repo / schema 设计。
- `test-plan.md` - exact commands 和 required verification。
- `plan.md` - 实施步骤和 stop conditions。
- `review.md` - 设计审查、实现授权、实际验证证据。

## /plan 风格文档生成入口

- [x] 目标 package path 和 package type 已确定。
- [x] parent / child 关系：父包 11.3.12；本包是第一个 child package。
- [x] 必需文件集合：七件套。
- [x] source-of-truth 输入已阅读：父包 contract / technical-design / plan / review、
  `docs/iterations/AGENTS.md`、M11 README、LearnedPath model / repo / migration / schemas。
- [x] contract / concept / status / evidence 变化已识别。
- [x] design-review gate 和 `test-plan.md` 触发状态已识别。
- [x] implementation authorization boundary 已写明。
- [x] umbrella / campaign package 判断：由父包提供 `GOAL_RUNNER.md` / `CURRENT_STATE.md`。
- [x] stop conditions 和 handoff / checkpoint 已写明。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录当前状态。

## 当前状态

本包已完成 repo-local implementation closeout。`LearnedCapability` asset foundation
已落地并通过 targeted repo/schema tests、LearnedPath compatibility tests、scoped ruff
和 offline Alembic SQL generation。online DB migration 仍因本地环境未验证；live validation、
`verify-scenario` 和 `wagent chat` 未运行。
