# Technical Design

Status: ready for review

## Current State

The package already has an umbrella `README.md`, `intent.md`, `acceptance.md`, and `plan.md`. The plan decomposes the external black-box validation recovery into five child packages and includes planned-package fields for each child.

The recorded baseline is:

- `docs/testing/results/external-black-box-validation-latest.md` reports overall `FAIL`.
- `docs/testing/results/pv-cli-003-failure-triage-20260525.md` classifies the failure as generic learning action label, lost business object, and literal matching.
- `docs/iterations/m11/README.md` already lists 11.3.8 as proposed umbrella planning.

## Documentation Structure

The parent package uses a full documentation set even though it is docs-only, because it affects package sequencing, validation behavior, evidence boundaries, and automation-consumption instructions.

Files:

- `README.md` - index, status, scope, deliverables, child sequence.
- `intent.md` - problem and product purpose.
- `contract.md` - allowed/forbidden changes, compatibility, evidence rules.
- `technical-design.md` - this documentation design and anti-drift structure.
- `test-plan.md` - exact documentation verification commands and not-run rules.
- `acceptance.md` - acceptance gates spanning functional, safety, test, and docs criteria.
- `plan.md` - execution-grade child package specifications.
- `review.md` - current authoring result and verification record.

## Affected Files

Changed by this docs package:

- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/README.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/contract.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/technical-design.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/test-plan.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`
- `docs/iterations/m11/README.md`

Read-only inputs:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `docs/product-model.md`
- `docs/testing/external-black-box-validation-plan.md`
- `docs/testing/results/external-black-box-validation-latest.md`
- `docs/testing/results/pv-cli-003-failure-triage-20260525.md`

## Control Flow

Future work must follow this sequence:

1. Review this parent umbrella package.
2. Create the next child package `11.3.8.1-learning-action-goal-preservation` with full seven-doc set.
3. Review the child contract, technical design, test plan, and plan.
4. Only then implement the child package.
5. Repeat for `11.3.8.2` through `11.3.8.5`.

No implementation Agent may treat the parent `plan.md` as direct authorization to edit runtime or tests.

## Compatibility Strategy

The parent docs preserve existing M11 closeout semantics: 11.3.7 remains passed for its first-wave user-facing behavior gates, while external black-box validation remains failed until rerun. The parent package does not rewrite historical eval status or product runtime status.

`11.3.8.5` is the only planned child allowed to update external black-box latest results, and only after actual current-session validation evidence exists.

## Anti-drift Rules

- Keep the external target as operator-provided validation input, never a product default.
- Keep target details out of runtime, prompts, and active default evals.
- Keep `PASS`, `FAIL`, `FOLLOW_UP`, `BLOCKED`, and `UNVERIFIED` tied to recorded evidence.
- Keep parent and child responsibilities separate: parent plans, child packages implement or validate.
- Keep M12 recovery out of 11.3.8 unless roadmap/product documents are updated first.

## Test Matrix

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| File completeness | Parent package has required docs for a sequencing/evidence planning package | `test-plan.md` documentation checks |
| Planned package fields | Each child package has execution-grade planned-package fields | `rg` checks plus review inspection |
| Status sync | Package README and M11 index both say `ready for review` | `rg` checks |
| Evidence honesty | Docs state runtime/live validation was not run | `review.md` and `test-plan.md` checks |
| Boundary preservation | Runtime/test/fixture files are not modified | `git diff --name-only` inspection |

## Validation Commands

```bash
find docs/iterations/m11/11.3.8-external-black-box-validation-recovery -maxdepth 1 -type f | sort
rg -n "Status: ready for review|状态：ready for review|Package name|Forbidden changes|Compatibility constraints|Scope guardrails|Exit criteria|Handoff to next package" docs/iterations/m11/11.3.8-external-black-box-validation-recovery docs/iterations/m11/README.md
git status --short -- docs/iterations/m11/11.3.8-external-black-box-validation-recovery docs/iterations/m11/README.md
```
