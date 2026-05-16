# Technical Design

Status: proposed
Milestone: M12
Type: mixed

## Current State

M12 currently has shipped deterministic recovery services:

- 12.1 classifier: `apps/api/app/services/recovery/classifier.py`
- 12.2 abort handler: `apps/api/app/services/recovery/abort_handler.py`
- 12.3 proposal generator: `apps/api/app/services/recovery/proposal.py`
- 12.4 retry policy evaluator: `apps/api/app/services/recovery/retry_policy.py`
- 12.5 conversation flow: `apps/api/app/services/recovery/conversation_flow.py`
- package exports: `apps/api/app/services/recovery/__init__.py`

Focused tests exist for the recovery chain:

- `apps/api/tests/test_recovery_classifier.py`
- `apps/api/tests/test_user_abort_handler.py`
- `apps/api/tests/test_recovery_proposal.py`
- `apps/api/tests/test_retry_policy.py`
- `apps/api/tests/test_recovery_conversation_flow.py`
- `apps/api/tests/test_recovery_exports.py`

12.6 does not add runtime behavior. It defines how to close M12 evidence.

## Contract Alignment / Invariants

| Contract requirement | Evidence closure mechanism | Validation entry |
|---|---|---|
| Evidence closure is not runtime behavior. | 12.6 docs define report shape and commands only. | Docs-only diff and no code/package status check. |
| Required validation must be command-backed. | `test-plan.md` lists exact pytest / ruff / diff commands. | Later evidence-closure report. |
| `NOT_RUN` and `UNVERIFIED` are not pass. | `contract.md` result semantics and not-run table. | Review table in 12.6 evidence closure. |
| M12 services remain deterministic and side-effect free. | Recovery suite plus forbidden dependency scan tests. | Recovery pytest suite. |
| No hidden recovery / relearning / browser continuation. | Boundary coverage table plus tests and static review. | Recovery suite and review evidence. |
| No retry / replan / takeover execution. | Retry policy and conversation flow tests must prove non-execution fields and markers. | Recovery suite. |
| M12 completion cannot be declared in design package. | `review.md` records only design-package generation. | Review checklist. |

## Proposed Evidence Closure

The later evidence-closure submission should:

1. Run the M12 recovery deterministic suite.
2. Run recovery ruff checks.
3. Run `git diff --check`.
4. Inspect git status for unintended code/package or M11 history changes.
5. Record not-run / unverified surfaces.
6. Create or update the evidence report:
   `docs/testing/results/2026-05-16-m12-recovery-tests-and-evidence.md`.
7. Update `docs/iterations/m12/12.6-recovery-tests-and-evidence/review.md`.
8. Update M12 README / `m12-plan.md` only after a real completion decision.
9. Add focused tests only if a concrete coverage gap is discovered.

This design package does not create the evidence report and does not run the
recovery suite.

## Affected Surfaces

| Surface | Changed in design package? | Later evidence closure |
|---|---:|---|
| API routes | No | No route changes expected. |
| API response schema | No | No response changes expected. |
| Database schema / migration | No | No migration. |
| CLI | No | No CLI behavior change. |
| Console UI | No | No UI validation by default. |
| Conversation events | No | Evidence may review non-execution event payloads only. |
| Replay execution | No | No retry / replay execution. |
| Reporter | No | Reporter remains upstream evidence. |
| Recovery services | No code change | Existing tests prove boundaries. |
| Worker / async jobs | No | No worker validation. |
| Tests / fixtures | No in design package | Later may run existing tests or add focused tests if a gap is found. |
| Docs | Yes | 12.6 package and M12 index. |

## Evidence Data Model / Report Shape

The later report should include:

- branch and base commit;
- command table with exact command, result, exit code, and scope;
- required validation summary;
- not-run / unverified table with reason and residual risk;
- boundary coverage table for 12.1-12.5;
- finding table with severity;
- final completion decision.

Result values must be `PASS`, `FAIL`, `SKIP`, `NOT_RUN`, or `UNVERIFIED`.

## Validation Command Design

Required later recovery suite command:

```bash
cd apps/api && .venv/bin/python -m pytest \
  tests/test_recovery_classifier.py \
  tests/test_user_abort_handler.py \
  tests/test_recovery_proposal.py \
  tests/test_retry_policy.py \
  tests/test_recovery_conversation_flow.py \
  tests/test_recovery_exports.py \
  -q
```

Required later ruff command:

```bash
cd apps/api && .venv/bin/ruff check \
  app/schemas/recovery.py \
  app/services/recovery \
  tests/test_recovery_classifier.py \
  tests/test_user_abort_handler.py \
  tests/test_recovery_proposal.py \
  tests/test_retry_policy.py \
  tests/test_recovery_conversation_flow.py \
  tests/test_recovery_exports.py
```

Required later static check:

```bash
git diff --check
```

## Recovery Boundary Coverage

12.1 classifier:

- `success_no_recovery_needed`;
- `failure`;
- `blocked`;
- `uncertain`;
- `needs_review`;
- `retry_possible_requires_confirmation` is not retry execution.

12.2 abort handler:

- `accepted_stop`;
- `cannot_interrupt_inflight_action`;
- idempotent abort;
- `no_new_actions_after`;
- `inflight_caveat`.

12.3 proposal generator:

- `non_executable: Literal[True]`;
- no selected option;
- recommended is not selected;
- `unknown_input` fallback;
- proposal is not execution.

12.4 retry policy:

- `retry_allowed_requires_confirmation` is not retry started;
- `retry_denied` is safe result;
- `side_effects_unknown` is denied;
- abort boundary denied;
- selected option filtering;
- no execution fields.

12.5 conversation flow:

- response is not command;
- `chosen_option_kind` is conversation marker only;
- event payload has `execution_boundary=not_executed`;
- no retry / replan / browser continuation;
- boundary + proposal reason precision;
- shown options include evidence / risk.

## Not Run / Unverified Handling

Default not-run items must be recorded as `NOT_RUN`:

- API tests;
- CLI tests;
- UI smoke;
- E2E;
- `verify-scenario`;
- autonomous run;
- live browser continuation;
- actual retry / replan / takeover / teaching execution.

If a future task scopes any of these surfaces, that task must provide the
actual command, product surface, output, run id, screenshot, or other
reviewable evidence required by root `AGENTS.md`.

## Compatibility

12.6 does not change schema, API, DB, CLI, frontend, replay status semantics,
conversation state semantics, recovery service outputs, or product model.

## Failure / Edge Cases

- A required test fails -> `m12_blocked`.
- Required command cannot run -> `m12_blocked` or `m12_not_complete` depending
  on whether the issue is environmental or product-related.
- Evidence is missing -> `UNVERIFIED`, not pass.
- E2E / live run not scoped -> `NOT_RUN`, not pass.
- P3 / info follow-ups remain -> only `m12_completed_with_followups` is
  allowed after required validation passes.
- Any blocker / P1 / P2 remains -> no completed decision.

## Non-goals

- new recovery feature;
- retry / re-run / replan execution;
- browser continuation;
- takeover implementation;
- teaching mode;
- LearnedPath write-back;
- M11.2 Runtime Observation / Wait-for-change;
- API / CLI / DB / frontend expansion;
- autonomous exploration;
- hidden relearning;
- default E2E / UI smoke / `verify-scenario`.

## Test Matrix 入口

Detailed commands and expected evidence are defined in `test-plan.md`.

## Validation Commands for This Design Package

This design-package submission runs only docs-level checks:

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
