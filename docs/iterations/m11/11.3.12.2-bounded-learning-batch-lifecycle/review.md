# Review

状态：complete

## FINAL_STATUS

status: PACKAGE_COMPLETE
parent_package: 11.3.12-bounded-learning-composable-capability-assets
active_child_package: 11.3.12.2-bounded-learning-batch-lifecycle
implementation_authorized: yes
do_not_start_next_package: true
blocking_findings: none
last_verified_at: 2026-06-06
commands_run: source inspection; interrupted-state audit; read-only design review; implementation audit; targeted pytest; compatibility pytest; scoped ruff; hardcoding scan; Alembic offline SQL generation
commands_not_run: online DB migration pass, live validation, `verify-scenario`, `wagent chat`, UI smoke
next_action: Do not extend this child. Route parent to 11.3.12.3 package generation only after reviewing this closeout.

## 2026-06-06 Code Review Handoff Fixes

- Fixed P1 batch exception closeout: after a `LearningBatch` is created, seed analysis,
  scenario planning, scenario explorer, or run persistence exceptions now close the batch
  to a terminal status and return `learning_batch_id`, `learning_batch_status`, and
  `learning_batch_summary` to the caller.
- Fixed P2 cross-session cancellation: `boundary_state()` refreshes the batch row, and
  `mark_running()` no longer overwrites `cancel_requested`.
- Fixed P2 `LearningBatchDetail` planned scenario redaction for `fill_values`,
  `toggle_values`, and binding sample `value` fields.
- Fixed P3 repository pagination for `LearningBatchRepository.list_for_session()` by
  pushing cursor and `limit + 1` into SQL.
- Verification: 164 scoped pytest passed, scoped ruff passed, hardcoding scan reviewed.

## Design Review

- Reviewer: Codex subagents `Boyle` and `Locke`
- Decision: approved
- Notes:
  - This child consumes 11.3.12.1 asset foundation.
  - Runtime implementation is not authorized until design review completes.
  - P1: cancellation-after-success status priority was contradictory. Fixed by making cancellation /
    timeout after useful assets derive `partial_success`, and cancellation before useful assets derive
    `cancelled`.
  - P1: synchronous v1 lacked an implementation-grade product cancel signal path. Fixed by narrowing v1
    cancellation to controller/repository fake-hook coverage and explicitly not claiming CLI Ctrl+C can
    cancel an already-running backend batch.
  - P2 follow-ups recorded in design: `LearningRunResult` batch fields must have compatibility defaults;
    LearnedCapability ingest requires strict target-agnostic mapping; failed / unverified terminal batch
    results must deliberately clear active task.
  - Re-review found no remaining P0 / P1 documentation-quality or code-feasibility findings.

## Actual Delivery

- Created seven-document child package for `11.3.12.2-bounded-learning-batch-lifecycle`.
- Defined `BoundedLearningPolicy`, `LearningBatch`, terminal statuses, cancel / timeout / detach boundary,
  evidence summary, compatibility, and no-live-validation scope.
- Added `LearningBatch` ORM, repository, Pydantic projections, Alembic migration, bounded policy helpers,
  and `LearningBatchController`.
- Integrated URL-only capability discovery with durable batch creation, safe-boundary cancel / timeout checks,
  bounded scenario policy, terminal closeout, `learning_batch_id` strategy metadata, LearnedCapability ingest,
  and compatibility LearnedPath writes.
- Integrated chat runtime with `session_id` handoff to the learning handler, batch id / status / summary event
  metadata, failed / unverified batch reporting, and active task clearing for terminal synchronous results.
- During interrupted-state audit, found that `should_stop_after_attempt()` was only covered as a helper and not
  wired into `LearningRunService`; fixed service-level bounded stop for adapter failures and consecutive
  no-new-capability attempts, with focused regression coverage.
- During code-audit subagent review, fixed additional P1s: default policy no longer plans dependency-pair
  probes, post-scenario timeout / cancel is observed before batch closeout, and rejected LearnedCapability
  ingest no longer counts as a passed scenario.

## Changed Files

- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/README.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/intent.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/contract.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/technical-design.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/test-plan.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/plan.md`
- `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle/review.md`
- `apps/api/app/models/learning_batch.py`
- `apps/api/app/repos/learning_batches_repo.py`
- `apps/api/app/schemas/learning_batch.py`
- `apps/api/app/services/learning/bounded_learning.py`
- `apps/api/app/services/learning/learning_batch_controller.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/alembic/versions/20260605_0002_add_learning_batches.py`
- `apps/api/tests/test_learning_batches_repo.py`
- `apps/api/tests/test_bounded_learning_batch_lifecycle.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `docs/iterations/m11/11.3.12-bounded-learning-composable-capability-assets/CURRENT_STATE.md`
- `docs/iterations/m11/README.md`

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| Source inspection | Existing batch/discovery/chat shape understood | Completed | 0 | pass | local file reads | No runtime execution |
| Design review | Independent review approves or requests changes | Approved after P1 fixes and re-review | N/A | pass | subagent review output | No remaining P0 / P1; implementation authorized |
| Interrupted-state audit | Determine whether implementation was partial, unauthorized, or complete | Found parent/child status conflict plus real implementation gap; fixed bounded stop wiring | 0 | pass | local diff review + subagent audit | Parent `CURRENT_STATE.md` synchronized after closeout |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_batches_repo.py tests/test_bounded_learning_batch_lifecycle.py -v` | repo / policy / controller tests pass | 18 passed | 0 | pass | command output | Initially found pagination nondeterminism; fixed test determinism |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v` | learning service and chat runtime integration pass | 119 passed | 0 | pass | command output | Initially found old tests missing expected `session_id`; fixed expectations |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v` | LearnedCapability / LearnedPath compatibility holds | 82 passed | 0 | pass | command output | Compatibility regression |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_batches_repo.py tests/test_bounded_learning_batch_lifecycle.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v` | combined focused 11.3.12.2 suites pass after bounded stop wiring and code-audit fixes | 140 passed | 0 | pass | command output | Includes service-level bounded stop, post-scenario timeout, and rejected-ingest coverage |
| scoped `uv run ruff check ...` from `test-plan.md` | changed 11.3.12.2 files pass ruff | All checks passed | 0 | pass | command output | Ran after import/line-length cleanup |
| `rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app` | no runtime target hardcoding | Only generic `data-testid` collection/redaction hits | 0 | pass | command output | No `/users`, Alice/Bob, validation-site, or user-management example wording in runtime |
| `pnpm run db:migrate:api` | online migration runs | Failed before DB connection | 126 | fail | command output | `.venv/bin/alembic` shebang points to stale `/Users/leechen/projects/WebAgentFlow/.venv/bin/python3.11` |
| `cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head` | online migration runs | Failed on Postgres connection | 1 | unverified | command output | Local/sandbox Postgres connection to localhost/127.0.0.1:5432 not permitted/reachable |
| `cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head --sql` | Alembic chain and SQL generation work | Passed; generated SQL through `20260605_0002` | 0 | pass | command output | Offline migration verification only |
| Live validation | Not authorized | Not run | N/A | skip | N/A | No `verify-scenario`, no autonomous run |

## Not Run / Unverified

| Item | Reason | Follow-up |
|---|---|---|
| Online DB migration | Local stale venv shebang and DB connectivity prevented online pass | Offline SQL generation passed; rerun online migration after venv/DB are repaired |
| Live validation | Not authorized for this child | Requires explicit future approval |
| `wagent chat` | Live product run not authorized for this child | Future live validation requires the parent runner inputs |
| UI smoke / Console | Out of scope for this child | Do not claim UI validation |

## Compatibility Review

- Existing LearnedCapability / LearnedPath / exploration API compatibility suites passed: 82/82.
- Existing `LearningRunResult` fields remain populated while new batch fields default compatibly.
- Old `ExplorationRun.strategy_json` rows without `learning_batch_id` remain valid; new capability-discovery
  scenario rows include `learning_batch_id`.
- Existing chat learned-action behavior remains compatible while learning completed / failed events now include
  batch metadata.

## Scope Review

- In scope: batch lifecycle docs/design, LearningBatch table/repo/schema/controller, bounded policy,
  LearningRunService batch integration, chat batch metadata, focused tests.
- Out of scope and not implemented by this child: Page Understanding hints, capability composition runtime,
  Console UI batch detail, async worker queue, progress streaming API, live validation.
- Current working tree contains broader 11.3.10 / 11.3.11 / Console / terminal-hints changes from earlier
  interrupted work. Those files are not claimed as 11.3.12.2 delivery and must be reviewed separately before
  any scoped commit.

## Code Review Findings

- P1 status conflict: fixed by synchronizing child status and parent `CURRENT_STATE.md`; parent now routes to
  planned 11.3.12.3 instead of design-review-pending 11.3.12.2.
- P1 bounded stop not wired into service loop: fixed by calling `should_stop_after_attempt()` after each
  scenario and recording `bounded_policy_stop` plus skipped count in batch summary.
- P1 default policy allowed dependency pairs: fixed by defaulting `allow_dependency_pairs` to `False`; pairwise
  probes now require explicit policy opt-in.
- P1 cancel / timeout after a scenario run was missed: fixed by checking batch boundary again after each
  scenario result is processed and before batch closeout.
- P1 rejected LearnedCapability ingest counted as passed: fixed so zero accepted capability rows keeps
  compatibility LearnedPath evidence durable but does not advertise a passed capability or returned
  `learned_path_ids`.
- P2 durable summary lacked scenario evidence: fixed by storing failed / unverified / unsupported summaries in
  `learning_batches.summary_json`.
- P2 runtime feedback included user-management examples: fixed by generating next-step examples from the
  actual learned capability label.
- P2 pagination nondeterminism in `LearningBatchRepository` test: fixed by making test timestamps explicit.
- P2 old chat tests did not account for required `session_id` handoff: fixed expectations to assert the new
  contract.

## Final Delta

`11.3.12.2` is complete for repo-local implementation. Online migration remains unverified due local
environment / sandbox connectivity, but migration syntax and chain were verified by offline SQL generation.
