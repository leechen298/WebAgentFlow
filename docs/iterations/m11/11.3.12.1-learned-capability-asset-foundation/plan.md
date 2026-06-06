# Plan

状态：proposed

## Implementation Boundary

This child implements only the asset foundation. It must not touch batch lifecycle, chat timeout,
bounded planner, Page Understanding hints, runtime composition, replay execution, CLI, or Console UI.

## Files

Create:

- `apps/api/app/models/learned_capability.py`
- `apps/api/app/repos/learned_capabilities_repo.py`
- `apps/api/app/schemas/learned_capability.py`
- `apps/api/alembic/versions/20260605_0001_add_learned_capabilities.py`
- `apps/api/tests/test_learned_capabilities_repo.py`

Modify:

- `apps/api/app/models/__init__.py`
- child and parent `review.md` / parent `CURRENT_STATE.md` during closeout

## Steps

1. Write failing repo tests for `LearnedCapability` ingest, dedup, trust, and compatibility.
2. Add Alembic migration for `learned_capabilities`.
3. Add ORM model and export it from `models/__init__.py`.
4. Add Pydantic schemas with redacted normal projection.
5. Add `LearnedCapabilityRepository` and dedup helper.
6. Run repo tests and fix implementation until passing.
7. Run LearnedPath regression tests.
8. Run ruff and hardcoding scan.
9. Update child `review.md` with changed files, commands, not-run items, compatibility review, and final status.
10. If child reaches `PACKAGE_COMPLETE`, update parent `CURRENT_STATE.md` to route to 11.3.12.2 planning.

## Stop Conditions

Stop before code if:

- design review leaves any P0 / P1 finding;
- implementation would need to alter learning scenario generation;
- implementation would need to change chat timeout/cancel behavior;
- implementation appears to require modifying LearnedPath schema or exploration router;
- tests require unauthorized live autonomous runs.

Stop during implementation if:

- old LearnedPath tests fail for reasons not directly understood and fixed;
- new asset schema would expose raw selectors or target-site details in public projection;
- any runtime hardcoding true positive is introduced.

## Verification

Required commands are listed in `test-plan.md`. Record actual outputs in `review.md`; do not claim live validation.

## Handoff

After this child closes:

- 11.3.12.2 can design and implement bounded learning batch lifecycle using the persisted asset layer.
- 11.3.12.1 must not claim bounded learning or composition behavior is complete.
