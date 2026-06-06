# 11.3.12.2 Bounded Learning Batch Lifecycle

状态：PACKAGE_COMPLETE
里程碑：M11
类型：mixed / code-gated child package
父包：`11.3.12-bounded-learning-composable-capability-assets`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包按代码型门禁处理。当前只生成七件套和设计评审材料；运行时代码实现必须等待
`review.md` 记录 `implementation_authorized: yes`。

## 目标

为 URL-only product learning 增加可审计、可界定、可关闭的 learning batch lifecycle：
后端学习批次不能只依赖 HTTP request 存活，也不能在 CLI timeout / cancel 后继续无界打开浏览器。

本包是 11.3.12.1 之后的第二个 child package。它可以消费 `LearnedCapability` 基础表 /
repo / schema，但不实现 Page Understanding hints 或 runtime capability composition。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - BoundedLearningPolicy、LearningBatch、cancel / timeout / detach 语义。
- `technical-design.md` - schema / model / repo / controller / service integration 设计。
- `test-plan.md` - unit / integration / chat runtime / static checks / live boundary。
- `plan.md` - 文档生成决策、允许文件、实施步骤、验证入口。
- `review.md` - 设计评审、实现授权、实际验证证据。

## /plan 风格文档生成入口

- [x] 目标 package path 和 package type 已确定。
- [x] parent / child 关系：父包 `11.3.12` campaign；当前 child `11.3.12.2`。
- [x] 必需文件集合：七件套。
- [x] source-of-truth 输入已阅读：parent `GOAL_RUNNER.md` / `CURRENT_STATE.md` /
  `contract.md` / `technical-design.md` / `test-plan.md` / `plan.md`，11.3.12.1 closeout，
  `docs/iterations/README.md`，`docs/iterations/AGENTS.md`，`docs/product-model.md`，
  existing `learning_run_service.py` / `chat_runtime.py` / learning tests。
- [x] contract / concept / status / evidence 变化已识别。
- [x] design-review gate 和 `test-plan.md` 触发状态已识别。
- [x] implementation authorization boundary 已写明。
- [x] stop conditions 和 handoff / checkpoint 已写明。

## 代码型门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 在实现收尾前记录验证证据。

## 当前状态

本包已完成 repo-local scoped implementation。下一步：不要扩展本包；后续能力提示与
runtime composition 必须进入 11.3.12.3 / 11.3.12.4。
