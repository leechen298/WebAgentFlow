# Implementation Plan

状态：proposed

## Inputs

- parent `11.3.12-bounded-learning-composable-capability-assets/GOAL_RUNNER.md`
- parent `CURRENT_STATE.md`
- parent `contract.md`
- parent `technical-design.md`
- parent `plan.md`
- `11.3.12.1-learned-capability-asset-foundation/review.md`
- `11.3.12.2-bounded-learning-batch-lifecycle/review.md`
- `11.3.12.3-page-understanding-capability-hints/review.md`
- `apps/api/app/models/learned_capability.py`
- `apps/api/app/repos/learned_capabilities_repo.py`
- `apps/api/app/schemas/learned_capability.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_learned_capabilities_repo.py`
- `apps/api/tests/test_learned_path_replay.py`

## Files / Modules

Allowed implementation files:

- `apps/api/app/schemas/capability_composition.py`
- `apps/api/app/services/learning/capability_composer.py`
- focused updates in `apps/api/app/repos/learned_capabilities_repo.py`
- focused updates in `apps/api/app/services/learning/learned_path_replay.py` only for execution-handoff
  compatibility helpers; do not change replay execution semantics.
- focused updates in `apps/api/tests/test_capability_composer.py`
- focused updates in `apps/api/tests/test_learned_capabilities_repo.py`
- focused updates in `apps/api/tests/test_learned_path_replay.py`
- this child package docs and parent `CURRENT_STATE.md` / M11 README status lines.

Forbidden implementation files:

- Console UI files.
- New public HTTP API routers.
- `apps/api/app/services/learning/autonomous_explorer.py` live-run paths.
- Direct autonomous-run endpoint callers.
- LLM provider prompt / browser step generation files unless design review explicitly narrows and authorizes a
  non-execution semantic recommendation change.
- Fixture-site or validation-site files.

## Steps

1. Design review checkpoint:
   - run read-only subagent review on seven docs;
   - fix P0 / P1 before implementation;
   - record authorization in `review.md`.
2. Add composition schemas:
   - public plan / result / policy;
   - private execution handoff;
   - redaction boundaries and status taxonomy.
3. Add deterministic composer service:
   - LearnedPath preference branch;
   - candidate compatibility filter;
   - deterministic ordering;
   - conflict / missing / unsafe / ambiguous rejection.
4. Add promotion guard:
   - reject plan-only evidence;
   - require successful execution and terminal evidence;
   - prepare optional source capability metadata without breaking LearnedPath rows.
5. Verification and review:
   - run test-plan commands;
   - run scoped ruff / hardcoding scan;
   - run code-review subagent;
   - update child `review.md` and parent `CURRENT_STATE.md`.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| docs / design | `review.md` design review section | `implementation_authorized: yes` and no unresolved P0/P1 | P0/P1, missing docs, parent route conflict |
| implementation | changed files + test evidence in `review.md` | required tests pass or unrelated failures recorded | test fail in scoped files, scope drift |
| closeout | child `FINAL_STATUS`, parent `CURRENT_STATE.md` | `PACKAGE_COMPLETE` or parent closeout route | insufficient evidence, unresolved review finding |

## Verification

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_composer.py -v` | composition unit tests pass | Yes | new focused tests |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_learned_path_replay.py -v` | asset / replay compatibility holds | Yes | regression |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v` | learning / chat compatibility holds | Yes | regression |
| scoped `uv run ruff check ...` | changed files pass ruff | Yes | exact list in `test-plan.md` |
| `rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app` | no runtime hardcoding | Yes | explain false positives |

## Review Checklist

- [ ] Implementation still matches `contract.md`.
- [ ] Technical design has passed review before implementation.
- [ ] `test-plan.md` commands were run or recorded as not run / unverified.
- [ ] No unauthorized live validation was run.
- [ ] No LLM browser-step execution slipped into this child.
- [ ] Existing LearnedPath preference remains intact.
- [ ] Public composition plan stays redacted.
- [ ] Parent `CURRENT_STATE.md` is synchronized after closeout.
