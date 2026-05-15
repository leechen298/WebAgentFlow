# 技术设计（Technical Design）

状态：proposed

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
- `apps/api/app/services/recovery/__init__.py`
  - package-level exports for 12.1 / 12.2 / 12.3 service entrypoints
- `apps/api/tests/test_recovery_classifier.py`
- `apps/api/tests/test_user_abort_handler.py`
- `apps/api/tests/test_recovery_proposal.py`
- `apps/api/tests/test_recovery_exports.py`

12.4 当前只生成 design package。后续实现提交才会新增 retry policy schema、
service 和 tests。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Retry policy is not retry execution. | Future `RetryPolicyDecision` is pure data; no command/browser/replay fields. | `test-plan.md`: forbidden dependency and no execution command tests. | Policy output cannot start retry. |
| Retry allowed is not retry started. | Outcome `retry_allowed_requires_confirmation` requires later user confirmation. | `test-plan.md`: missing confirmation scenario. | 12.5 owns confirmation flow. |
| Retry must be denied when side effects are unknown or unsafe. | Future evaluator maps side-effect / inflight / irreversible risk to `retry_denied`. | `test-plan.md`: side effects unknown, inflight, irreversible cases. | Fail-closed. |
| Retry must not duplicate irreversible external actions. | Future risk / reason model includes non-idempotent and irreversible action reasons. | `test-plan.md`: non-idempotent / irreversible matrix. | No browser action in 12.4. |
| 12.1 / 12.2 / 12.3 outputs remain unchanged. | Future service consumes existing models and does not mutate inputs. | `test-plan.md`: compatibility and input immutability. | Backward compatible. |
| No raw HTML / DB / browser / network / LLM reads. | Future evaluator uses only structured input models and evidence refs. | `test-plan.md`: forbidden dependency scan. | Keeps policy deterministic. |

## 实现方案（Proposed Implementation）

Future implementation files:

- `apps/api/app/schemas/recovery.py`
  - Add retry policy literals and Pydantic models.
- `apps/api/app/services/recovery/retry_policy.py`
  - Add deterministic retry policy evaluator.
- `apps/api/tests/test_retry_policy.py`
  - Add focused unit tests from `test-plan.md`.

本次提交不创建或修改这些代码文件。它只创建 12.4 design package and M12 index
updates。

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
| Tests / fixtures | Future only | `test_retry_policy.py` in future implementation. | No E2E or live run. |
| Docs | Yes | 12.4 design package and M12 index sync. | Current commit is docs-only. |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

Future schema additions in `apps/api/app/schemas/recovery.py`:

- `RetryPolicyOutcome`
- `RetryPolicyReason`
- `RetryRiskLevel`
- `RetryConfirmationRequirement`
- `RetryPolicyEvidence`
- `RetryPolicyInput`
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

Future module:

```text
apps/api/app/services/recovery/retry_policy.py
```

Public entry:

```python
evaluate_retry_policy(
    source: RecoveryProposal | RecoveryBoundary | AbortAcknowledgement | Mapping[str, Any],
    *,
    selected_option_kind: RecoveryProposalKind | None = None,
    user_confirmed: bool = False,
) -> RetryPolicyDecision
```

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
  + optional future user confirmation marker
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
- `RecoveryProposalOption.kind=abandon_task` -> `no_retry_needed` or `retry_denied`.
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

Design package generation runs docs-only checks:

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

Future implementation should run:

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py -q
cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py
```
