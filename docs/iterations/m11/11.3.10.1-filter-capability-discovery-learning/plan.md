# Implementation Plan

状态：PACKAGE_COMPLETE

## Required Reading

- `AGENTS.md`
- `docs/product-model.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- parent package `11.3.10-autonomous-filter-capability-learning`
- this package `intent.md`
- this package `contract.md`
- this package `technical-design.md`
- this package `test-plan.md`

## Implementation Steps

1. Confirm this package `review.md` records `implementation_authorized: yes`.
2. Inspect existing PageAnalysis, action planner, learning run service, LearnedPath repo, and exploration router boundaries.
3. Add capability discovery schema / DTOs where existing schemas are insufficient.
4. Implement PageAnalysis to filter inventory conversion.
5. Implement generic adapter support and unsupported evidence recording.
6. Implement scenario matrix generation: single, pairwise, all-supported smoke.
7. Wire URL-only product learning into capability discovery while preserving spec-backed flow.
8. Persist one run history record per scenario with discovery metadata.
9. Gate LearnedPath ingest on clean pass evidence.
10. Return aggregate discovery result for child 2 consumption.
11. Add unit tests for inventory, scenario generation, and adapter binding.
12. Add integration / service tests for run metadata and LearnedPath ingest gate.
13. Add regression coverage for URL-only `/users`-style page not collapsing to one search-button path.
14. Run required non-live test commands.
15. Update this package `review.md` with implementation evidence and any deviations.

## Stop Conditions

Stop before code implementation if:

- `technical-design.md` or `test-plan.md` is missing.
- `review.md` does not authorize implementation.
- implementation requires route-specific hardcoding.
- live autonomous validation is requested without explicit user approval.
- spec-backed autonomous verification would be regressed.
- P0 / P1 design conflict appears.

## Suggested Verification Commands

Exact commands should be chosen after inspecting the final implementation and test file names.
Expected command classes:

- focused API unit tests for capability discovery
- focused learning service tests
- focused chat/runtime regression tests only if affected by aggregate result shape
- ruff / import checks for changed Python modules

No live autonomous run is part of this package's default verification.

## Handoff

Child 1 reached non-live `PACKAGE_COMPLETE`. Child 2 consumed child 1 aggregate
capability result instead of trying to infer learning outcome from a single
alias or single LearnedPath id.
