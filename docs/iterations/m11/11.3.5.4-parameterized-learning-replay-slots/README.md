# 11.3.5.4 · Parameterized Learning / Replay Slots

状态：ready_for_implementation（design review passed，未开始实现）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：[`11.3.5.3-fixture-site-items-fixture`](../11.3.5.3-fixture-site-items-fixture/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代定位

11.3.5.4 是 working runtime P0 闭环的第二个子包。11.3.5.3 已提供
`apps/fixture-site` 的 `/records` 页面基座，本包补齐“学习新增项目 A 后，
执行新增项目 B 时必须真的填入 B”的参数化 learning / replay 链路。

本包只解决参数传播和 replay 替换：

```text
Intake record_name
-> Runtime fill_values.record_name
-> LearnedPath fill action value_slot=record_name
-> execute branch slot_overrides.record_name
-> ReplayRequest / run_replay
-> effective_action value=测试项目B
-> step log 证明填入 B 而不是 A
```

本包不接 ExecutionEvidence，不接 TaskResultReporter，不做 DOM evidence，也不做
`pending_choice`、`active_task`、Failure Recovery 或 TaskPathPlanner chat 接入。
这些分别属于 11.3.5.5 之后的包。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - `record_name`、`value_slot`、`slot_overrides`、日志和阻断契约。
- `technical-design.md` - intake、runtime、learning、replay、hook 传播链实现设计。
- `test-plan.md` - 文档检查、unit / integration 验证和非运行项。
- `plan.md` - 实施步骤、验证命令和交付清单。
- `review.md` - 文档阶段评审入口和后续 implementation review 记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。
- [ ] 实现阶段已开始。
- [ ] 参数化 replay 验证证据已记录到 `review.md`。

## 当前状态

文档包已通过设计评审，当前可以进入实现阶段。实现必须先确认：

- `record_name` 是本包唯一 P0 canonical business slot。
- `value_slot` 写入 LearnedPath actions JSON，不新增 DB column。
- `slot_overrides` 必须从 chat runtime 传播到 replay service / `run_replay()`。
- `execute_action()` 和 `wait_for_change_after_action()` 都必须使用 `effective_action`。
- step log / debug trace 必须能证明 replay 实际填入的是执行阶段的新值 B。

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
