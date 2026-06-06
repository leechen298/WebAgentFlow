# Implementation Plan

状态：proposed

## Inputs

- parent `11.3.12-bounded-learning-composable-capability-assets/GOAL_RUNNER.md`
- parent `CURRENT_STATE.md`
- parent `contract.md`
- parent `technical-design.md`
- parent `plan.md`
- `11.3.12.2-bounded-learning-batch-lifecycle/review.md`
- `apps/api/app/schemas/page_analysis.py`
- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/tests/test_filter_capability_discovery.py`
- `apps/api/tests/test_learning_run_service.py`

## Files / Modules

Allowed implementation files:

- `apps/api/app/schemas/capability_hints.py`
- `apps/api/app/schemas/page_analysis.py`
- `apps/api/app/services/learning/capability_hints.py`
- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/tests/test_capability_hints.py`
- focused updates in `apps/api/tests/test_filter_capability_discovery.py`
- focused updates in `apps/api/tests/test_page_analyzer_selector.py`
- focused updates in `apps/api/tests/test_learning_run_service.py`
- this child package docs and parent `CURRENT_STATE.md` / M11 README status lines.

Forbidden implementation files:

- Console UI files.
- `apps/api/app/services/learning/learned_path_replay.py`.
- Task planner / runtime composition files.
- LearnedCapability repository / model changes unless a design review identifies a compatibility bug.
- Direct autonomous-run endpoint callers.
- Fixture-site or validation-site files.

## Steps

1. Design review checkpoint:
   - run read-only subagent review on seven docs;
   - fix P0 / P1 before implementation;
   - record authorization in `review.md`.
2. Add capability hint schema:
   - schema defaults, redaction, versioning;
   - enum / literal validation for region roles, capability kinds, dependency kinds, terminal target kinds, sample
     source kinds, confidence, and support status;
   - `PageAnalysis` additive optional/default field.
3. Add deterministic hint builder:
   - region, control, terminal target, sample value, dependency groups;
   - no target labels / seed values in normal projection.
4. Integrate PageAnalyzer and capability discovery:
   - attach hints to analysis;
   - prefer hints where present;
   - preserve public redacted hint refs in serialized PageAnalysis;
   - retain runtime-only resolver bindings from hint ids to original `DiscoveredElement` execution metadata;
   - make scenario generation use resolver / original inventory bindings, not serialized selectors in hints;
   - treat redacted existing option values as evidence-only unless resolved through the private resolver;
   - preserve fallback behavior.
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
| closeout | child `FINAL_STATUS`, parent `CURRENT_STATE.md` | `PACKAGE_COMPLETE` and next child route selected | insufficient evidence, unresolved review finding |

## Verification

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_hints.py tests/test_filter_capability_discovery.py -v` | hint derivation and discovery integration pass | Yes | new focused tests |
| `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_page_analyzer_selector.py tests/test_learning_run_service.py tests/test_bounded_learning_batch_lifecycle.py -v` | existing analyzer / learning compatibility holds | Yes | regression |
| scoped `uv run ruff check ...` | changed files pass ruff | Yes | exact list in `test-plan.md` |
| `rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app` | no runtime hardcoding | Yes | explain false positives |

## Review Checklist

- [ ] Implementation still matches `contract.md`.
- [ ] Technical design has passed review before implementation.
- [ ] `test-plan.md` commands were run or recorded as not run / unverified.
- [ ] No unauthorized live validation was run.
- [ ] No composition runtime slipped into this child.
- [ ] Hints are additive and target-agnostic.
- [ ] Parent `CURRENT_STATE.md` is synchronized after closeout.
