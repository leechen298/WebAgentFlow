# Implementation Plan

状态：PACKAGE_COMPLETE

## Required Reading

- `AGENTS.md`
- `docs/product-model.md`
- parent package `11.3.10-autonomous-filter-capability-learning`
- child 1 package `11.3.10.1-filter-capability-discovery-learning`
- child 1 final `review.md`
- this package `intent.md`
- this package `contract.md`
- this package `technical-design.md`
- this package `test-plan.md`

## Precondition

Do not implement this package until:

- child 1 status is `PACKAGE_COMPLETE`
- child 1 exposes aggregate capability learning result
- parent `CURRENT_STATE.md` routes active child to this package
- this package `review.md` records `implementation_authorized: yes`

## Implementation Steps

1. Confirm child 1 aggregate result shape and passed / failed / unverified capability semantics.
2. Add or extend learning result aggregate type for `learning_outcome`.
3. Implement outcome derivation if child 1 does not already provide final outcome.
4. Implement control-term filtering for learned action identity fields.
5. Update `chat_runtime.py` learning completion response to use aggregate outcome.
6. Generate current session learned action metadata only from passed capabilities.
7. Ensure failed/unverified results do not enter current session learned action catalog.
8. Add history/debug timeline fields for learning batch outcome and capability summaries.
9. Update CLI session start copy to include `/conversation/history/<session_id>`.
10. Add unit, service/API, CLI, and regression tests.
11. Run required non-live verification commands.
12. Update this package `review.md` with implementation evidence and deviations.

## Stop Conditions

Stop before code implementation if:

- child 1 is not complete.
- aggregate capability result is missing or incompatible.
- implementation would infer success from a single alias.
- control-term filtering cannot be applied before catalog insertion.
- live validation is requested without explicit approval.
- history/debug timeline would expose raw private payloads.

## Suggested Verification Commands

Exact commands should be chosen after implementation. Expected command classes:

- focused API tests for learning outcome
- focused chat runtime tests
- focused CLI tests
- focused Console/API tests if history schema changes
- ruff / import checks for changed Python modules

No live autonomous run is part of this package's default verification.

## Handoff

After child 2 reaches `PACKAGE_COMPLETE`, the parent package may close 11.3.10.
Optional live validation remains a separate explicitly approved step.
