# Review

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
parent_package: 11.3.12-bounded-learning-composable-capability-assets
implementation_authorized: yes
next_action: Do not extend this child. Parent campaign is responsible for final closeout and any future validation route.
blocking_findings: none
last_verified_at: 2026-06-06
commands_run: source inspection; parent design review; child design review; document generation; targeted pytest; LearnedPath regression pytest; scoped ruff; hardcoding scan; Alembic offline SQL generation; code-review subagent closeout; limited `git diff --check`; trailing-whitespace scan
commands_not_run: online DB migration pass, live autonomous validation, `verify-scenario`, `wagent chat`

## Design Review

- Reviewer: Codex parent + subagent read-only review
- Decision: approved_for_implementation
- Notes:
  - This child narrows 11.3.12 to the asset foundation only.
  - Initial child review found one P1: migration verification was missing from `test-plan.md`.
  - P1 was fixed by adding required Alembic migration verification via `pnpm run db:migrate:api`
    or direct Alembic fallback with exact failure recording.
  - No unresolved P0 / P1 findings remain for this child.

## Actual Delivery

- Created seven-document child package for 11.3.12.1.
- Scoped Phase 1 to `LearnedCapability` schema / model / repo / migration / compatibility foundation.
- Deferred batch lifecycle, bounded planner, Page Understanding hints, runtime composition, CLI, and Console UI.
- Added `LearnedCapability` ORM and Alembic migration for `learned_capabilities`.
- Added `LearnedCapabilityRepository` with stable dedup, idempotent ingest, list, lookup, and trust transition helpers.
- Added Pydantic summary/detail schemas that redact debug evidence and internal source path ids from normal projection.
- Added repo/schema tests for ingest, invalid capability rejection, required action/evidence keys,
  dedup, trust, FK `SET NULL`, list filtering, schema redaction, source path id projection hiding, server defaults, metadata
  registration, and ORM fetch.
- Preserved existing LearnedPath model/repo/schema/API behavior; no HTTP LearnedCapability API was added.

## Changed Files

- `apps/api/app/models/learned_capability.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/repos/learned_capabilities_repo.py`
- `apps/api/app/schemas/learned_capability.py`
- `apps/api/alembic/versions/20260605_0001_add_learned_capabilities.py`
- `apps/api/tests/test_learned_capabilities_repo.py`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/README.md`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/plan.md`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/review.md`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/GOAL_RUNNER.md`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/CURRENT_STATE.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/README.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/intent.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/contract.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/technical-design.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/test-plan.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/plan.md`
- `docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation/review.md`
- `docs/iterations/m11/README.md`

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| Source inspection | Existing LearnedPath and migration patterns understood | Completed | 0 | pass | local file reads | No runtime execution |
| Child design review | Decide implementation authorization | Completed after P1 fix | 0 | pass | Codex subagent review + local follow-up | Authorized only this child |
| `git diff --check -- docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets docs/iterations/m11/11.3.12.1-learned-capability-asset-foundation docs/iterations/m11/README.md` | No whitespace errors in tracked diffs | Passed | 0 | limited pass | command output | `git diff` does not cover untracked new files until added to index |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py -v` | LearnedCapability repo/schema tests pass | 18 passed | 0 | pass | command output | Targeted child tests, including nested forbidden action payload rejection and source LearnedPath id projection hiding |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v` | LearnedPath compatibility holds | 64 passed | 0 | pass | command output | Regression tests |
| `uv run ruff check apps/api/app/models/learned_capability.py apps/api/app/repos/learned_capabilities_repo.py apps/api/app/schemas/learned_capability.py apps/api/tests/test_learned_capabilities_repo.py apps/api/alembic/versions/20260605_0001_add_learned_capabilities.py` | New/changed package files pass ruff | Passed | 0 | pass | command output | Scoped ruff |
| `uv run ruff check apps/api/app apps/api/tests` | Whole API ruff passes | Failed | 1 | fail | command output | Existing unrelated lint failures in execution runtime, conversation intake, page analyzer, page verification, structure integrity, and supervisor observation tests; scoped ruff for new package files passes |
| `rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app` | No new runtime hardcoding | Existing generic hits only | 0 | pass | command output | Existing `autonomous_explorer.py` data-testid collection plus new schema redaction blocklist entry for `data-testid`; no target route/label/fixture value hardcoding |
| `pnpm run db:migrate:api` | Online Alembic migration runs | Failed before DB connection | 126 | fail | command output | Root `.venv/bin/alembic` shebang points to stale `/Users/leechen/projects/WebAgentFlow/.venv/bin/python3.11` |
| `cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head` | Online Alembic migration runs | Failed on Postgres connection | 1 | unverified | command output | Local/sandbox Postgres connection to 127.0.0.1:5432 not permitted/reachable |
| `cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head --sql` | Alembic chain and SQL generation work | Passed; generated SQL through `20260605_0001` | 0 | pass | command output | Offline migration verification only |
| `git diff --check -- <scoped files>` | No whitespace errors in tracked diffs | Passed | 0 | limited pass | command output | `git diff` does not cover untracked new files until added to index |
| `rg -n '[[:blank:]]+$' <scoped child code/docs files>` | No trailing whitespace in scoped files | No matches | 1 | pass | command output | `rg` exit 1 means no matches |
| `wagent chat` | Not authorized | Not run | N/A | skip | N/A | No live validation |
| `verify-scenario` | Not authorized | Not run | N/A | skip | N/A | No live validation |

## Not Run / Unverified

| Item | Reason | Follow-up |
|---|---|---|
| Online DB migration | Local `pnpm` script has stale venv shebang; direct Alembic cannot connect to Postgres from current sandbox | Offline SQL generation passed; rerun online migration after local DB / venv path is repaired |
| LearnedCapability HTTP API | Out of scope for this child | Future debug/API child may add read-only routes |
| Live validation | Not authorized for this child | Requires explicit future approval |

## Compatibility Review

- Existing LearnedPath ORM/repo/API tests passed: 64/64.
- No LearnedPath model, schema, repo, router, replay, CLI, Console, chat timeout, batch lifecycle, bounded planner, or composition files were edited by this child.
- `learned_capabilities` uses nullable FK `SET NULL` for both source run and source LearnedPath.

## Scope Review

- In scope: LearnedCapability table, ORM, repo, schemas, tests, docs, parent routing.
- Out of scope and not implemented: HTTP API routes, learning batch lifecycle, bounded planner, Page Understanding hints, runtime composition, `wagent chat`, replay behavior, live autonomous validation.

## Code Review Findings

- P1 redaction leak: fixed by recursive redaction of `debug`, raw DOM / HTML / selector, selector,
  `target_selector`, `data-testid`, `terminal_detail`, `evidence_targets`, `path_id`, and
  `learned_path_id` style keys in normal evidence and detail payload projections. Final closeout also
  hides top-level `source_learned_path_id` from summary/detail projections while preserving it on the ORM row.
- P2 DB defaults: fixed by adding ORM and Alembic server defaults for `query_signature`, `provenance`,
  and `trust`.
- P2 invalid stored rows: fixed by validating allowed `capability_kind` and required
  `action_schema_json` / `evidence_json` keys before ingest.
- P2 direct action payload storage: fixed by recursively rejecting exact and token-style forbidden action
  keys for direct Playwright / LLM / replay / execution payloads, including nested `llm_payload` and
  `replay` keys.

## Final Delta

`11.3.12.1` is complete for repo-local implementation. Online migration remains unverified due local environment / sandbox connectivity, but migration syntax and chain were verified by offline SQL generation.
