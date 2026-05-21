# 11.3.5.5 · ExecutionEvidence & TaskResultReporter Adapter

状态：draft_docs（设计草案，未开始实现）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：[`11.3.5.4-parameterized-learning-replay-slots`](../11.3.5.4-parameterized-learning-replay-slots/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代定位

11.3.5.5 是 working runtime P0 闭环的第三个子包。11.3.5.3 提供 `/items`
页面基座；11.3.5.4 打通 `item_name -> value_slot -> slot_overrides ->
effective_action`，让“学习 A 后执行 B”真正填入 B。

本包只解决执行后的页面证据和保守汇报：

```text
ReplayRequest.evidence_targets
-> run_replay() action 执行完成
-> runtime.stop() 前采集 DOM evidence
-> ReplayResult.execution_evidence
-> ConversationReplaySummary.execution_evidence
-> Reporter Adapter
-> TaskResultReporter._check_postconditions()
-> verified / uncertain / needs_review / failed / blocked
-> 用户可见保守回复
```

关键目标是让 `TaskResultReporter` 在 replay succeeded 且 `/items` 列表中确认看到
执行阶段的新项目名时输出 `verified`。不能只把 `ExecutionEvidence` 塞进 event payload
而让 Reporter 继续输出 `uncertain`。

## 本包不做

- 不新增 `/items` 页面。
- 不修改 `item_name` slot / `value_slot` / `slot_overrides` 参数化机制，除非为了传递 evidence target。
- 不接 TaskPathPlanner。
- 不做 `pending_choice`。
- 不做 `active_task` / RuntimeLedger。
- 不做 Failure Recovery 菜单。
- 不做搜索 / 编辑 / 删除闭环。
- 不运行 `verify-scenario` 或 autonomous run。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - `ExecutionEvidenceTarget`、`ExecutionEvidence`、Reporter adapter 和 outcome 契约。
- `technical-design.md` - replay evidence capture、conversation summary、reporter verified path 的实现设计。
- `test-plan.md` - schema、capture、reporter、chat runtime adapter 的 targeted tests。
- `plan.md` - 实施步骤、验证命令和交付清单。
- `review.md` - 文档阶段评审入口和后续 implementation review 记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。
- [ ] 实现阶段已开始。
- [ ] Evidence / Reporter 验证证据已记录到 `review.md`。

## 当前状态

文档包已生成，等待设计评审。实现必须先确认：

- P0 evidence 只要求 `dom_text_present` 和 `unknown`。
- `/items` 新增项目的 evidence target 必须优先限定在 `[data-testid='item-list']`。
- `ExecutionEvidence.target` 必须来自 `ExecutionEvidenceTarget.text`。
- DOM evidence 必须在 Playwright runtime stop 前采集。
- `TaskResultReporter` 原生 outcome 仍是 `verified / failed / uncertain / needs_review / blocked`。
- Reporter verified path 必须真的读取 structured postcondition evidence。

## 开发入口

实现前先读：

```text
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
```

实现完成后，把实际变更、命令输出、pass / fail 结果和未运行项写入 `review.md`。
