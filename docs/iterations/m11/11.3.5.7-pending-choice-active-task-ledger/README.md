# 11.3.5.7 · Pending Choice & Minimal Active Task Ledger

状态：implementation complete（code review passed，targeted tests passed）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：[`11.3.5.6-wagent-chat-records-closed-loop-evaluation`](../11.3.5.6-wagent-chat-records-closed-loop-evaluation/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包是 11.3.5.x working runtime 的 P1 runtime robustness 包。它建立
`pending_choice` 和最小 `active_task` ledger，让 `wagent chat` 在模糊输入、
多候选、用户选择、取消和任务状态记录上有 code-owned 状态边界。

## 迭代定位

11.3.5.3 - 11.3.5.6 已经证明 `/records` P0 working loop 可以从 `wagent chat`
跑通：

```text
/records
-> 学习新增项目 A
-> value_slot=record_name
-> 执行新增项目 B
-> DOM evidence verified
-> TaskResultReporter verified
```

11.3.5.7 不再扩展 P0 happy path。它解决 P0 之后的第一个交互问题：
当用户输入太模糊、候选动作不止一个，或者用户需要在 A/B/C 中选择时，
Runtime 必须写入 `pending_choice`，下一轮由代码解析 choice，并保证真实
`learned_path_id` 不进入用户可见回复、Router prompt 或 LLM trace。

同时，本包加入最小 `active_task` metadata，让 learning / execution / clarify
在开始、等待用户、完成、失败、取消时有统一状态记录，但不做完整 RuntimeLedger
重构。

## 本包做什么

- 新增 `pending_choice` metadata contract。
- 新增 `pending_choice_private_map` 或等价私有映射。
- 支持用户输入 `A` / `1` / `第一个` 选择 pending choice。
- 支持用户输入 choice label 的简单 deterministic matching。
- 支持用户说“不是，我要...”时清理旧 choice 并重新进入 intake。
- 支持 `pending_choice.turns_remaining` 过期清理。
- 扩展 Entry Gate / Context Collector / Runtime，使存在 `pending_choice` 时进入
  heavy runtime。
- 增加最小 `active_task` metadata contract。
- 学习 / 执行 / clarify 开始时写 `active_task`，完成 / 失败 / 取消时清理或标记。
- 统一 `/cancel` 和中文取消对 `pending_intake`、`pending_target`、`pending_choice`、
  `active_task` 的清理。

## 本包不做

- 不接 TaskPathPlanner 多候选 chat 路径；Planner 接入属于 11.3.5.9。
- 不做复杂 Failure Recovery；重试 / 重新学习 / 取消菜单属于 11.3.5.8。
- 不启用 `learn_then_execute`。
- 不新增 `/records` 搜索 / 编辑 / 删除页面功能。
- 不让 Router 输出 `learned_path_id`、selector、Playwright action 或内部 adapter。
- 不让 LLM 直接解析真实 path id 或调用 internal runtime adapter。
- 不改变 TaskResultReporter outcome。
- 不调用 `verify-scenario` 或 autonomous run。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - `pending_choice`、私有映射、`active_task`、cancel / expiry 契约。
- `technical-design.md` - runtime metadata、choice handler、ledger update 和清理设计。
- `test-plan.md` - pending choice / active task / cancel / redaction 测试矩阵。
- `plan.md` - 实施步骤、验证命令和复核清单。
- `review.md` - 设计评审入口和后续实现证据记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 在收尾前记录验证证据。

## 当前状态

实现已完成并通过 targeted tests。最终收口证据见：

```text
review.md
```
