# 12.5 Recovery Conversation Flow Contract

状态：approved for implementation

## 概念 / 边界契约

| Concept | Contract |
|---|---|
| `RecoveryConversationInput` | conversation-flow service 的输入。聚合当前 conversation session/status、user message / command kind、12.1 boundary、12.2 abort acknowledgement、12.3 proposal、12.4 retry policy decision 和 structured evidence refs。 |
| `RecoveryConversationDecision` | conversation-level 决策结果。它决定显示、询问、记录或 handoff，不是 execution command。 |
| `RecoveryConversationResponse` | 面向用户的 response。它是 user-facing explanation，不是 retry / replan / browser command。 |
| `RecoveryConversationEventPayload` | 可写入现有 conversation event 的 structured payload。它记录 recovery evidence、shown options 和 user choice marker，不执行动作。 |
| `RecoveryChoicePrompt` | 面向用户的 choice prompt，包含说明文字和可见选项。 |
| `RecoveryChoiceOption` | 用户可见选项，不是 executable action。必须标记其 downstream owner 和 execution boundary。 |
| `RecoveryConversationState` | recovery conversation 的建议状态或 mode，不直接改变 DB 状态；实际状态更新由 existing conversation runtime review 后处理。 |
| `RecoveryConversationReason` | 触发 response / prompt / handoff 的结构化原因，不是自由文本推理。 |

不变原则：

```text
Conversation flow is not execution.
Conversation may display proposal options but must not auto-select them.
Conversation may show retry policy result but must not start retry.
Conversation may ask the user for confirmation but must not consume confirmation as execution.
Conversation must record evidence and user-facing explanations.
```

`RecoveryConversationDecision` 和 `RecoveryConversationResponse` 不得包含 retry
command、replan command、browser action、takeover command、teaching command 或
LearnedPath write-back command。

## 状态 / 结果契约

建议 `RecoveryConversationDecision` / `RecoveryConversationState`：

| State / decision | Result contract |
|---|---|
| `recovery_response_ready` | Recovery explanation is ready for user display. No action is executed. |
| `ask_user_for_context` | Ask for missing context or permission. Does not replan automatically. |
| `show_recovery_options` | Show proposal options. Does not auto-select an option. |
| `show_retry_policy_result` | Show retry policy result. Does not start retry. |
| `acknowledge_abort` | Acknowledge stop / abort boundary. Does not resume browser action. |
| `needs_manual_review` | Ask for review or evidence clarification. Does not mark success. |
| `abandon_confirmed_for_conversation` | Records conversation-level abandon intent only. Does not run cleanup or rollback. |
| `handoff_pending` | Records future handoff boundary. Does not execute takeover, teaching, replan or retry. |

必须明确：

- `show_retry_policy_result != retry started`。
- `ask_user_for_context != automatic replan`。
- `abandon_confirmed_for_conversation != browser cleanup / external rollback`。
- `handoff_pending != takeover executed`。
- selected user option is conversation choice only, not execution.

User choice naming contract:

- Prefer `chosen_option_kind`, `conversation_choice`, or `requested_next_step`
  for future internal fields.
- Avoid `selected_action`, `execute_choice`, `run_choice`, `retry_choice`,
  or any field name that implies execution.
- A selected user option only records a conversation choice / requested next
  step. It must carry or preserve a non-execution marker such as
  `non_executable`, `execution_boundary`, or equivalent wording in the response
  / event payload.
- Even when a choice points to retry, replan, takeover, teaching, or observation
  handoff, 12.5 must not execute that downstream action.

## Schema / API 契约

12.5 MVP 不新增 API，不新增 CLI，不新增 DB，不新增 frontend。

未来可以在 `apps/api/app/schemas/recovery.py` 或 recovery conversation module 中设计
内部 schema：

- `RecoveryConversationInput`
- `RecoveryConversationDecision`
- `RecoveryConversationResponse`
- `RecoveryConversationEventPayload`
- `RecoveryChoicePrompt`
- `RecoveryChoiceOption`

这些 schema 必须是纯数据结构。12.5 design package 不新增 public API route。
Conversation API expansion, if needed, must remain within existing conversation
runtime boundary and require implementation review.

Event payload / event type contract:

- Prefer wrapping recovery conversation data inside existing conversation event
  payload mechanisms.
- Do not add a new public API route for recovery conversation in 12.5.
- Do not add a new `ConversationEventType` or `ConversationStatus` by default.
- If implementation proves a new event type or status is required, the
  implementation review must explicitly record:
  - why existing event types / statuses are insufficient;
  - the exact enum addition;
  - compatibility impact for existing event consumers;
  - focused tests proving the new enum records conversation state only and does
    not imply recovery execution.

明确保持：

- No new public API route in 12.5 design package.
- No DB migration.
- No frontend UI.
- No browser action.
- No retry / replan / takeover / teaching execution command.

## Evidence / Observation 契约

允许输入来源：

- 12.1 `RecoveryBoundary`
- 12.2 `AbortAcknowledgement`
- 12.3 `RecoveryProposal`
- 12.4 `RetryPolicyDecision`
- existing conversation session status
- existing conversation event payloads
- user message / command text
- structured evidence refs already present in recovery outputs

12.5 不得读取：

- raw HTML；
- browser state directly；
- DB directly outside existing repos；
- network；
- LLM；
- M11.2 runtime observation as if implemented。

Conversation output 必须保留 evidence references、source decision、shown options、
policy outcome 和 user-facing explanation。若 evidence 不足，conversation 必须询问
context 或 manual review，不能假装已恢复或已执行。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：12.5 属于 M12 Failure Recovery / Abort / Runtime
  Robustness，不新增 lifecycle stage，不新增 internal Agent role。
- Scope boundary 对齐：12.5 只设计 recovery conversation flow，不扩大到 retry
  execution、browser continuation、teaching mode、takeover 或 third-party integration。
- Roadmap / milestone 对齐：12.5 位于 12.1-12.4 deterministic recovery services
  之后，12.6 recovery tests and evidence 之前。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本次不改变这些边界。

## 兼容性契约

- 12.1 classifier output remains unchanged.
- 12.2 abort handler output remains unchanged.
- 12.3 proposal generator output remains unchanged.
- 12.4 retry policy output remains unchanged.
- Existing conversation command / state / orchestrator contracts remain valid unless
  explicitly updated in a later implementation review.
- 12.5 consumes and wraps outputs; it does not mutate upstream recovery outputs.

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变，不需要 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort / proposal / retry-policy boundaries：不变；12.5 只
  包装 12.1-12.4 输出为 conversation response / event payload / state suggestion。

## 非目标

- retry execution；
- re-run execution；
- replan execution；
- browser continuation；
- takeover implementation；
- teaching mode；
- LearnedPath write-back；
- M11.2 Runtime Observation / Wait-for-change；
- API endpoint expansion beyond existing conversation API；
- CLI behavior expansion；
- frontend UI；
- DB migration；
- autonomous exploration；
- hidden relearning；
- `verify-scenario`；
- E2E。

## 未决问题

- 12.5 implementation 应以 `contract.md`、`technical-design.md`、`test-plan.md`
  和 `plan.md` 为输入；若实现时发现这些文档缺失、过期、互相冲突或无法执行，
  应停止并报告具体缺口。
- 若实现需要新增 `ConversationEventType` 或 `ConversationStatus`，必须在实现任务中
  明确 review，因为本设计包只定义 future internal payload / state suggestion。默认
  策略是复用 existing conversation event payload，不新增 enum。

不允许空白或隐式省略。只有写明原因时，才允许使用 `N/A`。
