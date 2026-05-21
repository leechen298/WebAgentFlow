# 11.3.5.6 · WAgent Chat `/items` Closed-loop Evaluation

状态：implementation complete（closed-loop pass，result recorded）
里程碑：M11
类型：mixed
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置迭代：
[`11.3.5.3-product-test-site-items-fixture`](../11.3.5.3-product-test-site-items-fixture/),
[`11.3.5.4-parameterized-learning-replay-slots`](../11.3.5.4-parameterized-learning-replay-slots/),
[`11.3.5.5-execution-evidence-result-reporter-adapter`](../11.3.5.5-execution-evidence-result-reporter-adapter/)

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [x] 混合型迭代

混合型迭代按代码型迭代门禁处理。本包的主要交付不是新增产品能力，而是对
11.3.5.3 - 11.3.5.5 已实现能力做一次可审计的 `wagent chat` 闭环验证，并沉淀
结果证据。如果执行过程中发现阻断性小缺口，只允许做最小修复；大功能缺口必须记录为
后续迭代，不得在本包扩大范围。

## 迭代定位

11.3.5.6 是 working runtime P0 闭环的收口验证包。前序包分别完成：

```text
11.3.5.3: /items product-test-site 页面基座
11.3.5.4: item_name -> value_slot -> slot_overrides -> effective_action
11.3.5.5: evidence_targets -> execution_evidence -> TaskResultReporter verified path
```

本包要证明这些能力在真实 `wagent chat` 产品入口里连成一条窄闭环：

```text
用户只给 /items URL
-> 用户说“学习新增项目，名称叫测试项目A-${timestamp}”
-> 系统学习新增项目并绑定 item_name
-> 用户说“帮我新增项目，名称叫测试项目B-${timestamp}”
-> replay 实际填入 B，不复读 A
-> [data-testid='item-list'] 中出现 B
-> TaskResultReporter 输出 verified
-> review.md / docs/testing/results 记录可复查证据
```

## 本包不做

- 不新增 `/items` 功能，不做搜索 / 编辑 / 删除。
- 不新增 `item_name` / `value_slot` / `slot_overrides` 机制。
- 不新增 `ExecutionEvidence` / Reporter adapter 机制。
- 不接 TaskPathPlanner。
- 不做 `pending_choice`。
- 不做 `active_task` / RuntimeLedger。
- 不做 Failure Recovery 菜单。
- 不启用 `learn_then_execute` 自动组合。
- 不调用 `verify-scenario`。
- 不调用 autonomous run。
- 不把 Codex / AI 当作 WebAgentFlow 内部 Agent。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - 闭环验证、证据记录、pass / fail / unverified 契约。
- `technical-design.md` - 执行拓扑、取证点、结果文件与 review 写回设计。
- `test-plan.md` - `wagent chat` 闭环测试矩阵、命令和未运行边界。
- `plan.md` - 执行步骤、验证命令和复核清单。
- `review.md` - 设计评审入口和后续闭环执行结果记录。

## 混合型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在执行前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 在收尾前记录验证证据。
- [x] `docs/testing/results/m11-11.3.5.6-items-closed-loop-<YYYY-MM-DD>.md`
  已记录可复查结果。
- [x] 实际闭环已执行，或明确记录 blocked / unverified 原因。

## 当前状态

闭环已执行并通过。结果文件：
[`docs/testing/results/m11-11.3.5.6-items-closed-loop-2026-05-21.md`](../../../testing/results/m11-11.3.5.6-items-closed-loop-2026-05-21.md)。

执行结果证明当前工作区已经包含 11.3.5.3 - 11.3.5.5 的实现结果：

- `apps/product-test-site` `/items` 可打开并能新增项目。
- `ReplayAction.value_slot` 和 `ReplayRequest.slot_overrides` 已实现。
- `run_replay()` 使用 `effective_action` 并在 step log 中保留参数化证据。
- `ExecutionEvidenceTarget` / `ExecutionEvidence` 已实现。
- `/items` evidence target 使用 `[data-testid='item-list']`。
- `TaskResultReporter` 能基于 structured postcondition evidence 输出 `verified`。

复核入口：

```text
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```
