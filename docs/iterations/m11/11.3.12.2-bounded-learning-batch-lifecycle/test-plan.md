# Test Plan

状态：executed_repo_local

## Test Scope

This package requires `test-plan.md` because it changes database schema, service lifecycle, conversation
events, cancellation / timeout semantics, evidence summary, and compatibility behavior.

No live autonomous validation is authorized by this child package.

## Unit Tests

### LearningBatch repository

File: `apps/api/tests/test_learning_batches_repo.py`

Required cases:

- create pending batch with policy / request JSON and default empty arrays;
- mark running with page identity and planned scenarios;
- append run / capability / LearnedPath ids while non-terminal;
- reject appending ids after terminal `cancelled`;
- request cancellation sets `cancel_requested_at` and non-terminal status;
- terminal status writes `completed_at` exactly once;
- list batches by `session_id` and `status`.

### BoundedLearningPolicy

File: `apps/api/tests/test_bounded_learning_batch_lifecycle.py`

Required cases:

- default policy has version and finite budget values;
- scenario planner truncates to `max_scenario_count`;
- all-supported smoke scenario is disabled by default unless policy allows it;
- dependency pairs are included only when policy and candidate metadata allow them;
- repeated failures per adapter stop future attempts for that adapter;
- consecutive no-new-capability threshold stops planning / execution.

### Status derivation

Required cases:

- all planned scenarios passed -> `completed`;
- passed + failed / unsupported -> `partial_success`;
- only unverified -> `unverified`;
- timeout before any useful asset -> `timed_out`;
- timeout after useful asset -> `partial_success`;
- cancellation before useful asset -> `cancelled`;
- cancellation after useful asset -> `partial_success`;
- no supported scenarios -> `failed`.

## Integration Tests

### LearningRunService capability discovery

File: `apps/api/tests/test_learning_run_service.py` or
`apps/api/tests/test_bounded_learning_batch_lifecycle.py`

Required cases:

- URL-only product learning creates a `LearningBatch` and returns `learning_batch_id`;
- scenario `ExplorationRun.strategy_json` includes `learning_batch_id`;
- passed atomic capability scenarios persist `LearnedCapability` rows when action/evidence schemas are safe;
- compatibility `learned_path_ids` still appear for current chat behavior;
- failed / unsupported / unsafe capability payloads appear in batch summary and are not advertised as passed;
- batch status is terminal before `LearningRunResult` is returned;
- fake clock timeout stops before running scenarios beyond budget;
- cancellation hook stops before next scenario and prevents post-cancel asset attachment.

### Conversation runtime

File: `apps/api/tests/test_conversation_chat_runtime.py`

Required cases:

- learning success event includes `learning_batch_id`, `learning_batch_status`, and sanitized summary;
- learning partial-success feedback includes learned and not-learned counts;
- learning failed / unverified response includes batch status and clears `active_task`;
- cancel text after a stale learning active task uses existing runtime-context cleanup and does not leave stale
  `active_task.status=learning`;
- in-flight synchronous batch cancellation is tested at service/controller level through fake
  `cancel_checker` / repository `request_cancel()`, not as a real CLI Ctrl+C product claim;
- user-facing learned action labels do not become control text such as "开始学习" or "取消".

## Regression Tests

Run existing compatibility suites:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v
```

Expected: no old LearnedPath, learning service, or chat runtime regression. If broad suites fail from
pre-existing unrelated tests, run the scoped files above and record the exact unrelated failures.

## Migration Verification

Required:

```bash
pnpm run db:migrate:api
```

If local script or DB environment fails, run direct Alembic fallback and record exact output:

```bash
cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head
cd apps/api && ../../.venv/bin/python -m alembic -c alembic.ini upgrade head --sql
```

Online migration must not be claimed as passed unless the online command exits 0.

## Static Checks

Run scoped ruff over changed files:

```bash
uv run ruff check apps/api/app/models/learning_batch.py apps/api/app/repos/learning_batches_repo.py apps/api/app/schemas/learning_batch.py apps/api/app/services/learning/bounded_learning.py apps/api/app/services/learning/learning_batch_controller.py apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_batches_repo.py apps/api/tests/test_bounded_learning_batch_lifecycle.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/alembic/versions/20260605_0002_add_learning_batches.py
```

Run hardcoding scan:

```bash
rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app
```

Expected: no new runtime target hardcoding. Explain existing generic false positives.

## E2E / UI Smoke Boundary

No E2E / UI smoke is authorized in this child package. Unit / integration tests with fake runtime factories are
allowed. Do not claim browser validation without real browser evidence.

## Live Validation Boundary

Not authorized:

- `verify-scenario`
- product UI autonomous run
- direct `/exploration/autonomous-runs` calls
- `wagent chat` live learning against a target site

Future live validation requires explicit user approval and must record API base URL, target URL, DB state
policy, scenario list, `learning_batch_id`, run ids, capability ids, LearnedPath ids, pass gate / terminal /
ingest summaries, and stable redacted result docs.

## Acceptance Gates

Implementation may close only if:

- required unit / integration tests pass;
- scoped ruff passes or unrelated failures are recorded truthfully;
- migration is verified online or online failure is recorded with offline SQL evidence;
- compatibility suites pass for LearnedCapability, LearnedPath, learning service, and chat runtime;
- hardcoding scan is reviewed;
- no unresolved P0 / P1 design, code, evidence, or scope finding remains;
- `review.md` records commands run and commands not run.
