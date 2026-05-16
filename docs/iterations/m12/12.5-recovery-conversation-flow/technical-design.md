# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

当前已有：

- `apps/api/app/schemas/conversation.py`
  - `ConversationStatus` 已包含 `ABORT_REQUESTED`、`TAKEOVER_REQUESTED`、
    `EXECUTION_FAILED`、`FAILED` 等 runtime states。
  - `ConversationEventType` 已包含 command、state、replay、plan execution、
    task result 和 abort / takeover requested events。
  - `ConversationDispatchResponse` 提供 `user_response`、`events_appended`、
    `allowed`、`error`、`replay_result` 等 dispatch response 字段。
- `apps/api/app/services/conversation/commands.py`
  - pure slash-command parser，已识别 `/abort`、`/takeover`、`/cancel`、`/replay`。
- `apps/api/app/services/conversation/state.py`
  - pure state transition helper，已定义 abort / takeover requested transitions。
- `apps/api/app/services/conversation/orchestrator.py`
  - records messages/events, transitions session status, supports planning preview,
    confirmation gate, explicit replay hook and `dispatch_engine_event` placeholder。
- `apps/api/app/services/recovery/*`
  - 12.1 classifier、12.2 abort handler、12.3 proposal generator、12.4 retry
    policy evaluator 已作为纯 deterministic recovery services 交付。
- Recovery tests:
  - `test_recovery_classifier.py`
  - `test_user_abort_handler.py`
  - `test_recovery_proposal.py`
  - `test_retry_policy.py`
  - `test_recovery_exports.py`

当前缺口：还没有 recovery conversation flow wrapper。Conversation runtime 还不能把
recovery boundary / abort acknowledgement / proposal / retry policy decision 包装成
一致的 user-facing recovery conversation response。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Conversation flow is not execution. | Future `RecoveryConversationResponse` contains display/event/state suggestion only, no command fields. | `test-plan.md`: no execution command / forbidden dependency tests. | Prevents retry/replan/browser continuation. |
| Proposal options are shown, not auto-selected. | Future response preserves option list and display metadata; selected option only comes from explicit user choice input. | `test-plan.md`: recommended displayed but not selected; selected user option is conversation choice only. | Keeps 12.3 boundary. |
| Retry policy result is displayed, not started. | Future flow wraps `RetryPolicyDecision` and writes event payload with policy outcome only. | `test-plan.md`: retry allowed requires confirmation but no execution. | Keeps 12.4 boundary. |
| Abort is acknowledged without new browser actions. | Future abort response uses `AbortAcknowledgement.no_new_actions_after` and `inflight_caveat`. | `test-plan.md`: accepted stop and inflight caveat cases. | Preserves user control. |
| Upstream recovery outputs remain unchanged. | Future service consumes copies / Pydantic models and returns new response data. | `test-plan.md`: input immutability. | Compatibility with 12.1-12.4. |
| No raw HTML / browser / network / LLM reads. | Future service consumes structured recovery and conversation inputs only. | `test-plan.md`: forbidden dependency scan. | Keeps deterministic conversation flow. |

## 实现方案（Proposed Implementation）

Future implementation files:

- `apps/api/app/schemas/recovery.py`
  - Add internal recovery conversation schema if needed.
- `apps/api/app/services/recovery/conversation_flow.py`
  - Add deterministic pure service that converts recovery outputs into user-facing
    conversation response, event payload, and next-state suggestion.
- `apps/api/app/services/conversation/orchestrator.py`
  - Future integration point only; should route existing engine events / session
    state to the recovery conversation service without executing recovery.
- `apps/api/app/services/conversation/state.py`
  - Future state transition review point if recovery-specific status suggestion
    needs mapping to existing statuses.
- `apps/api/tests/test_recovery_conversation_flow.py`
  - Focused unit tests for pure recovery conversation service.
- `apps/api/tests/test_conversation_recovery_flow.py`
  - Limited integration tests around orchestrator/event boundary if implementation
    touches conversation runtime.

本次提交不创建或修改这些代码文件。它只创建 12.5 design package and M12 index
updates。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No new public route in design package; future implementation may use existing conversation API only. | Existing API routes remain unchanged. |
| API response schema | No | Future internal response shape only unless separately reviewed. | No public response shape changes in design package. |
| Database schema / migration | No | No persistence or migration. | Existing conversation tables untouched. |
| CLI | No | No CLI behavior expansion for MVP design. | `wagent conversation` unchanged. |
| Console UI | No | No frontend display in 12.5 design package. | UI belongs to future work if scoped. |
| Conversation events | Future | Future internal event payload design may wrap recovery outputs. | New event enum/status changes require implementation review. |
| Replay execution | No | No replay command or continuation. | Replay semantics unchanged. |
| Reporter | No | Task Result Reporter remains upstream evidence. | Reporter output unchanged. |
| Recovery services | Future | Future conversation flow wrapper consumes 12.1-12.4 outputs. | Upstream services unchanged. |
| Worker / async jobs | No | No worker path. | Async behavior unchanged. |
| Tests / fixtures | Future | Unit and limited conversation integration tests in future implementation. | No E2E or live run. |
| Docs | Yes | 12.5 design package and M12 index sync. | Current commit is docs-only. |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

Future internal schema additions may include:

- `RecoveryConversationInput`
- `RecoveryConversationDecision`
- `RecoveryConversationResponse`
- `RecoveryConversationEventPayload`
- `RecoveryChoicePrompt`
- `RecoveryChoiceOption`
- `RecoveryConversationState`
- `RecoveryConversationReason`

Expected properties:

- `RecoveryConversationResponse` contains user-facing text, prompt/options if any,
  evidence refs, source recovery objects, policy outcome and next-state suggestion.
- `RecoveryChoiceOption` contains display label, kind, downstream owner and
  non-execution marker.
- No schema contains retry command, replan command, browser action, takeover command,
  teaching command or LearnedPath write-back field.
- Inputs are structured Pydantic models or mappings validated into those models.

## 服务 / 模块设计（Service / Module Design）

Future module:

```text
apps/api/app/services/recovery/conversation_flow.py
```

Public entry shape:

```python
build_recovery_conversation_response(
    *,
    session_status: str,
    user_input: str | None = None,
    command_kind: str | None = None,
    boundary: RecoveryBoundary | None = None,
    abort: AbortAcknowledgement | None = None,
    proposal: RecoveryProposal | None = None,
    retry_policy: RetryPolicyDecision | None = None,
) -> RecoveryConversationResponse
```

Service properties:

- deterministic；
- side-effect free；
- no DB write in pure service；
- no browser；
- no network；
- no LLM；
- no retry execution；
- no replan execution；
- no takeover execution；
- no LearnedPath write-back。

## 数据流（Data Flow）

```text
Conversation session/status + user message/command
  + 12.1 RecoveryBoundary
  + 12.2 AbortAcknowledgement
  + 12.3 RecoveryProposal
  + 12.4 RetryPolicyDecision
  -> RecoveryConversationFlow
  -> RecoveryConversationResponse(user_response, prompt/options, evidence)
  -> proposed RecoveryConversationEventPayload
  -> next conversation state suggestion
```

Future orchestrator integration should append conversation messages/events using existing
repo paths. Pure recovery conversation service must not write DB directly.

## 状态推导（Status / State Derivation）

Recommended derivation order:

1. Abort acknowledgement present -> `acknowledge_abort` response. If inflight caveat
   exists, explain side-effect uncertainty.
2. Retry policy decision present -> `show_retry_policy_result` and ask confirmation /
   context / review based on policy outcome.
3. Recovery proposal present -> `show_recovery_options`; display options without
   auto-selection.
4. Recovery boundary `blocked` / `ask_user` -> `ask_user_for_context`.
5. Recovery boundary `uncertain` / `needs_review` -> `needs_manual_review`.
6. Recovery boundary `failure` -> explain failure evidence and show proposal options if
   present.
7. Unknown or conflicting source -> conservative `needs_manual_review`.

Fallback must be conservative. Never infer recovery success from replay completion,
proposal recommendation, retry policy allow, or selected user choice alone.

## 兼容性（Compatibility）

- Existing `RecoveryBoundary` remains valid input.
- Existing `AbortAcknowledgement` remains valid input.
- Existing `RecoveryProposal` remains valid input.
- Existing `RetryPolicyDecision` remains valid input.
- Existing conversation command / state / orchestrator contracts remain valid unless
  explicitly updated in a later implementation review.
- No public API, DB, CLI, UI, replay, reporter, worker compatibility impact in the
  12.5 design package.

## 失败 / 边界情况（Failure / Edge Cases）

- Missing recovery source -> ask manual review, not success.
- Proposal option exists without policy decision -> display option and mark downstream
  policy required, not retry allowed.
- Retry policy `retry_allowed_requires_confirmation` -> ask confirmation, no retry.
- Retry policy `retry_denied` -> explain denial, no retry.
- Abort `cannot_interrupt_inflight_action` -> acknowledge stop and side-effect
  uncertainty, no new browser action.
- User selects abandon -> record conversation-level abandon intent only; no browser
  cleanup or external rollback.
- User selects takeover / re-teach handoff -> record `handoff_pending` only; no
  takeover or teaching implementation.
- Multiple options -> display recommended / rank as emphasis only; selected option
  must come from explicit user input.

## 非目标（Non-goals）

- API endpoint expansion；
- CLI behavior expansion；
- frontend UI；
- DB / migration；
- retry execution；
- re-run execution；
- replan execution；
- browser continuation；
- takeover implementation；
- teaching mode；
- LearnedPath write-back；
- M11.2 Runtime Observation / Wait-for-change；
- live autonomous run；
- `verify-scenario`。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Unit / recovery conversation | Prove recovery sources map to user-facing responses and state suggestions. | `test-plan.md` Unit matrix. |
| Proposal display boundary | Prove options are displayed but not auto-selected or executed. | `test-plan.md` proposal scenarios. |
| Retry policy display boundary | Prove policy results are shown without starting retry. | `test-plan.md` retry policy scenarios. |
| Abort boundary | Prove accepted stop and inflight caveat are acknowledged safely. | `test-plan.md` abort scenarios. |
| Conversation integration | Prove future orchestrator/event payload wrapping does not execute recovery. | `test-plan.md` limited integration matrix. |
| Forbidden dependencies | Prove no browser/network/LLM/retry/replan/write-back imports. | `test-plan.md` forbidden dependency scan. |
| API / UI / E2E / live | Not part of design package. | `test-plan.md` Not Run / N/A sections. |

## 验证命令入口（Validation Commands）

Design package generation runs docs-only checks:

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```

Future implementation should run focused unit and limited integration tests named in
`test-plan.md`.
