# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

当前已有：

- `apps/api/app/schemas/recovery.py`
  - 12.1 `RecoveryEvidence` / `RecoveryBoundary`
  - 12.2 `UserAbortSignal` / `UserAbortState` / `AbortEvidence` /
    `AbortAcknowledgement`
- `apps/api/app/services/recovery/classifier.py`
  - deterministic 12.1 recovery boundary classifier
- `apps/api/app/services/recovery/abort_handler.py`
  - deterministic 12.2 user abort handler
- `apps/api/tests/test_recovery_classifier.py`
- `apps/api/tests/test_user_abort_handler.py`

12.3 目前只有文档包。本轮不创建 proposal schema、service 或 tests。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Proposal is not execution. | Future proposal generator returns pure data object only. | `test-plan.md`: non-execution / forbidden dependency tests. | No command field, no browser action field. |
| Proposal option defaults to `non_executable=true`. | Future `RecoveryProposalOption` schema default and unit tests. | `test-plan.md`: all options non-executable. | Default must not depend on caller. |
| Recommended option is not selected option. | Future schema may expose `recommended_option_ids`, `rank`, or `priority`, but no `selected_option_id`. | `test-plan.md`: no selected-state field and recommended not auto-selected. | User confirmation belongs to 12.5 flow. |
| `consider_retry_later` is not retry. | Future generator maps retry-compatible boundary to proposal kind only. | `test-plan.md`: retry option is handoff-only. | 12.4 owns retry policy. |
| `suggest_reteach` is not LearnedPath write-back. | Future generator only emits handoff option. | `test-plan.md`: no write-back dependency. | Teaching / path update is later work. |
| `wait_for_runtime_observation_later` is not M11.2 implementation. | Future generator only labels future observation handoff. | `test-plan.md`: no M11.2 dependency. | M11.2 remains separate. |
| Only consume 12.1 / 12.2 structured outputs. | Future service accepts `RecoveryBoundary` or `AbortAcknowledgement`. | `test-plan.md`: input source matrix. | No raw HTML / DB / browser / LLM access. |

## 实现方案（Proposed Implementation）

Future implementation should add:

- schema definitions in `apps/api/app/schemas/recovery.py`
- deterministic proposal generator in `apps/api/app/services/recovery/proposal.py`
- focused unit tests in `apps/api/tests/test_recovery_proposal.py`

The proposal generator should accept either:

- `RecoveryBoundary`
- `AbortAcknowledgement`

and return:

- `RecoveryProposal`

The generator must be deterministic and side-effect free. It must not access DB,
browser, network, LLM provider, conversation dispatcher, retry execution,
replan execution, or LearnedPath write-back.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No route changes in 12.3 MVP. | Existing API surfaces remain unchanged. |
| API response schema | No | Future proposal schema remains internal until 12.5 integration. | No public response shape changes. |
| Database schema / migration | No | No persistence or migration. | Existing DB untouched. |
| CLI | No | No CLI command or output changes. | `wagent conversation` unaffected. |
| Console UI | No | No frontend display in 12.3 MVP. | UI belongs to later flow if needed. |
| Conversation events | No | No dispatcher or event routing. | 12.5 owns conversation flow. |
| Replay execution | No | No replay command or continuation. | Replay semantics unchanged. |
| Reporter | No | No Task Result Reporter changes. | Reporter output remains upstream evidence. |
| Worker / async jobs | No | No worker path. | Async behavior unchanged. |
| Tests / fixtures | Future unit tests only | `test_recovery_proposal.py` in implementation round. | No E2E or live run. |
| Docs | Yes | This design package alignment. | Implementation docs now follow code iteration gate. |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

Future schema additions may include:

- `ProposalSource`
- `RecoveryProposalKind`
- `ProposalRiskHint`
- `ProposalConfirmationRequirement`
- `ProposalOwner`
- `RecoveryProposalOption`
- `RecoveryProposal`

Expected properties:

- `RecoveryProposal.options` contains display options only.
- Each option has `non_executable=true` by default.
- No `selected_option_id` or equivalent selected-state field.
- Optional `recommended_option_ids`, `rank`, or `priority` can express display
  ordering or emphasis only.
- Evidence references are copied or transformed from 12.1 / 12.2 structured inputs.

These schema additions must be backward compatible with existing
`RecoveryBoundary` and `AbortAcknowledgement`.

## 服务 / 模块设计（Service / Module Design）

Future module:

```text
apps/api/app/services/recovery/proposal.py
```

Suggested public entry:

```python
generate_recovery_proposal(source: RecoveryBoundary | AbortAcknowledgement | Mapping[str, Any]) -> RecoveryProposal
```

Suggested class:

```python
RecoveryProposalGenerator.generate(...)
```

Service properties:

- deterministic；
- pure logic；
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
12.1 RecoveryBoundary
  -> RecoveryProposalGenerator
  -> RecoveryProposal(options=[...], evidence_refs=[...], non_executable markers)

12.2 AbortAcknowledgement
  -> RecoveryProposalGenerator
  -> RecoveryProposal(options=[...], evidence_refs=[...], no-new-action boundary preserved)
```

The generator must preserve evidence and risk context. It may derive display
ordering, but must not derive a selected option.

## 状态推导（Status / State Derivation）

Future mapping:

| Input | Default proposal direction |
|---|---|
| `blocked` / `ask_user` | `ask_user_for_context` |
| `failure` / `stop` | `review_evidence` or `abandon_task` |
| `failure` / `suggest_reteach` | `suggest_reteach` |
| `failure` / `retry_possible_requires_confirmation` | `consider_retry_later` |
| `uncertain` | `review_evidence` |
| `needs_review` | `review_evidence` |
| abort `accepted_stop` | `abandon_task`, `review_evidence`, or later handoff |
| abort `cannot_interrupt_inflight_action` | `review_evidence` plus side-effect risk hint |
| abort `needs_manual_review` | `review_evidence` |

Fallback: if source evidence is insufficient or unsupported, emit
`review_evidence` with a risk hint rather than inventing an executable action.

## 兼容性（Compatibility）

- Existing `RecoveryBoundary` remains valid input.
- Existing `AbortAcknowledgement` remains valid input.
- No changes to classifier or abort handler behavior.
- No public API, DB, CLI, UI, replay, or reporter compatibility impact in 12.3 MVP.

## 失败 / 边界情况（Failure / Edge Cases）

- Missing evidence refs -> emit `review_evidence`, not retry or replan.
- Abort with `inflight_caveat=true` -> include side-effect risk hint.
- `no_new_actions_after=true` -> proposal must not imply browser continuation.
- `retry_possible_requires_confirmation` -> emit `consider_retry_later`, not retry.
- Unknown source shape -> validation error or conservative `review_evidence`, depending on final schema decision.
- Multiple possible options -> rank or recommend only; do not select.

## 非目标（Non-goals）

- API endpoint；
- CLI command；
- frontend UI；
- DB / migration；
- conversation dispatcher；
- retry policy；
- retry execution；
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
| Unit / recovery proposal | Prove mapping from 12.1 / 12.2 inputs to non-executable proposal options. | `test-plan.md` Unit matrix. |
| Forbidden dependencies | Prove generator has no DB/browser/network/LLM/dispatcher/retry/write-back imports. | `test-plan.md` forbidden dependency scan. |
| Evidence preservation | Prove evidence refs and abort caveats are preserved. | `test-plan.md` evidence scenarios. |
| API / UI / E2E / live | Not part of 12.3 MVP. | `test-plan.md` Not Run / N/A sections. |

## 验证命令入口（Validation Commands）

Future implementation should run focused unit and static checks. This
documentation alignment round runs docs-level checks only.

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print
git status --short docs/iterations/m11
git diff --name-only
```
