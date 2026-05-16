# 12.5 · Recovery Conversation Flow

状态：approved for implementation
里程碑：M12
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

12.5 是代码型迭代。实现提交会把 M12.1-M12.4 的纯 recovery service
outputs 包装进 runtime conversation flow，让用户看到清晰、可审计、可选择的
recovery conversation。设计包已完成 review，可按 `webagentflow-iteration-dev`
执行实现；实现 Agent 应只读本迭代文档，不在实现过程中改写迭代文档。

## 当前状态

- 12.1 Failure Classification and Recovery Boundary 已实现并交付。
- 12.2 User Abort / Stop Handling 已实现并交付。
- 12.3 Recovery Proposal MVP 已实现并交付。
- 12.4 Retry / Re-run Policy 已实现并交付。
- 12.5 design package 已完成 review，当前可进入 implementation。

12.5 实现和维护应遵守：

- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - conversation response、choice、event、state 和 evidence 契约。
- `technical-design.md` - schema / service / conversation integration boundary 设计。
- `test-plan.md` - required unit / conditional limited integration matrix 和未运行边界。
- `plan.md` - 实施步骤和验证命令。
- `review.md` - 本次设计包生成记录、实际验证证据、未运行项和 follow-ups。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] `technical-design.md` 已完成 implementation gate review。
- [x] `technical-design.md` 包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design / test plan 一致。
- [x] `review.md` 已记录本次设计包验证证据。

当前可开工。代码实现应以本设计包为输入，按 `technical-design.md` 窄范围实现，
按 `test-plan.md` 和 `plan.md` 自测，并在最终回复中报告真实验证证据、未运行项和风险。
实现 Agent 不应在实现过程中改写 `review.md` 或其他迭代文档。

## 核心原则

```text
Recovery conversation flow is not recovery execution.
Conversation may present, explain, ask, route, and record choices.
Conversation must not execute retry, replan, browser continuation, takeover,
teaching mode, or LearnedPath write-back.
```

12.5 可以把恢复菜单端到用户面前，但不能替用户点菜。Conversation 可以展示
proposal options、retry policy result 和 evidence explanation；它不能自动选择
option，也不能把 user confirmation marker 直接消费成 browser action。

## 和 12.1 / 12.2 / 12.3 / 12.4 的关系

- 12.1 输出 `RecoveryBoundary`：classification、recommendation、reason 和 evidence。
- 12.2 输出 `AbortAcknowledgement`：stop decision、abort evidence、
  `no_new_actions_after` 和 `inflight_caveat`。
- 12.3 输出 `RecoveryProposal`：display-only proposal options，所有 option
  `non_executable=true`。
- 12.4 输出 `RetryPolicyDecision`：retry policy outcome，不是 retry command。
- 12.5 消费并包装这些输出，生成 user-facing conversation response、event payload
  和 next-state suggestion。

12.5 不改变 12.1-12.4 输出，不执行 12.3 option，不启动 12.4 retry，也不新增
browser continuation。

## Live Run 边界

12.5 MVP 不触发 live run、`verify-scenario`、autonomous run、UI smoke 或
E2E。若后续明确要求 live run，必须按仓库根 `AGENTS.md` 记录 `pass_gate.status`、
Supervisor verdict、scorecard 和 `run_id`。
