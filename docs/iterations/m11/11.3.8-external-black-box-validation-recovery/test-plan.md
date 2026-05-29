# Test Plan

Status: ready for review

## Test Scope

- Unit: N/A. This parent package changes documentation only.
- Integration: N/A. No runtime integration is implemented.
- API: N/A. No API contract or route is changed.
- Console UI: N/A. No UI is changed.
- E2E: N/A. No browser validation is requested or authorized for this parent package.
- Agent / Reporter / Recovery: Documentation inspection only; no product Agent behavior is executed.
- Codex / AI External Operator: Codex acts only as documentation author and shell-based docs verifier in this package.
- Live autonomous run: N/A and explicitly not run.

## Required Documentation Checks

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| docs | Parent package file set exists | `find docs/iterations/m11/11.3.8-external-black-box-validation-recovery -maxdepth 1 -type f | sort` | Shows README, intent, contract, technical-design, test-plan, acceptance, plan, review | Yes | Docs-only verification |
| docs | Parent package status sync | `rg -n "11\\.3\\.8-external-black-box-validation-recovery|状态：ready for review|ready for review / umbrella planning" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.8-external-black-box-validation-recovery/README.md` | Package README, milestone index, and milestone plan expose `ready for review` | Yes | User explicitly requested README/index sync; milestone plan is also kept aligned |
| docs | Planned child package fields | `rg -n "Package name|Status:|Type:|Goal:|Why this exists|Inputs / required reading|Allowed changes|Forbidden changes|Expected deliverables|Expected tests / verification|Compatibility constraints|Scope guardrails|Exit criteria|Handoff to next package" docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md` | Required planned-package fields are present for child packages | Yes | Review must still inspect adequacy |
| docs | Acceptance and evidence wording | `rg -n "not run|unverified|PASS|FAIL|FOLLOW_UP|BLOCKED|PV-CLI-003|external-black-box-validation-latest" docs/iterations/m11/11.3.8-external-black-box-validation-recovery` | Docs preserve evidence honesty and current failure baseline | Yes | No runtime pass claims |
| git | Scope guard | `git status --short -- docs/iterations/m11/11.3.8-external-black-box-validation-recovery docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md` | Only docs under the package, M11 index, and M11 plan changed | Yes | Runtime/test/build files must not appear |

## Commands Not Run And Why

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API/unit tests | Parent package does not change runtime or test implementation | Child code packages must run focused tests |
| `pnpm run build` / console build | No frontend files changed | Not relevant to docs-only package |
| `wagent chat` external black-box validation | Parent package is planning only; revalidation belongs to `11.3.8.5` | Latest result remains `FAIL` |
| `verify-scenario` / autonomous run | Not requested and prohibited for docs-only work | None for this parent package |
| UI smoke / browser validation | No UI changes and no live validation requested | `11.3.8.5` owns product validation |

## Blocker Recording Rule

If any required documentation check fails, keep package status below `ready for review` and record the failure in `review.md`. If runtime or test implementation files are modified, stop and revert only those changes made by this documentation task or ask for direction if unrelated changes are present.

## No Unverified Claims Rule

This package must not claim:

- code implemented;
- runtime tests passed;
- CLI behavior fixed;
- external black-box validation rerun;
- `PV-CLI-003` fixed;
- M11 status upgraded beyond the documented recovery plan.

Any such item must be written as `not run`, `not implemented`, `not verified`, or `blocked`.
