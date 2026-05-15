# 12.3 Plan

Status: documentation initialized.

## 本轮范围

本轮只初始化 12.3 Recovery Proposal MVP 文档，不创建或修改代码。

创建：

- `docs/iterations/m12/12.3-recovery-proposal-mvp/README.md`
- `docs/iterations/m12/12.3-recovery-proposal-mvp/intent.md`
- `docs/iterations/m12/12.3-recovery-proposal-mvp/plan.md`
- `docs/iterations/m12/12.3-recovery-proposal-mvp/review.md`

更新：

- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`

不修改 AGENTS / CLAUDE / roadmap / product model / architecture / scope
boundary。若发现 stale reference，只记录到 `review.md` Follow-up。

## Concept Model

未来实现可围绕这些概念建模：

| Concept | Meaning |
|---|---|
| `RecoveryProposal` | 面向用户展示的一组恢复选项，不是 command。 |
| `RecoveryProposalOption` | 单个可展示选项，默认不可执行。 |
| `RecoveryProposalKind` | option 类型，例如 ask user、review evidence、suggest reteach。 |
| `ProposalSource` | proposal 来源，例如 failure boundary 或 abort acknowledgement。 |
| `ProposalEvidence` | 支撑 proposal 的 evidence refs。 |
| `ProposalRiskHint` | 风险提示，例如 side effects unknown 或 policy check required。 |
| `ProposalConfirmationRequirement` | 后续是否需要用户确认或 policy check。 |

## Future Candidate Files

后续 implementation 可能新增或修改：

- `apps/api/app/schemas/recovery.py`
- `apps/api/app/services/recovery/proposal.py`
- `apps/api/tests/test_recovery_proposal.py`
- `docs/iterations/m12/12.3-recovery-proposal-mvp/plan.md`
- `docs/iterations/m12/12.3-recovery-proposal-mvp/review.md`

本轮不创建或修改这些代码文件。

## Future Implementation Steps

1. Define proposal schema in `recovery.py`:
   - proposal source；
   - proposal kind；
   - proposal option；
   - risk hint；
   - confirmation marker；
   - non-executable marker。
2. Implement a deterministic proposal generator:
   - input: `RecoveryBoundary` or `AbortAcknowledgement`；
   - output: `RecoveryProposal`；
   - no DB, browser, network, LLM, conversation dispatcher, retry, replan, or
     LearnedPath write-back。
3. Preserve evidence references:
   - failure classification / reason / recommendation；
   - abort decision / evidence / no-new-action boundary；
   - inflight caveat；
   - source status and structured evidence fields。
4. Keep all options non-executable by default:
   - `non_executable=true`；
   - no command field；
   - no browser action field；
   - no hidden execution side effect。
5. Allow deterministic ordering or labels only:
   - proposal generator may rank options or mark one as recommended；
   - it must not auto-select an option；
   - it must not produce `selected_option_id` or any equivalent selected-state
     field；
   - `recommended_option_ids`, `rank`, and `priority` may be used only for
     display ordering or emphasis；
   - any next step belongs to later user confirmation and downstream package.
6. Update 12.3 review evidence after implementation.

## Future Test Plan

Focused unit tests should cover:

- failure boundary -> `review_evidence` / `consider_retry_later` / `suggest_reteach`
  options as appropriate；
- blocked boundary -> `ask_user_for_context` option；
- uncertain boundary -> `review_evidence` option；
- needs_review boundary -> `review_evidence` option；
- abort acknowledgement -> `abandon_task` / `review_evidence` / later handoff options；
- all options have `non_executable=true` by default；
- recommended option is not auto-selected；
- proposal output has no `selected_option_id` or equivalent selected-state field；
- retry-related option is only `consider_retry_later` and requires 12.4 policy；
- re-teach option does not write LearnedPath；
- takeover option does not implement takeover；
- runtime observation option does not implement M11.2；
- input objects are not mutated；
- forbidden dependency scan excludes DB, browser, network, LLM, conversation dispatcher,
  retry execution, and LearnedPath write-back.

## Future Acceptance Criteria

- Proposal generator is deterministic and side-effect free.
- Proposal output includes source, options, evidence refs, confirmation markers, and
  non-executable markers.
- No proposal option executes retry, replan, browser continuation, takeover,
  teaching, conversation dispatch, or LearnedPath write-back.
- `consider_retry_later` is routed to 12.4 for policy evaluation.
- Proposal ordering / recommendation never becomes auto-selection.
- Proposal schema has no `selected_option_id`.
- Focused unit tests and ruff pass.

## Validation for This Documentation Round

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
