# 12.3 · Recovery Proposal MVP

Status: documentation initialized.

## 目标

12.3 定义 Recovery Proposal MVP：基于 12.1 `RecoveryBoundary` 和 12.2
`AbortAcknowledgement`，生成可展示给用户的恢复选项。

12.3 的核心原则是：

```text
Proposal is not execution.
```

Proposal 是解释、选项和后续 owner 标记，不是 command。它不能执行 retry、
replan、browser continuation、conversation dispatch、LearnedPath write-back
或 teaching / takeover flow。

## 和 12.1 / 12.2 的关系

- **12.1 Failure Classification and Recovery Boundary** 已实现 deterministic
  classifier。它输出 classification、reason、evidence references 和 boundary
  recommendation，但不生成用户可见 proposal。
- **12.2 User Abort / Stop Handling** 已实现 deterministic abort handler。它
  输出 `AbortAcknowledgement`、stop decision 和 abort evidence，但不生成恢复
  菜单。
- **12.3 Recovery Proposal MVP** 接收这些边界结果，定义如何把它们格式化成
  用户可理解、可审计、默认不可执行的 proposal options。

12.3 不重新分类 failure，也不重新处理 abort。它只把已有边界转成后续选择。

## Recovery Proposal 定义

`RecoveryProposal` 是一组可展示给用户的恢复选项。它必须说明：

- proposal 来自哪个 source；
- option 的 kind；
- 为什么展示这个 option；
- 关联哪些 evidence references；
- 是否需要用户确认；
- 是否需要后续 policy check；
- 由哪个后续 owner 处理；
- option 是否可执行。

在 12.3 中，所有 proposal option 默认必须是 `non_executable=true`。即使
option 指向 later retry / replan / takeover / teaching flow，选择它也不能在
12.3 内执行动作。

12.3 可以排序或标记推荐选项，但不能自动选择 proposal。`recommended` 只表示
展示优先级，不表示 system-selected action。

未来实现不应设计 `selected_option_id` 这类字段。可以使用
`recommended_option_ids`、`rank` 或 `priority` 表达展示顺序和推荐程度，但
不能用任何字段暗示系统已经替用户选中了下一步。

## Proposal Sources

建议 source 值：

| Source | 含义 |
|---|---|
| `from_failure_boundary` | 来自 12.1 `failure` classification 或 failure recommendation。 |
| `from_abort_acknowledgement` | 来自 12.2 user abort / stop acknowledgement。 |
| `from_uncertain_result` | 来自 12.1 `uncertain` classification。 |
| `from_blocked_result` | 来自 12.1 `blocked` classification。 |
| `from_manual_review_needed` | 来自 `needs_review` 或 abort `needs_manual_review`。 |

## Proposal Option Kinds

建议 option kinds：

| Kind | 含义 | 关键边界 |
|---|---|---|
| `ask_user_for_context` | 请求用户补充缺失上下文、权限或目标状态。 | 只能询问，不能继续浏览器动作。 |
| `review_evidence` | 请用户或人工 review 当前 evidence。 | 不能把 review 结果预设为 success。 |
| `suggest_reteach` | 建议后续重新教学或更新 LearnedPath。 | 不是 hidden relearning，也不是 LearnedPath write-back。 |
| `consider_retry_later` | 标记未来可交给 12.4 考虑 retry。 | 不是 retry，不判断完整 retry policy。 |
| `abandon_task` | 建议放弃当前任务或保持停止状态。 | 不删除 evidence，不伪造成功。 |
| `handoff_to_takeover_later` | 标记未来可交给用户接管流程。 | 不是 takeover implementation。 |
| `wait_for_runtime_observation_later` | 标记未来可等待更丰富 observation。 | 不是 M11.2 Runtime Observation / Wait-for-change 实现。 |

## Proposal Option Shape

未来实现可围绕这些字段建模，本轮不创建 schema：

| Field | Meaning |
|---|---|
| `id` | 稳定 option id，便于展示和审计。 |
| `kind` | option kind。 |
| `title` | 面向用户的短标题。 |
| `message` | 面向用户的解释文案。 |
| `requires_user_confirmation` | 是否需要用户确认才能进入下一步。 |
| `requires_policy_check` | 是否必须交给 12.4 或其他后续 policy 检查。 |
| `blocked_by` | 阻止直接继续的原因。 |
| `evidence_refs` | 来源 evidence references。 |
| `next_owner` | 后续 owner，例如 user、12.4、12.5 或 manual review。 |
| `non_executable` | 12.3 默认必须为 true。 |

不要在 12.3 schema 中加入 `selected_option_id`。12.3 可以表达推荐顺序，但
selected option 只能来自后续用户确认链路，不能由 proposal generator 产生。

建议 `next_owner`：

- `user`
- `recovery_policy_12_4`
- `conversation_flow_12_5`
- `teaching_or_takeover_future`
- `manual_review`

## Evidence Requirement

每个 proposal option 必须可追溯到结构化 evidence：

- 12.1 `RecoveryBoundary.classification`
- 12.1 `RecoveryBoundary.recommendation`
- 12.1 `RecoveryBoundary.reason`
- 12.1 `RecoveryBoundary.evidence`
- 12.2 `AbortAcknowledgement.decision`
- 12.2 `AbortAcknowledgement.evidence`
- abort `no_new_actions_after`
- abort `inflight_caveat`

如果 evidence 不足，proposal 应优先给出 `review_evidence` 或
`ask_user_for_context`，不能假装可以安全 retry 或 replan。

## Confirmation Requirement

12.3 可以标记 option 是否需要用户确认，但不能消费确认，也不能执行确认后的动作。

默认规则：

- 任何 retry / re-run 相关 option 都必须 `requires_user_confirmation=true`，
  并且 `requires_policy_check=true`。
- 任何 re-teach / LearnedPath update 相关 option 都必须指向后续 teaching /
  path update flow，不能自动写回。
- abort 后的 proposal 不能绕过 12.2 的 no-new-browser-action boundary。
- `non_executable=true` 是所有 12.3 options 的默认状态。

## 和 12.4 / 12.5 / 12.6 的边界

- **12.4 Retry / re-run policy**：决定 retry 是否允许、何时禁止、需要哪些确认。
  12.3 只能产生 `consider_retry_later`。
- **12.5 Recovery conversation flow**：把 proposal 展示、用户选择和后续路由接入
  runtime conversation。12.3 不接 dispatcher / API / CLI。
- **12.6 Recovery tests and evidence**：关闭 M12 的测试和 evidence。12.3 只规划
  proposal 的未来测试，不运行业务测试。

## Non-goals

12.3 不做：

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
- `verify-scenario`。
