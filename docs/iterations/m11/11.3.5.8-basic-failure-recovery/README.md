# 11.3.5.8 · Basic Failure Recovery

状态：draft_docs（待评审，未开始实现）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：

- [`11.3.5.5-execution-evidence-result-reporter-adapter`](../11.3.5.5-execution-evidence-result-reporter-adapter/)
- [`11.3.5.6-wagent-chat-items-closed-loop-evaluation`](../11.3.5.6-wagent-chat-items-closed-loop-evaluation/)
- [`11.3.5.7-pending-choice-active-task-ledger`](../11.3.5.7-pending-choice-active-task-ledger/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包是 11.3.5.x working runtime 的 P2 runtime robustness 包。它不新增
happy path 能力，而是在 replay 失败、页面不匹配、证据不足时给用户一个安全出口：

```text
A. 重试执行该操作
B. 重新学习
C. 取消
```

## 迭代定位

11.3.5.3 - 11.3.5.6 已跑通 `/items` P0 working loop：

```text
学习新增项目 A
-> 参数化执行新增项目 B
-> DOM evidence verified
-> TaskResultReporter verified
```

11.3.5.8 依赖 11.3.5.7 的 `pending_choice`、private map、最小 `active_task`
和 cancel cleanup 实现能力。实现前必须先确认这些能力已在当前代码中可用，并且
相关 targeted tests 通过。11.3.5.8 在这个状态底座上补基础失败恢复：失败时不编造成果，
不让 LLM 自己探索修复，而是由 Runtime 根据 replay / reporter / evidence 状态给出
可选择的恢复动作。

## 本包做什么

- replay failed / runtime error 时，保守报告失败并展示恢复选项。
- evidence missing / reporter `needs_review` / `uncertain` 时，不说成功，展示恢复选项。
- URL mismatch / drift / blocked 时，阻断继续执行并展示恢复选项。
- 复用 11.3.5.7 的 `pending_choice` 机制展示 A/B/C。
- private map 内部保存 retry / relearn / cancel 所需的最小安全 payload。
- 用户选择 A 时，Runtime 按原 learned action、target URL、slot overrides 再次执行一次。
- evidence missing / uncertain / needs_review 下的重试可能重复已经发生过的副作用，
  用户可见文案必须提示“重试会再次执行该操作”。
- 用户选择 B 时，Runtime 进入重新学习分支，不自动 learn_then_execute。
- 用户选择 C 或说“算了”时，清理 pending recovery / pending choice / active task。
- 记录可审计 recovery events，例如 offered / selected / retry started / relearn started。

## 本包不做

- 不做复杂自治恢复。
- 不做 LLM 自主探索。
- 不做 selector healing。
- 不做多步修复计划。
- 不接 TaskPathPlanner，多候选 planning 属于 11.3.5.9。
- 不启用 `learn_then_execute`。
- 不新增 `/items` 搜索 / 编辑 / 删除闭环。
- 不新增 DB migration。
- 不调用 `verify-scenario` 或 autonomous run。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - failure classification、recovery choice、retry / relearn / cancel 契约。
- `technical-design.md` - runtime recovery handler、pending choice 复用、event 和状态流转设计。
- `test-plan.md` - replay failure、evidence missing、blocked、retry / relearn / cancel 测试矩阵。
- `plan.md` - 实施步骤、验证命令和复核清单。
- `review.md` - 设计评审入口和后续实现证据记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。

## 当前状态

文档已生成，等待设计评审。评审通过后才能进入代码实现阶段。
