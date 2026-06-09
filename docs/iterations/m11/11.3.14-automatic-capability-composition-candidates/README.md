# 11.3.14 Automatic Capability Composition Candidates

状态：REPO_LOCAL_NON_LIVE_IMPLEMENTATION_READY_FOR_REVIEW
里程碑：M11
类型：mixed / code-gated

## 目标

补齐 WebAgentFlow 现有 `CapabilityComposer` 之后缺失的产品链路：由已学习的
`LearnedCapability` 原子能力自动生成有限组合候选，执行候选，按证据门禁决定是否晋升为
`LearnedPath`，并导出可供外部 Validation Site 评估的
`waf.learning_evidence_bundle.v1`。

本包不把“生成候选”直接等同于“学会路径”。组合候选只有在真实执行并通过 pass / terminal /
ingest gate 后，才可以晋升为成功 `LearnedPath`。

## 背景

11.3.12.4 已实现底层 `CapabilityComposer`：

- 给定 `required_capability_kinds` 和候选 `LearnedCapability` 时，可构造
  `CapabilityCompositionPlan`。
- 可优先选择已有 high-confidence `LearnedPath`。
- 可返回 private execution handoff。
- 可根据 execution evidence 返回 promotion metadata。

但它仍缺少产品级自动化闭环：

- 不会从页面/用户任务/Validation Site evidence 需求自动生成组合候选集合。
- 不会对一个页面的能力图做 bounded pair / chain coverage。
- 不会自动执行候选并记录 pass/fail/negative evidence。
- 不会把通过候选晋升写入 `LearnedPath`。
- 不会导出 provider 可评估的 redacted learning evidence bundle。

## 文档

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`

## 当前边界

- 本包已完成 review repair 的 repo-local non-live implementation，实际验证见
  `review.md`。
- 不得作为 `PACKAGE_COMPLETE` 合入；仍需二次 code review、live validation /
  `wagent chat` 产品路径验证，以及 live Postgres migration 验证。
- 不运行 live validation。
- 不调用 direct autonomous-run endpoint。
- 不把 Validation Site oracle、路径、字段、选择器、seed copy 写入 WebAgentFlow runtime 或 prompt。

## 与 Validation Site 的关系

Validation Site 可以维护 provider-private oracle 和组合覆盖率指标。WebAgentFlow 只负责导出
观测到的 capability / path / composition evidence bundle，并消费 Validation Site 的 redacted
evaluation result。Validation Site 不应直接读取 WebAgentFlow DB 或内部 runtime payload。
