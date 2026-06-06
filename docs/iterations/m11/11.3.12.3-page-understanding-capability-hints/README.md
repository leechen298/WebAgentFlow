# 11.3.12.3 Page Understanding Capability Hints

状态：PACKAGE_COMPLETE
里程碑：M11
类型：mixed / code-gated child package
父包：`11.3.12-bounded-learning-composable-capability-assets`

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

本包按代码型门禁处理。七件套已通过 read-only design re-review，scoped implementation 已完成，
`review.md` 已记录测试、ruff、hardcoding scan 和 code-review evidence。

## 目标

把 PageAnalysis / Page Understanding 的输出扩展为 target-agnostic capability hints，让后续 L1
bounded learning 能更准确识别页面区域、控件角色、terminal target、sample value source 和依赖关系。

本包承接 11.3.12.2 的 `LearningBatch` / bounded policy，不实现 capability composition runtime。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - CapabilityHintSet、region / control / dependency / terminal hint 语义。
- `technical-design.md` - schema / analyzer / service integration / compatibility 设计。
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

本包处于 `PACKAGE_COMPLETE`。已新增 redacted `CapabilityHintSet`、PageAnalyzer hint 输出、
hint-aware capability discovery、schema-level redacted-ref validation 和 focused regression tests。
本包未运行也不授权 live validation、`verify-scenario` 或 runtime composition。
