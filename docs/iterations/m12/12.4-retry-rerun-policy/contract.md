# 12.4 Retry / Re-run Policy Contract

状态：proposed

## 概念 / 边界契约

| Concept | Contract |
|---|---|
| `RetryPolicyInput` | Future policy evaluator 的输入。只聚合 12.1 boundary、12.2 abort acknowledgement、12.3 proposal / option、structured evidence refs、future user confirmation marker 和 future policy hints。 |
| `RetryPolicyDecision` | retry / re-run policy 的输出结果。它是 policy result，不是 retry command。 |
| `RetryPolicyEvidence` | 用于解释 policy decision 的结构化 evidence references。必须来自上游结构化输出或 future confirmation / policy marker。 |
| `RetryPolicyReason` | 触发 allow / deny / review / context 的结构化原因，不是自由文本推理。 |
| `RetryRiskLevel` | retry 风险级别，用于表达 side-effect / idempotency 风险。不能替代用户确认。 |
| `RetryConfirmationRequirement` | 表示后续是否需要用户确认或 policy check。它不消费确认，也不执行确认后的 retry。 |
| `RetryPolicyOutcome` | policy outcome：allowed with confirmation、denied、needs context、needs review、or no retry needed。不得包含 execution command。 |

不变原则：

```text
Retry policy is not retry execution.
Retry allowed is not retry started.
Retry requires explicit user confirmation through later flow.
Retry must be denied when side effects are unknown or unsafe.
Retry must not duplicate irreversible external actions.
```

## 状态 / 结果契约

建议 `RetryPolicyOutcome`：

| Outcome | Result contract |
|---|---|
| `retry_allowed_requires_confirmation` | 当前 evidence 没有禁止 retry consideration，但 retry 仍未开始；必须交给后续用户确认和 12.5 flow。 |
| `retry_denied` | retry 被安全策略拒绝。这是有效安全结果，不是 engine failure。 |
| `retry_needs_more_context` | 缺少上下文、确认信息、policy hint 或 evidence，不能判断是否可 retry。 |
| `retry_needs_manual_review` | evidence 冲突或风险不清，需要人工 review。 |
| `no_retry_needed` | 当前结果不需要 retry，例如 success / no recovery needed / abandon task。 |

建议 `RetryPolicyReason`：

| Reason | Meaning |
|---|---|
| `retry_candidate_with_clear_evidence` | proposal 指向 `consider_retry_later`，且 evidence 没有立即禁止 retry consideration。 |
| `side_effects_unknown` | 外部副作用未知，不能安全 retry。 |
| `non_idempotent_action` | 操作不可幂等或可能重复提交。 |
| `irreversible_action_possible` | 可能已经产生不可逆副作用。 |
| `missing_execution_evidence` | 缺少执行、replay、reporter 或 proposal evidence。 |
| `missing_user_confirmation` | 尚未获得后续用户确认。 |
| `unsupported_replay_state` | replay state 不支持 retry 判断。 |
| `abort_boundary_active` | abort / stop boundary 仍然有效。 |
| `policy_source_unknown` | policy input 来源不清，不能安全判断。 |
| `already_succeeded` | 已有 success / no recovery needed evidence。 |

必须明确：

- `retry_allowed_requires_confirmation != retry started`。
- `retry_denied` 是安全结果，不是 failure。
- `no_retry_needed` 适用于 `success_no_recovery_needed` / `no_recovery_needed`
  或明确放弃当前任务的场景。

## Schema / API 契约

本次设计包不新增 API，不新增 CLI，不新增 DB，不新增 frontend。

未来可以在 `apps/api/app/schemas/recovery.py` 设计纯 schema：

- `RetryPolicyInput`
- `RetryPolicyDecision`
- `RetryPolicyEvidence`
- `RetryPolicyOutcome`
- `RetryPolicyReason`
- `RetryRiskLevel`
- `RetryConfirmationRequirement`

这些 schema 必须是纯数据结构，不包含执行逻辑。`RetryPolicyDecision` 不得包含
browser action、retry command、replay command、conversation dispatch command 或
LearnedPath write-back command。

明确保持：

- No API route changes.
- No CLI changes.
- No DB changes.
- No frontend changes.
- No conversation dispatcher changes in 12.4.

## Evidence / Observation 契约

允许输入来源：

- 12.1 `RecoveryBoundary`
- 12.2 `AbortAcknowledgement`
- 12.3 `RecoveryProposal`
- 12.3 `RecoveryProposalOption` where `kind=consider_retry_later`
- structured evidence refs already present in these outputs
- future user confirmation marker
- future policy configuration / hints

12.4 不得读取：

- raw HTML；
- browser state directly；
- DB directly；
- network；
- LLM；
- M11.2 runtime observation as if implemented。

如果 evidence 不足，policy 必须返回 `retry_needs_more_context` 或
`retry_needs_manual_review`，不能假装 retry is allowed，也不能启动 retry。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：12.4 属于 M12 Failure Recovery / Abort / Runtime
  Robustness，不新增 lifecycle stage，不新增 internal Agent role。
- Scope boundary 对齐：12.4 只定义 retry policy，不扩大到 runtime conversation
  flow、browser continuation、teaching mode、takeover 或 third-party integration。
- Roadmap / milestone 对齐：12.4 位于 12.3 proposal generator 之后，12.5
  recovery conversation flow 之前。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本次不改变这些边界。

## 兼容性契约

- 12.1 classifier output remains unchanged.
- 12.2 abort handler output remains unchanged.
- 12.3 proposal generator output remains unchanged.
- Existing `RecoveryBoundary` remains valid.
- Existing `AbortAcknowledgement` remains valid.
- Existing `RecoveryProposal` remains valid.
- Retry policy consumes proposal / boundary / abort evidence but does not mutate them.

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变，不需要 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort / proposal boundaries：不变；12.4 只消费 12.1 /
  12.2 / 12.3 输出并返回 policy decision。

## 非目标

- retry execution；
- re-run execution；
- replan execution；
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

## 未决问题

- 12.4 implementation 前需要审核 `contract.md`、`technical-design.md`、
  `test-plan.md` 和 `plan.md`。
- Future user confirmation marker 的具体字段名由 12.5 conversation flow 接入前
  再定；12.4 只定义 policy 必须要求确认，不消费 runtime confirmation。
- 12.1 / 12.2 历史包仍是旧四件套，缺少新模板的 `contract.md` /
  `technical-design.md` / `test-plan.md`；本次不回填，记录在 `review.md`
  Follow-ups。

不允许空白或隐式省略。只有写明原因时，才允许使用 `N/A`。
