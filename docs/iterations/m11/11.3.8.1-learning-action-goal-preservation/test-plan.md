# 测试计划（Test Plan）

状态：ready for review

## Test Scope

- Unit: focused learning label / metadata construction tests.
- Integration: focused chat runtime service tests that persist session learned action metadata.
- API: N/A; no public route changes planned.
- Console UI: N/A; no UI changes.
- E2E: N/A for this package.
- Agent / Reporter / Recovery: no Agent verdict, reporter, recovery, abort, or retry behavior is executed.
- Codex / AI External Operator: documentation author only for this package; implementation Agent may run shell commands and record outputs.
- Live autonomous run: explicitly not run in this package.

## Test Matrix

| ID | Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|---|
| D1 | docs | Seven-doc package exists | `find docs/iterations/m11/11.3.8.1-learning-action-goal-preservation -maxdepth 1 -type f | sort` | Shows README, intent, contract, technical-design, test-plan, plan, review | Yes | Documentation stage |
| D2 | docs | Required terms and gates present | `rg -n "Learning Action Goal Preservation|business_goal|canonical_goal|business_object|match_terms|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.1-learning-action-goal-preservation` | Finds contract/design/testable gate terms | Yes | Documentation stage |
| D3 | docs | Milestone index sync | `rg -n "11\\.3\\.8\\.1-learning-action-goal-preservation|ready for review" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md` | M11 index and 11.3.8 plan show child package review-ready status | Yes | Documentation stage |
| T1 | unit | Product learning preserves English business identity | `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q` | Added / existing tests pass; result metadata preserves business goal / canonical goal / aliases and excludes slot values | Yes after implementation | No external site dependency |
| T2 | service | Chat runtime stores preserved identity in session action | `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q` | Added / existing tests pass; `metadata_json.learned_actions[]` contains optional business identity fields | Yes after implementation | Matching behavior not required here |
| T3 | regression | Existing intake behavior remains compatible if touched | `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_intake.py -q` | Existing tests pass | Conditional | Required only if intake files change |
| T4 | lint/scope | Runtime and tests avoid forbidden target constants | `rg -n "5177|inventory item|data-testid|WebAgentFlow-Validation-Site" apps/api/app apps/api/tests` plus review inspection | No new target-specific runtime / prompt constants; historical docs/tests may be explained | Yes after implementation | Prefer targeted changed-file scan in review |
| T5 | lint | Changed Python files are lint-clean | `cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py` | Ruff passes | Yes after implementation | Adjust file list if design-approved files differ |
| T6 | git | Whitespace check | `git diff --check` | Clean | Yes | Documentation and implementation stages |

## Commands Not Run And Why

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API full test suite | Not required for documentation authoring; implementation may run focused tests first | Later implementation review can request broader suite if blast radius grows |
| Console build / UI smoke | No frontend changes planned | None for this package |
| `wagent chat` external black-box validation | Revalidation belongs to `11.3.8.5` after 11.3.8.1-11.3.8.4 finish | Latest result remains `FAIL` |
| `verify-scenario` / autonomous run | Not requested and prohibited for docs-only authoring | None |
| Direct autonomous-run endpoint | Forbidden by repository rules | Must never be used as product validation evidence |

## E2E / UI Smoke Boundary

This package must not claim E2E, UI smoke, CLI product validation, or external black-box validation unless a later reviewed scope explicitly changes that and records product-surface evidence. Focused pytest output is not a product pass.

## Codex / AI External Operator Boundary

Codex may run shell commands for docs and focused tests. Codex must not pretend to be the Supervisor Agent, Task Path Planner, Task Result Reporter, or any internal WebAgentFlow role. If no `run_id`, screenshot, raw CLI output, or artifact exists, the corresponding live result must be marked `not run` / `unverified`.

## Live Run Boundary

No `verify-scenario`, autonomous run, direct `/exploration/autonomous-runs`, or product-driven browser execution is part of this package.

## Blocker Recording Rule

If preserving business identity requires a public API change, DB migration, target-specific constants, or matcher policy change, stop implementation and update `contract.md` / `technical-design.md` for review before coding further.

## No Unverified Claims Rule

Do not claim:

- `PV-CLI-003` fixed;
- external black-box validation passed;
- end-to-end learn-then-execute passed;
- matcher improvement completed;
- suggested utterance generation fixed.

Those claims belong to later packages only after their own evidence exists.

