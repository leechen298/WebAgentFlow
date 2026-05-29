# 复盘 / 评审（Review）

状态：ready for review

## 2026-05-29 Documentation Authoring

- Author: Codex A, documentation author.
- Decision: ready for documentation / design review.
- Scope: created the 11.3.8.1 child package seven-doc set and synchronized milestone routing status.

## Changed Files

- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/README.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/intent.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/contract.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/technical-design.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/test-plan.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/plan.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md`

## Commands Run

- `find docs/iterations/m11/11.3.8.1-learning-action-goal-preservation -maxdepth 1 -type f | sort`
  - Result: listed the expected seven files: `README.md`, `intent.md`, `contract.md`,
    `technical-design.md`, `test-plan.md`, `plan.md`, `review.md`.
- `rg -n "Learning Action Goal Preservation|business_goal|canonical_goal|business_object|match_terms|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.1-learning-action-goal-preservation`
  - Result: found required goal-preservation, metadata, forbidden-change, and exit-criteria terms.
- `rg -n "11\\.3\\.8\\.1-learning-action-goal-preservation|ready for review" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md`
  - Result: M11 index, M11 plan, and 11.3.8 parent plan expose the child package and `ready for review` status.
- `git status --short`
  - Result: only docs changed by this task plus pre-existing untracked `.agent-runs/`; no runtime / schema / API / frontend / fixture / migration / test implementation files changed.
- `git diff --check`
  - Result: clean.

## Test Results

Documentation checks passed. Runtime tests are not run because this task is documentation-only and no runtime files are modified.

## Compatibility Review

- No public API, DB schema, CLI command, frontend UI, replay status, reporter, recovery, abort, or Agent role changes were made.
- The package contract requires optional, backward-compatible session metadata only after review.
- Existing M11 closeout and external black-box latest `FAIL` result remain unchanged.

## Scope Review

- Runtime, schema, API, frontend, fixture, migration, and test implementation files were not modified.
- No external Validation-Site / Fixture-Site files were modified.
- No `verify-scenario`, autonomous run, direct autonomous endpoint call, browser smoke, or WAgent product validation was run.

## Unresolved Findings

- P1: None known.
- P2: None known.
- P3: Implementation may discover that intake action metadata is not available at the exact learning result boundary; the contract records this as a blocker condition.

## Final Assessment

Ready for documentation / design review. Not ready for implementation until review explicitly approves the package and updates status.

## 2026-05-29 Documentation Revision

- Author: Codex A, documentation revision agent.
- Trigger: docs review at `.agent-runs/20260529-112710-m11-11.3.8.1-learning-action-goal-preservation/docs-review.md`.
- Scope: P0/P1 review findings only.
- Decision: addressed the P1 procedural blocker by adding `.agent-runs/` to `.gitignore` so local agent-run coordination / review artifacts no longer appear as untracked worktree changes during future documentation reviews.

### Revision Changed Files

- `.gitignore`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md`

### Review Finding Response

| Finding | Priority | Response | Status |
|---|---|---|---|
| Untracked `.agent-runs/` made the worktree unclean before review | P1 | Added `.agent-runs/` to `.gitignore`; after the edit, `git status --short --branch` reports only tracked revision changes and no untracked `.agent-runs/` entry | Addressed |

### Revision Commands

| Command | Result | Exit code | Notes |
|---|---|---|---|
| `git status --short --branch` | Before revision: branch `v0.1-local` with untracked `.agent-runs/`; after revision: only tracked `.gitignore` and package `review.md` edits | 0 | Worktree hygiene check |
| `git check-ignore -v .agent-runs .agent-runs/20260529-112710-m11-11.3.8.1-learning-action-goal-preservation/docs-review.md` | `.gitignore` now ignores `.agent-runs/` and nested review artifacts | 0 | Procedural P1 check |
| `git diff --check` | Clean | 0 | Whitespace check |

### Revision Compatibility / Scope Review

- No runtime, schema, API, frontend, fixture, migration, worker, prompt, or test implementation files were modified.
- No package scope was broadened.
- No status was promoted to `ready_for_implementation`; the package remains `ready for review` until documentation / design review explicitly passes.
- No `verify-scenario`, autonomous run, direct autonomous endpoint call, browser smoke, CLI product validation, or external black-box validation was run.

### Remaining Findings / Risks

- P0: None known.
- P1: None known after ignoring `.agent-runs/`.
- P2/P3: Deferred unless raised by the next documentation / design review.

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `find docs/iterations/m11/11.3.8.1-learning-action-goal-preservation -maxdepth 1 -type f \| sort` | Seven package docs exist | Listed all seven expected package docs | 0 | Pass | terminal output | Documentation-only |
| `rg -n "Learning Action Goal Preservation\|business_goal\|canonical_goal\|business_object\|match_terms\|Forbidden Changes\|Exit Criteria" docs/iterations/m11/11.3.8.1-learning-action-goal-preservation` | Required review terms present | Required terms found across README, contract, technical design, test plan, and plan | 0 | Pass | terminal output | Documentation-only |
| `rg -n "11\\.3\\.8\\.1-learning-action-goal-preservation\|ready for review" docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md` | Milestone / parent status sync present | M11 index, M11 plan, and parent plan show child status `ready for review` | 0 | Pass | terminal output | Documentation-only |
| `git status --short` | Only allowed docs changed | Shows package docs, M11 index, M11 plan, parent plan; pre-existing `.agent-runs/` remains untracked | 0 | Pass | terminal output | Scope check |
| `git diff --check` | No whitespace errors | Clean | 0 | Pass | terminal output | Docs check |

## Not Run / Unverified

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API/unit tests | No runtime code changed in this documentation task | Implementation package must run focused tests |
| CLI / `wagent chat` | No product validation requested or authorized | 11.3.8.5 owns external revalidation |
| UI smoke / browser validation | No UI changes | None for docs authoring |
| `verify-scenario` / autonomous run | Prohibited for docs-only work unless explicitly requested | None |
| External black-box validation | Later package responsibility | Latest result remains `FAIL` |

## 2026-05-29 Implementation

- Author: Codex C, implementation agent.
- Decision: implementation complete for this child package scope; follow-up packages still own reusable utterance generation, matcher consumption, cross-chain regression, and external black-box revalidation.
- Scope: preserved learning action business identity metadata in the learning result and session learned action record without changing matcher, replay, reporter, recovery, routes, frontend, migrations, worker code, fixture sites, or external validation result docs.

## Implementation Changed Files

- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md`

## Implementation Summary

- Added optional internal `LearningRunRequest` / `LearningRunResult` identity fields: `action_goal`, `canonical_goal`, `action_aliases`, `business_goal`, `business_object`, and `match_terms`.
- Built deterministic, target-agnostic identity terms from structured action metadata, with de-duplication and slot-value exclusion.
- Preserved intake-derived identity in `session.metadata_json.learned_actions[]` when learning handlers return only a generic learning wrapper label.
- Kept `_matching_actions()` unchanged; this package only stores metadata for later matcher work.

## Implementation Commands

| Command | Result | Exit code | Notes |
|---|---|---:|---|
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q` | `9 passed in 0.08s` | 0 | Required T1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q` | `85 passed in 0.81s` | 0 | Required T2 |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py` | `All checks passed!` | 0 | Required T5 |
| `rg -n "5177\|inventory item\|data-testid\|WebAgentFlow-Validation-Site" apps/api/app apps/api/tests` | Found existing historical `data-testid` occurrences in tests and `autonomous_explorer.py`; no `5177`, `inventory item`, or `WebAgentFlow-Validation-Site` introduced by this package | 0 | Required T4 scope scan plus diff inspection |
| `rg -n "5177\|inventory item\|data-testid\|WebAgentFlow-Validation-Site" apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py` | Found pre-existing `data-testid` test fixture lines in the two changed test files; implementation diff added no forbidden target constants | 0 | Changed-file scope scan |
| `git diff --check` | Clean | 0 | Required T6 |

## Implementation Compatibility / Scope Review

- Existing Chinese `登录` / `创建记录` learning expectations remain covered by the focused tests.
- Existing learned action records without the new optional metadata remain valid.
- No matcher confidence, candidate selection, replay execution, Task Result Reporter, recovery, abort, public route, DB schema, frontend, fixture, or worker behavior was changed.
- No external black-box validation, `verify-scenario`, autonomous run, direct autonomous endpoint call, CLI product smoke, UI smoke, or browser validation was run.

## Implementation Unresolved Limits

- `PV-CLI-003` is not claimed fixed or verified by this package.
- Suggested utterance quality remains unchanged and belongs to `11.3.8.2`.
- Matcher consumption of `business_goal` / `canonical_goal` / `match_terms` remains for `11.3.8.3`.
