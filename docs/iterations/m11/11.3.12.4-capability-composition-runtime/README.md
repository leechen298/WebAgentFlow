# 11.3.12.4 Capability Composition Runtime

状态：PACKAGE_COMPLETE
里程碑：M11
类型：mixed / code-gated child package
父包：`11.3.12-bounded-learning-composable-capability-assets`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包按代码型门禁处理。七件套已通过 read-only design review，scoped implementation 已完成，
`review.md` 已记录测试、ruff、hardcoding scan 和 code-review evidence。

## 目标

在已有 LearnedPath 不可用或不够匹配时，让 L3 runtime 可以在代码规则下组合多个
`LearnedCapability` 原子能力，形成可审计的 `CapabilityCompositionPlan`。组合计划只有在真实执行并
通过 evidence gate 后，才可晋升为完整 LearnedPath。

本包承接 11.3.12.1 LearnedCapability、11.3.12.2 LearningBatch / bounded policy、11.3.12.3
Page Understanding capability hints；不实现 LLM step-by-step browser execution，不新增内部 Agent 角色。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - composition plan、candidate compatibility、execution gate、promotion 语义。
- `technical-design.md` - schema / composer service / repository lookup / promotion guard 设计。
- `test-plan.md` - unit / service / regression / static checks / live boundary。
- `plan.md` - 允许文件、实施步骤、验证入口、停机条件。
- `review.md` - 设计评审、实现授权、实际验证证据。

## 代码型门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 在实现收尾前记录验证证据。

## 当前状态

本包处于 `PACKAGE_COMPLETE`。已新增 deterministic composition schemas、`CapabilityComposer`、
private execution handoff、promotion guard 和 focused regression tests。本包未运行也不授权 live
validation、`verify-scenario`、Console UI 或 public API。
