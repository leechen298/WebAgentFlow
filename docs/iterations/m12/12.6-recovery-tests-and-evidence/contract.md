# Contract

Status: proposed
Milestone: M12
Type: mixed

## 概念 / 边界契约

| Concept | Contract |
|---|---|
| `M12EvidenceClosure` | M12 recovery evidence closure record. It is an acceptance record, not runtime behavior. |
| `RecoveryValidationCommand` | A command, product surface, or review action used to produce evidence. It must include scope and expected result. |
| `RecoveryValidationResult` | A recorded result. It must be one of `PASS`, `FAIL`, `SKIP`, `NOT_RUN`, or `UNVERIFIED`. |
| `RecoveryBoundaryEvidence` | Evidence that a specific M12 boundary held, such as non-execution, non-relearning, or no browser continuation. |
| `NotRunEvidence` | A required record for scoped-out validation. It must explain why the item was not run and what risk remains. |
| `EvidenceFinding` | A finding from evidence review. It must include severity, source, and action or acceptance note. |
| `EvidenceSeverity` | Finding severity: `blocker`, `p1`, `p2`, `p3`, or `info`. |
| `M12CompletionDecision` | Final M12 evidence decision: `m12_completed`, `m12_completed_with_followups`, `m12_blocked`, or `m12_not_complete`. |

`M12EvidenceClosure` is not a command, retry, replan, browser action, runtime
event, or hidden recovery mechanism.

## 结果契约

`RecoveryValidationResult` semantics:

| Result | Contract |
|---|---|
| `PASS` | Command or reviewed evidence ran successfully and matches the expected boundary. |
| `FAIL` | Command ran or evidence was reviewed and did not meet the expected boundary. |
| `SKIP` | Item was intentionally skipped under a documented condition that still preserves the required boundary. |
| `NOT_RUN` | Item was not executed. It is not pass evidence. |
| `UNVERIFIED` | Evidence is incomplete, indirect, or unavailable. It is not pass evidence. |

Completion decisions:

| Decision | Contract |
|---|---|
| `m12_completed` | All required validation is `PASS`, no blocker / P1 / P2 findings remain, and not-run items are explicitly out of scope. |
| `m12_completed_with_followups` | Required validation is `PASS`, no blocker / P1 / P2 remain, and only P3 / info follow-ups remain. |
| `m12_blocked` | Required validation failed, required evidence is missing, or a boundary is unclear. |
| `m12_not_complete` | M12 work or validation is intentionally incomplete and should not be accepted as closed. |

This design package must not set `m12_completed` or
`m12_completed_with_followups`. Completion decisions are allowed only in the
later evidence-closure submission after validation has actually run.

## Evidence 契约

Valid pass evidence may come from:

- actual command output;
- test result summary with exact command;
- ruff result with exact command;
- `git diff` / `git status` output;
- reviewed file paths and commits;
- explicit not-run table with reason and risk.

Invalid pass evidence:

- implementation claim only;
- agent self-declared pass without command-backed output;
- unrun E2E;
- unrun `verify-scenario`;
- unrun live autonomous run;
- unreviewed screenshot claim;
- docs-only statement presented as runtime behavior.

## Scope 契约

This design package does not add API / CLI / DB / frontend behavior.

Later evidence-closure may update:

- `docs/iterations/m12/12.6-recovery-tests-and-evidence/review.md`;
- `docs/testing/results/2026-05-16-m12-recovery-tests-and-evidence.md`;
- `docs/iterations/m12/README.md`;
- `docs/iterations/m12/m12-plan.md`.

If a test coverage gap is found, later evidence-closure may add focused tests
under `apps/api/tests/test_recovery_*.py`. That is allowed only when the report
records the gap, scope, exact test added, command, and result.

## 不变契约

12.6 does not change:

- Product lifecycle stages;
- Internal Agent roles;
- Public API contracts;
- Database schema;
- Replay status semantics;
- Recovery service boundaries;
- Conversation flow non-execution boundary.

## Not-run Contract

Any scoped-out validation must be recorded as `NOT_RUN` or `UNVERIFIED`, with
a reason and residual risk. The record must not imply pass.

Default not-run items for this design package:

- API tests;
- CLI tests;
- UI smoke;
- E2E;
- `verify-scenario`;
- autonomous run;
- browser continuation;
- actual retry / replan / takeover / teaching execution.
