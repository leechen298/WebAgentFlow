# 12.4 Retry / Re-run Policy Intent

状态：implemented

## Goal

12.4 的目标是定义 retry / re-run policy：在 12.1 `RecoveryBoundary`、
12.2 `AbortAcknowledgement`、12.3 `RecoveryProposal` 的基础上，判断 retry
何时可以进入后续用户确认链路，何时必须拒绝，何时需要更多上下文或人工 review。

12.4 已基于本设计包实现 policy schema、deterministic evaluator 和 focused unit
tests。实现只返回 policy decision，不执行 retry。

## Motivation

12.3 已经能生成 display-only recovery proposal，其中 `consider_retry_later`
只是“未来可考虑 retry”的菜单项，不是 retry policy，也不是 retry command。

如果没有独立 retry policy，后续 conversation flow 很容易把“可考虑 retry”误读为
“可以 retry”，从而重复提交表单、重复点击支付 / 确认按钮、覆盖目标页面状态，或在
side effects unknown 时继续操作浏览器。

12.4 存在的理由是：

- 把 retry proposal 和 retry execution 继续隔离；
- 对 side effects、idempotency、evidence、用户确认和 unsupported state 做明确判断；
- 让 `retry_denied` 成为有效安全结果，而不是新的 failure；
- 给 12.5 conversation flow 一个确定性的 policy input，而不是让对话层临时推断。

## Boundary / Non-goals

12.4 做：

- retry / re-run policy semantics；
- retry policy decision model；
- retry evidence requirements；
- side-effect risk classification；
- idempotency boundary；
- policy confirmation requirements；
- policy denial reasons；
- policy handoff to 12.5 conversation flow；
- deterministic policy evaluator implementation；
- focused unit test matrix。

12.4 不做：

- retry execution；
- re-run execution；
- browser continuation；
- conversation recovery flow；
- API endpoint；
- CLI command；
- frontend UI；
- DB / migration；
- M11.2 Runtime Observation / Wait-for-change；
- teaching mode；
- takeover implementation；
- LearnedPath write-back；
- autonomous exploration；
- hidden relearning；
- `verify-scenario`；
- E2E。

## Success Criteria

- 12.4 文档目录包含完整代码型迭代包：
  `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
  `test-plan.md`、`plan.md`、`review.md`。
- 文档明确 `Retry policy is not retry execution`。
- 文档明确 `retry_allowed_requires_confirmation != retry started`。
- 文档明确 retry 必须检查 side effects、idempotency、policy evidence 和
  user confirmation。
- 实现明确 unknown / unsafe side effects、non-idempotent action、irreversible
  action possible、unsupported replay state、abort boundary active 等情况必须
  deny 或进入 review/context。
- `contract.md` 定义 retry policy concepts、outcomes、reasons、evidence 和
  compatibility。
- `technical-design.md` 记录 implemented schema / evaluator / data flow。
- `test-plan.md` 覆盖 unit matrix，并明确 API / UI / E2E / live run 不在本次执行。
- `plan.md` 的验证表格引用 `technical-design.md` 和 `test-plan.md`。
- `review.md` 按实际运行结果记录 validation evidence 和未运行项。
