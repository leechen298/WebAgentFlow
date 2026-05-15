# 12.3 Recovery Proposal MVP Contract

状态：implemented

## 概念 / 边界契约

| Concept | Contract |
|---|---|
| `RecoveryProposal` | 面向用户展示的一组恢复选项。它是展示层 / 解释层 / 选项集合，不是 execution command。 |
| `RecoveryProposalOption` | 单个 proposal option。默认 `non_executable=true`，不能包含会触发浏览器动作、retry、replan 或 write-back 的命令语义。 |
| `RecoveryProposalKind` | option 的类型，决定用户看到的建议类别，不决定执行动作。 |
| `ProposalSource` | proposal 的来源，只能来自 12.1 `RecoveryBoundary` 或 12.2 `AbortAcknowledgement` 及其已有 structured evidence refs。 |
| `ProposalEvidence` | option 关联的 evidence references，必须可追溯到输入对象。 |
| `ProposalRiskHint` | 风险提示，例如 side effects unknown、policy check required、requires user context。它不能替代 policy decision。 |
| `ProposalConfirmationRequirement` | 表示后续是否需要用户确认或下游 policy check。它不消费确认，也不执行确认后的动作。 |
| `ProposalOwner` / `next_owner` | 后续责任方，例如 user、12.4 retry policy、12.5 conversation flow、manual review、future teaching / takeover flow。 |

不变原则：

```text
Proposal is not execution.
Proposal is not command.
Proposal option is non-executable by default.
Recommended option is not selected option.
```

未来 schema 不应设计 `selected_option_id` 或任何等价 selected-state 字段。可以使用
`recommended_option_ids`、`rank` 或 `priority` 表示展示顺序或推荐程度，但 selected
option 只能来自后续用户确认链路。

## 状态 / 结果契约

建议 `RecoveryProposalKind`：

| Kind | Result contract |
|---|---|
| `ask_user_for_context` | 请求用户补充缺失上下文、权限或目标状态。不能继续浏览器动作。 |
| `review_evidence` | 请求用户或人工 review 当前 evidence。不能把 review 结果预设为 success。 |
| `suggest_reteach` | 建议后续重新教学或更新 LearnedPath。不是 hidden relearning，也不是 LearnedPath write-back。 |
| `consider_retry_later` | 标记未来可交给 12.4 考虑 retry。不是 retry，也不是完整 safe-retry 判断。 |
| `abandon_task` | 建议放弃当前任务或保持停止状态。不删除 evidence，不伪造成功。 |
| `handoff_to_takeover_later` | 标记未来可交给用户接管流程。不是 takeover implementation。 |
| `wait_for_runtime_observation_later` | 标记未来可等待更丰富 observation。不是 M11.2 Runtime Observation / Wait-for-change 实现。 |

推荐顺序、rank 或 priority 只影响展示，不表示系统选择。任何下一步动作必须由后续
用户确认和下游包处理。

## Schema / API 契约

本轮不新增 API，不新增 CLI，不新增 DB，不新增 frontend。

未来可以在 `apps/api/app/schemas/recovery.py` 设计纯 schema：

- `RecoveryProposal`
- `RecoveryProposalOption`
- `RecoveryProposalKind`
- `ProposalSource`
- `ProposalRiskHint`
- `ProposalConfirmationRequirement`

这些 schema 必须是纯数据结构，不包含执行逻辑。它们不得改变现有 API route、
conversation event、database schema 或 frontend contract。

明确保持：

- No API route changes.
- No CLI changes.
- No DB changes.
- No frontend changes.
- No conversation dispatcher changes in 12.3.

## Evidence / Observation 契约

允许的输入来源：

- 12.1 `RecoveryBoundary`
- 12.2 `AbortAcknowledgement`
- already-present structured evidence refs inside those outputs

12.3 不得读取：

- raw HTML；
- browser state directly；
- DB directly；
- network；
- LLM；
- M11.2 runtime observation as if implemented。

如果 evidence 不足，proposal 必须优先给出 `review_evidence` 或
`ask_user_for_context`，不能假装可以安全 retry、replan 或 continue。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：12.3 属于 M12 Failure Recovery / Abort / Runtime
  Robustness，不新增 lifecycle stage，不新增 internal Agent role。
- Scope boundary 对齐：12.3 只定义 failure / abort 后的下一步 proposal，不扩大到
  target-site ownership、account、remote trigger 或 third-party integration。
- Roadmap / milestone 对齐：12.3 是 M12 内的 Recovery Proposal MVP，位于 12.1
  classification 和 12.2 abort handling 之后，12.4 retry policy 和 12.5
  conversation flow 之前。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本轮不改变这些边界。

## 兼容性契约

- 12.1 classifier output remains unchanged.
- 12.2 abort handler output remains unchanged.
- Existing `RecoveryBoundary` remains valid.
- Existing `AbortAcknowledgement` remains valid.
- 12.3 only consumes these outputs; it must not require upstream schema changes
  for the MVP design.

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变，不需要 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变；12.3 只消费 12.1 / 12.2 输出。

## 非目标

- retry / re-run policy；
- retry execution；
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

- 12.3 implementation 应以 `contract.md`、`technical-design.md`、
  `test-plan.md` 和 `plan.md` 为执行依据；若实现时发现这些文档缺失、过期、
  互相冲突或无法执行，应停止并报告具体缺口。
- 12.0 / 12.1 / 12.2 历史包仍是旧四件套；是否回填新模板由后续文档治理任务决定。
