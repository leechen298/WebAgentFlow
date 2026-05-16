# 12.4 · Retry / Re-run Policy

状态：implemented
里程碑：M12
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

12.4 是代码型迭代。已实现 retry / re-run policy schema、deterministic
policy evaluator 和 focused unit tests。实现仍保持 policy-only 边界：不执行
retry，不继续浏览器，不接 conversation flow。

## 当前状态

- 12.1 Failure Classification and Recovery Boundary 已实现并交付。
- 12.2 User Abort / Stop Handling 已实现并交付。
- 12.3 Recovery Proposal MVP 已实现并交付。
- 12.4 Retry / Re-run Policy 已实现并完成 focused unit validation。

12.4 实现和后续维护应继续遵守：

- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - retry policy 概念、状态、schema、evidence、兼容性和不变契约。
- `technical-design.md` - implemented schema / service / data flow / compatibility 设计。
- `test-plan.md` - unit matrix、实际验证证据和未运行的 API / UI / E2E / live run 边界。
- `plan.md` - 实施步骤、验证命令和实现记录。
- `review.md` - 设计包生成、实现验证证据、未运行项和 follow-ups。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design / test plan 一致。
- [x] `review.md` 已记录最终验证证据。

当前实现已完成并通过 focused recovery suite；未运行 API / CLI / E2E /
`verify-scenario` / autonomous run，因为 12.4 不新增这些 surfaces。

## 核心原则

```text
Retry policy is not retry execution.
Retry allowed is not retry started.
Retry requires explicit user confirmation through later flow.
Retry must be denied when side effects are unknown or unsafe.
Retry must not duplicate irreversible external actions.
```

12.4 只产出 retry / re-run policy decision，不执行 retry，不继续浏览器，不接
conversation flow，也不把 12.3 proposal option 直接变成 command。

## 和 12.1 / 12.2 / 12.3 的关系

- 12.1 输出 `RecoveryBoundary`：classification、recommendation、reason 和
  evidence references。
- 12.2 输出 `AbortAcknowledgement`：stop decision、abort evidence、
  `no_new_actions_after` 和 `inflight_caveat`。
- 12.3 输出 `RecoveryProposal`：display-only proposal options，所有 option
  `non_executable=true`，没有 selected option。
- 12.4 消费这些结构化输出，判断 retry 是否可以进入后续确认链路，是否必须拒绝，
  或是否需要更多上下文 / 人工 review。

12.4 不改变 12.1 / 12.2 / 12.3 的输出，不执行 12.3 option，也不在本轮接入
12.5 conversation flow。

## Live Run 边界

本次设计和实现不触发 live run、`verify-scenario`、autonomous run、UI smoke 或
E2E。若未来需要 live run，必须按仓库根 `AGENTS.md` 记录 `pass_gate.status`、
Supervisor verdict、scorecard 和 `run_id`。
