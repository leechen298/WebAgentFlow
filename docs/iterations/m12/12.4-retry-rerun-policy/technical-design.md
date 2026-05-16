# 技术设计（Technical Design）

状态：implemented

## 当前状态（Current State）

当前已有：

- `apps/api/app/schemas/recovery.py`
  - 12.1 `RecoveryEvidence` / `RecoveryBoundary`
  - 12.2 `UserAbortSignal` / `UserAbortState` / `AbortEvidence` /
    `AbortAcknowledgement`
  - 12.3 `RecoveryProposal` / `RecoveryProposalOption` / `RecoveryProposalKind` /
    `ProposalSource` / `ProposalRiskHint` / `ProposalConfirmationRequirement` /
    `ProposalOwner`
- `apps/api/app/services/recovery/classifier.py`
  - deterministic 12.1 recovery boundary classifier
- `apps/api/app/services/recovery/abort_handler.py`
  - deterministic 12.2 user abort handler
- `apps/api/app/services/recovery/proposal.py`
  - deterministic 12.3 recovery proposal generator
- `apps/api/app/services/recovery/retry_policy.py`
  - deterministic 12.4 retry / re-run policy evaluator
- `apps/api/app/services/recovery/__init__.py`
  - package-level exports for 12.1 / 12.2 / 12.3 / 12.4 service entrypoints
- `apps/api/tests/test_recovery_classifier.py`
- `apps/api/tests/test_user_abort_handler.py`
- `apps/api/tests/test_recovery_proposal.py`
- `apps/api/tests/test_recovery_exports.py`
- `apps/api/tests/test_retry_policy.py`

12.4 已实现 retry policy schema、service 和 tests。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Retry policy is not retry execution. | `RetryPolicyDecision` is pure data; no command/browser/replay fields. | `test_retry_policy.py`: forbidden dependency and no execution command tests. | Policy output cannot start retry. |
| Retry allowed is not retry started. | Outcome `retry_allowed_requires_confirmation` requires later user confirmation. | `test-plan.md`: missing confirmation scenario. | 12.5 owns confirmation flow. |
| Retry must be denied when side effects are unknown or unsafe. | Evaluator maps side-effect / inflight / irreversible risk to `retry_denied`. | `test_retry_policy.py`: side effects unknown, inflight, irreversible cases. | Fail-closed. |
| Retry must not duplicate irreversible external actions. | Risk / reason model includes non-idempotent and irreversible action reasons. | `test_retry_policy.py`: non-idempotent / irreversible matrix. | No browser action in 12.4. |
| 12.1 / 12.2 / 12.3 outputs remain unchanged. | Service consumes existing models and does not mutate inputs. | `test_retry_policy.py`: compatibility and input immutability. | Backward compatible. |
| No raw HTML / DB / browser / network / LLM reads. | Evaluator uses only structured input models and evidence refs. | `test_retry_policy.py`: forbidden dependency scan. | Keeps policy deterministic. |

## 实现方案（Proposed Implementation）

Implemented files:

- `apps/api/app/schemas/recovery.py`
  - Added retry policy literals and Pydantic models.
- `apps/api/app/services/recovery/retry_policy.py`
  - Added deterministic retry policy evaluator.
- `apps/api/tests/test_retry_policy.py`
  - Added focused unit tests from `test-plan.md`.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No route changes in 12.4 design package or implementation MVP. | Existing API surfaces remain unchanged. |
| API response schema | No | Future schema remains internal until a later conversation/API integration. | No public response shape changes. |
| Database schema / migration | No | No persistence or migration. | Existing DB untouched. |
| CLI | No | No CLI command or output changes. | `wagent conversation` unaffected. |
| Console UI | No | No frontend display in 12.4 MVP. | UI belongs to later flow if needed. |
| Conversation events | No | No dispatcher or event routing. | 12.5 owns conversation flow. |
| Replay execution | No | No replay command or continuation. | Replay semantics unchanged. |
| Reporter | No | No Task Result Reporter changes. | Reporter output remains upstream evidence. |
| Worker / async jobs | No | No worker path. | Async behavior unchanged. |
| Tests / fixtures | Yes | `test_retry_policy.py` added. | No E2E or live run. |
| Docs | Yes | 12.4 docs and M12 index sync. | Records implementation evidence. |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

Schema additions in `apps/api/app/schemas/recovery.py`:

- `RetryPolicyOutcome`
- `RetryPolicyReason`
- `RetryRiskLevel`
- `RetryConfirmationRequirement`
- `RetryPolicyEvidence`
- `RetryPolicyDecision`

Expected properties:

- `RetryPolicyDecision.outcome` uses one of:
  - `retry_allowed_requires_confirmation`
  - `retry_denied`
  - `retry_needs_more_context`
  - `retry_needs_manual_review`
  - `no_retry_needed`
- `RetryPolicyDecision` includes reason, evidence refs, risk level and
  confirmation requirement.
- `RetryPolicyDecision` contains no execution command, browser action,
  replay command, selected proposal execution, or LearnedPath write-back field.
- Inputs are structured Pydantic models or mappings validated into those models.

## 服务 / 模块设计（Service / Module Design）

Implemented module:

```text
apps/api/app/services/recovery/retry_policy.py
```

Public entry:

```python
evaluate_retry_policy(
    source: RecoveryProposal | RecoveryBoundary | AbortAcknowledgement | Mapping[str, Any],
    *,
    selected_option_kind: RecoveryProposalKind | None = None,
    has_user_confirmation_marker: bool = False,
) -> RetryPolicyDecision
```

`has_user_confirmation_marker` 只影响 policy outcome。它不是 execution consent
consumer，不启动 retry，也不代表 retry 已经被执行。实际 confirmation 消费和
conversation handoff 属于 12.5。

Class:

```python
RetryPolicyEvaluator.evaluate(...)
```

Service properties:

- deterministic；
- side-effect free；
- no DB；
- no browser；
- no network；
- no LLM；
- no conversation dispatcher；
- no retry execution；
- no replan execution；
- no LearnedPath write-back。

## 数据流（Data Flow）

```text
12.3 RecoveryProposal
  + optional future selected option kind
  + optional future has_user_confirmation_marker
  + structured evidence refs
  -> RetryPolicyEvaluator
  -> RetryPolicyDecision(outcome, reason, risk, confirmation requirement, evidence)

12.1 RecoveryBoundary / 12.2 AbortAcknowledgement
  -> RetryPolicyEvaluator
  -> RetryPolicyDecision(no retry / denied / needs review / needs context)
```

`RecoveryProposalOption.kind=consider_retry_later` 是最直接的 retry policy
input，但仍然不是 retry command。Policy allowed 仍需 later user confirmation。

## 状态推导（Status / State Derivation）

Recommended derivation order:

1. Success / no recovery needed -> `no_retry_needed`。
2. Active abort boundary / in-flight caveat -> `retry_denied`。
3. Side effects unknown / irreversible / non-idempotent evidence -> `retry_denied`。
4. Missing execution / proposal / policy evidence -> `retry_needs_more_context`。
5. Review-only proposal or uncertain evidence -> `retry_needs_manual_review`。
6. `consider_retry_later` with clear evidence and no deny reasons ->
   `retry_allowed_requires_confirmation`。
7. Unknown source -> `retry_needs_manual_review` or `retry_denied` depending on risk evidence。

Fallback must be conservative. Never infer retry allowed from a generic failure,
completed replay, or proposal recommendation alone.

## 兼容性（Compatibility）

- Existing `RecoveryBoundary` remains valid input.
- Existing `AbortAcknowledgement` remains valid input.
- Existing `RecoveryProposal` remains valid input.
- Existing classifier / abort handler / proposal generator behavior remains unchanged.
- No public API, DB, CLI, UI, replay, reporter, or worker compatibility impact in
  12.4 MVP.

## 失败 / 边界情况（Failure / Edge Cases）

- Missing evidence refs -> `retry_needs_more_context`, not retry allowed.
- `AbortAcknowledgement.no_new_actions_after=true` -> deny or require manual review;
  no browser continuation.
- `AbortAcknowledgement.inflight_caveat=true` -> `retry_denied` because side effects
  may be unknown.
- `RecoveryProposalOption.kind=consider_retry_later` with side-effect risk ->
  `retry_denied`.
- `RecoveryProposalOption.kind=review_evidence` -> `retry_needs_manual_review`.
- `RecoveryProposalOption.kind=abandon_task` -> `no_retry_needed` by default.
  Preserve side-effect risk in reason / evidence if present, but do not present
  abandon as a retry failure.
- Unknown source shape -> conservative `retry_needs_manual_review` / `retry_denied`.
- Multiple proposal options -> policy evaluates explicit selected option only in future
  flow; recommended order is not selected state.

## 非目标（Non-goals）

- API endpoint；
- CLI command；
- frontend UI；
- DB / migration；
- conversation dispatcher；
- retry execution；
- re-run execution；
- replan execution；
- browser continuation；
- LearnedPath write-back；
- teaching mode；
- takeover implementation；
- M11.2 Runtime Observation / Wait-for-change；
- live autonomous run；
- `verify-scenario`。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Unit / retry policy | Prove mapping from proposal / boundary / abort inputs to policy outcomes. | `test-plan.md` Unit matrix. |
| Side-effect / idempotency | Prove unknown / unsafe side effects deny retry. | `test-plan.md` risk scenarios. |
| Confirmation boundary | Prove allowed policy still requires confirmation and never starts retry. | `test-plan.md` confirmation scenarios. |
| Forbidden dependencies | Prove evaluator has no DB/browser/network/LLM/dispatcher/retry/write-back imports. | `test-plan.md` forbidden dependency scan. |
| Input immutability | Prove inputs are not mutated. | `test-plan.md` immutability scenario. |
| API / UI / E2E / live | Not part of 12.4 MVP. | `test-plan.md` Not Run / N/A sections. |

## 验证命令入口（Validation Commands）

Implementation validation runs focused recovery tests and static checks:

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py -q
cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py
```
