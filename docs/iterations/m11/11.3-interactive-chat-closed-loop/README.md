# 11.3 Interactive Chat Closed Loop

状态：accepted（implementation review passed, manual smoke passed）
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - interactive chat、学习意图、session learned actions、自动执行边界。
- `technical-design.md` - CLI / API / service / orchestrator 实现设计。
- `test-plan.md` - unit / integration / CLI / manual smoke 验证方案。
- `plan.md` - 分步实施和验证命令。
- `review.md` - 实际实现、验证证据和未运行项记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在。
- [x] `plan.md` 与已审核的 contract / technical design 一致。
- [x] `review.md` 在收尾前记录验证证据。

## 当前状态

M11.0 / M11.1 已经提供 conversation API、non-interactive
`wagent conversation`、Task-to-Path planning preview、confirmation gate、
execution via replay 和 result reporter。当前缺口是普通用户不能只通过一个持续
聊天入口完成“学习页面 -> 沉淀 LearnedPath -> 再用自然语言执行”的闭环。

本包新增 `wagent chat` 作为人工自测主入口。第一阶段只验证 fixture-site
`/entry` happy path，不扩大到 `/records`、真实业务页、M12 recovery / retry /
takeover 或复杂 LLM 意图理解。

当前代码实现和 scoped regression 已通过审查；M11.3 已通过真实
`wagent chat` 人工闭环 smoke。该 smoke 使用当前工作区 API 临时端口 `8002`
执行，因为当时本机 `8001` 被旧 API 进程占用。

## 后续归属

后续 “working runtime” 收口不另开 11.4，统一挂在 11.3.5.x：

- `fixture-site /records` 测试页。
- 参数化 learning / replay，覆盖 `record_name`、`value_slot` 和 `slot_overrides`。
- ExecutionEvidence 与 TaskResultReporter adapter，要求 runtime stop 前采集页面证据。
- `wagent chat` `/records` 闭环测试结果记录。
- `pending_choice`、最小 `active_task`、基础失败恢复和 TaskPathPlanner 多候选 chat 接入。

这些能力属于 11.3 Interactive Chat 的产品化后续，但具体施工、设计和验收锚点放在
11.3.5 Customer-Facing Agent Router & Skill Runtime 下。完整施工稿见
[`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)。
