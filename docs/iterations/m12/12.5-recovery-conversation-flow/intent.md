# 12.5 Recovery Conversation Flow Intent

状态：proposed

## Goal

12.5 的目标是定义 recovery conversation flow：在 12.1 `RecoveryBoundary`、
12.2 `AbortAcknowledgement`、12.3 `RecoveryProposal`、12.4
`RetryPolicyDecision` 的基础上，生成用户可读、可审计、可选择的 conversation
response，并给现有 conversation runtime 一个安全的后续状态建议。

本次提交只交付设计包。后续实现提交将以本设计包为输入，设计并实现 pure
conversation-flow service、必要内部 schema、focused unit tests 和有限的
conversation integration tests。

## Motivation

M12.1-M12.4 已经提供了 deterministic recovery decision chain，但这些输出目前
仍是 service-level objects。用户需要看到的是 WebAgentFlow 以 conversation
方式解释发生了什么、哪些选项可选、哪些选项被 policy 拒绝、哪些信息还缺失。

如果 12.5 不独立定义 conversation boundary，后续 runtime flow 很容易把：

- proposal option 误读成执行命令；
- retry policy outcome 误读成 retry 已开始；
- user confirmation marker 误读成 browser continuation consent；
- abandon / takeover / re-teach handoff 误读成实际执行。

12.5 存在的理由是把“展示 / 解释 / 询问 / 记录”与“执行恢复动作”继续隔离。

## Boundary / Non-goals

12.5 做：

- recovery conversation flow semantics；
- conversation response boundary；
- conversation event boundary；
- user choice routing boundary；
- display of recovery proposal options；
- display of retry policy decisions；
- ask-user / review-evidence / abandon dialogue design；
- safe handoff to future retry / replan / takeover flows；
- conversation state transition design；
- future unit / integration test matrix。

12.5 不做：

- retry execution；
- re-run execution；
- replan execution；
- browser continuation；
- takeover implementation；
- teaching mode；
- LearnedPath write-back；
- M11.2 Runtime Observation / Wait-for-change；
- API endpoint expansion beyond existing conversation API；
- CLI behavior expansion unless explicitly scoped later；
- frontend UI；
- DB migration；
- autonomous exploration；
- hidden relearning；
- `verify-scenario`；
- E2E。

## Success Criteria

- 12.5 文档目录包含完整代码型迭代包：
  `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
  `test-plan.md`、`plan.md`、`review.md`。
- 文档明确 `Recovery conversation flow is not recovery execution`。
- 文档明确 conversation 可以展示 / 解释 / 询问 / 记录，但不能执行 retry、
  replan、browser continuation、takeover、teaching mode 或 LearnedPath write-back。
- `contract.md` 定义 recovery conversation concepts、decision/state、schema/API、
  evidence、compatibility 和不变契约。
- `technical-design.md` 设计 future pure service、existing conversation
  orchestrator/state integration boundary、data flow 和 edge cases。
- `test-plan.md` 覆盖 future unit / limited integration matrix，并明确 API / UI /
  E2E / live run 不在本次执行。
- `plan.md` 的验证表格引用 `technical-design.md` 和 `test-plan.md`。
- `review.md` 按实际运行结果记录 validation evidence 和未运行项。
