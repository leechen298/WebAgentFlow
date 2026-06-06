# Implementation Plan

状态：executed

## Inputs

- parent `11.3.12-bounded-learning-composable-capability-assets/GOAL_RUNNER.md`
- parent `CURRENT_STATE.md`
- parent `contract.md`
- parent `technical-design.md`
- parent `plan.md`
- `11.3.12.1-learned-capability-asset-foundation/review.md`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`

## Documentation Generation Plan

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.12.2-bounded-learning-batch-lifecycle` |
| Package type | `mixed / code-gated child package` |
| Parent / child route | Parent `11.3.12`; child `11.3.12.2`; follows completed `11.3.12.1` |
| Required docs | `README.md`, `intent.md`, `contract.md`, `technical-design.md`, `test-plan.md`, `plan.md`, `review.md` |
| Source inputs read | Parent campaign docs, iteration standards, product model, M11 index, learning service, chat runtime, relevant tests |
| Contract / status / evidence changes | Adds durable `LearningBatch`, `BoundedLearningPolicy`, terminal batch statuses, cancel / timeout evidence |
| Design-review gate | Required before code implementation |
| Test-plan trigger | Required: DB schema, service lifecycle, cancellation / timeout, chat integration, evidence semantics |
| Implementation authorization boundary | `review.md` must record `implementation_authorized: yes`; currently `no` |
| Stop conditions | Missing docs, unresolved P0/P1, live validation need without approval, scope drift into 11.3.12.3/4 |
| Handoff / checkpoint | Read-only design review, then implementation if authorized |

## Files / Modules

Allowed implementation files:

- `apps/api/app/models/learning_batch.py`
- `apps/api/app/models/__init__.py`
- `apps/api/app/repos/learning_batches_repo.py`
- `apps/api/app/schemas/learning_batch.py`
- `apps/api/app/services/learning/bounded_learning.py`
- `apps/api/app/services/learning/learning_batch_controller.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/alembic/versions/20260605_0002_add_learning_batches.py`
- `apps/api/tests/test_learning_batches_repo.py`
- `apps/api/tests/test_bounded_learning_batch_lifecycle.py`
- focused updates in `apps/api/tests/test_learning_run_service.py`
- focused updates in `apps/api/tests/test_conversation_chat_runtime.py`
- this child package docs and parent `CURRENT_STATE.md` / M11 README status lines.

Forbidden implementation files:

- Console UI files.
- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/terminal_hints.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- Task planner / runtime composition files outside explicit chat event metadata.
- Direct autonomous-run endpoint callers.
- Fixture-site or validation-site files.

## Steps

1. Design review checkpoint:
   - run read-only subagent review on seven docs;
   - fix P0 / P1 before implementation;
   - record authorization in `review.md`.
2. Add `LearningBatch` schema / ORM / repo / migration:
   - create durable table and repository methods;
   - add focused repo tests.
3. Add bounded policy and controller:
   - define default policy;
   - enforce scenario count and timeout / cancel safe boundaries;
   - add fake-clock and fake-cancel-checker tests.
4. Integrate `LearningRunService`:
   - create and close batch around URL-only capability discovery;
   - attach `learning_batch_id` to scenario `ExplorationRun.strategy_json`;
   - persist safe `LearnedCapability` rows where evidence allows;
   - preserve current compatibility `LearningRunResult` fields.
5. Integrate chat runtime:
   - pass `session_id` to learning handler;
   - add batch status / summary to learning completed / failed events;
   - ensure active task clears for terminal synchronous results;
   - keep current CLI Ctrl+C as client-side exit / stale runtime-context cleanup, not real in-flight backend
     cancellation.
6. Verification and review:
   - run test-plan commands;
   - run scoped ruff / hardcoding scan;
   - run migration verification or record environment blocker;
   - run code-review subagent;
   - update child `review.md` and parent `CURRENT_STATE.md`.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| docs / design | `review.md` design review section | `implementation_authorized: yes` and no unresolved P0/P1 | P0/P1, missing docs, parent route conflict |
| implementation | changed files + test evidence in `review.md` | required tests pass or unrelated failures recorded | test fail in scoped files, scope drift |
| closeout | child `FINAL_STATUS`, parent `CURRENT_STATE.md` | `PACKAGE_COMPLETE` and next child route selected | insufficient evidence, unresolved review finding |

## Verification

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_batches_repo.py tests/test_bounded_learning_batch_lifecycle.py -v` | model / repo / lifecycle tests pass | Yes | new focused tests |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v` | existing learning/chat behavior plus new batch integration passes | Yes | no live browser |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v` | asset compatibility holds | Yes | regression |
| scoped `uv run ruff check ...` | changed files pass ruff | Yes | exact file list in `test-plan.md` |
| `rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app` | no runtime hardcoding | Yes | explain false positives |
| Alembic online / offline commands | migration chain verified or environment failure recorded | Yes | online pass required for online claim |

## Review Checklist

- [ ] Implementation still matches `contract.md`.
- [ ] Technical design has passed review before implementation.
- [ ] `test-plan.md` commands were run or recorded as not run / unverified.
- [ ] No unauthorized live validation was run.
- [ ] No Page Understanding hints or composition runtime slipped into this child.
- [ ] Batch terminal status cannot remain `running` after returned learning result.
- [ ] Cancelled batch cannot receive later assets.
- [ ] Parent `CURRENT_STATE.md` is synchronized after closeout.
