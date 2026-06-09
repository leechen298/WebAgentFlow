# Contract

状态：proposed

## Concepts

### CapabilityGraph

一个页面范围内可组合的 `LearnedCapability` 集合及其关系投影。它由 WebAgentFlow 运行时从
已持久化能力、PageAnalysis hints、terminal target、control/region scope 和 trust 状态构建。

它不得包含 Validation Site 私有 oracle 答案。

### CompositionCandidate

由代码生成的候选组合。它不是 `LearnedPath`，也不是成功证据。

Required public fields:

- `candidate_id`
- `target_url` / page signature scope
- `candidate_family`
- `source_capability_ids`
- `ordered_capability_kinds`
- `expected_terminal_target`
- `risk_level`
- `confidence`
- `generation_reason`
- `status`

Allowed statuses:

- `generated`
- `rejected_static`
- `ready_for_execution`
- `executing`
- `execution_passed`
- `execution_failed`
- `execution_unverified`
- `promoted_to_learned_path`
- `negative_evidence_recorded`

### CompositionCandidateFamily

Provider 和 WebAgentFlow 都可以用 redacted family 名称表达组合类型。示例：

- `filters_then_submit`
- `filters_then_export`
- `filter_then_open_detail`
- `reset_after_filters`
- `create_record`
- `edit_record`

具体页面字段、选择器、seed value 属于 provider-private oracle，不进入 WebAgentFlow runtime。

### CompositionCoverageMetric

用于评估候选生成是否充分的覆盖率指标。它和成功率不同。

示例：

- `required_family_coverage`
- `critical_capability_participation`
- `candidate_reasonable_rate`
- `execution_attempt_coverage`
- `promotion_reliability`
- `negative_evidence_capture_rate`

## Generation Contract

候选生成必须 bounded：

- 先按 candidate family 生成。
- 每个 family 有 max candidate count。
- 默认只生成 single submit chain、pairwise dependency chain 和 small smoke chain。
- 使用 Page Understanding / capability hints / deterministic dependency rules 限制组合。
- 不做指数级全排列。
- 不重复生成同一 source capability set 的候选。

## Static Rejection Contract

以下候选必须在执行前拒绝：

- 跨 page signature；
- query signature / DOM fingerprint 不兼容；
- trust 不允许；
- 缺 required slot；
- 多个 capability 写同一 control 且没有明确覆盖规则；
- submit / export / detail action 排在 required controls 前；
- terminal target 缺失；
- unsupported adapter / operation；
- high-risk destructive action 且无用户确认。

## Execution Contract

执行候选必须通过 WebAgentFlow 已批准的 execution / replay runtime，不得由 LLM 逐步操作浏览器。

执行必须记录：

- candidate id；
- source capability ids；
- ordered action schemas；
- terminal evidence；
- pass / fail / unverified；
- browser event evidence；
- result observation；
- user-facing summary evidence when routed through `wagent chat`。

## Promotion Contract

候选晋升为 `LearnedPath` 必须满足：

- candidate status is `execution_passed`；
- terminal evidence compatible with expected terminal target；
- ingest gate eligible；
- action list is reusable and semantic；
- source capability ids retained in LearnedPath metadata or associated evidence；
- no provider-private oracle data stored in runtime row。

失败、未验证或静态拒绝候选不得晋升为成功 `LearnedPath`。

## Learning Evidence Bundle Contract

WebAgentFlow 应导出 provider-evaluable `waf.learning_evidence_bundle.v1`。它是面向外部评估的
脱敏投影，不是内部数据库 dump，也不是 provider oracle 的副本。

Required top-level sections:

- `operator_actions`: approved surface, command or UI surface, cwd, timestamp, session refs；
- `page_analysis_summary`: bucket counts, visible totals, capability hint kinds and redacted refs；
- `learning_batches`: batch status, policy, planned/attempted/passed/failed/unverified/unsupported counters, warnings；
- `learned_capabilities`: kind, adapter type, action schema summary, terminal target summary, evidence summary, trust, source refs；
- `learned_paths`: path family hint, action count/kinds, source run relation, source capability refs, ingest reason；
- `runs`: pass gate, terminal verdict, attempt ingest evaluation, supervisor summary/confidence, result observation refs；
- `composition`: candidate family, source capability refs, static rejection reason, execution outcome, promotion decision；
- `redaction`: schema version, forbidden-token scan result, redaction warnings。

报告不得包含：

- provider oracle answer；
- target seed copy；
- DOM snapshots；
- selectors unless redacted refs；
- raw UUIDs when an opaque/hash ref can be used；
- private execution handoff payloads；
- credentials, cookies, tokens；
- hidden provider raw evidence。

Validation Site 应只消费该 bundle 的 redacted artifact，不得直接读取 WebAgentFlow 数据库、
内部 ORM payload、private action payload 或 prompt/runtime 内部结构。

## Metrics Contract

本包把“组合生成能力”的主要指标定义为覆盖率和可靠性分层：

- 候选覆盖率：应该生成的 candidate family 生成了多少。
- 参与覆盖率：关键 `LearnedCapability` 是否参与了至少一个合理候选。
- 静态合理率：候选被 provider oracle 评估为 reasonable / risky / invalid 的比例。
- 执行尝试覆盖率：可执行候选中实际执行了多少。
- 晋升可靠性：晋升为 `LearnedPath` 的候选必须 100% 可靠。
- negative evidence 捕获率：失败或无效候选是否被记录而不是静默丢失。

## Runtime Hardcoding Prohibition

Runtime / prompt 不得硬编码：

- Validation Site URL / route；
- field labels；
- button labels；
- selector / test id；
- seed copy；
- provider oracle ids；
- provider expected values。

## Compatibility

- Existing `CapabilityComposer` remains the deterministic plan builder.
- Existing `LearnedPath` replay remains preferred when high-confidence path exists.
- Existing `LearnedCapability`, `LearningBatch`, and `ExplorationRun` rows remain readable.
- No live validation is authorized by this contract.
