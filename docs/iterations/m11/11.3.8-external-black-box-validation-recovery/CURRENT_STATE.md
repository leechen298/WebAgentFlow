# CURRENT_STATE.md

This file is the current routing snapshot for Codex App `/goal` work on
`11.3.8 External Black-box Validation Recovery`.

It is intentionally short. Historical details remain in package docs,
milestone docs, and review records.

## Snapshot

current_mode: full_campaign_mode
parent_package: 11.3.8-external-black-box-validation-recovery
parent_status: active / in progress
parent_authorizes_runtime_implementation: no
latest_external_black_box_result: FAIL

## Active Child Package

active_child_package: 11.3.8.2-suggested-utterance-generation
route_status: PACKAGE_COMPLETE
route_type: child-package-complete
next_action: full campaign mode may create / review 11.3.8.3 child seven-doc package; do not reimplement 11.3.8.2
do_not_reimplement: true
handoff_source: 11.3.8.2-suggested-utterance-generation PACKAGE_COMPLETE

Route meaning:

- `11.3.8.1` review-closeout reached `PACKAGE_COMPLETE`.
- `11.3.8.2` full child-package cycle reached `PACKAGE_COMPLETE`.
- The next eligible package is `11.3.8.3`; full campaign mode may create /
  review its own seven-document child package after confirming no source
  conflict or out-of-scope diff.
- Do not treat the parent `11.3.8` campaign as complete; suggested utterances,
  matcher consumption, regression tests, and external black-box revalidation are
  not all complete. Matcher consumption, regression tests, and external
  black-box revalidation remain pending.

## Package Queue

| Package | Current route status | Next action |
|---|---|---|
| `11.3.8.1-learning-action-goal-preservation` | `PACKAGE_COMPLETE` | Done; stable metadata contract may be consumed by 11.3.8.2 |
| `11.3.8.2-suggested-utterance-generation` | `PACKAGE_COMPLETE` | Done; reusable utterances may be consumed by 11.3.8.3 |
| `11.3.8.3-learned-action-matching-improvement` | `ready_after_11.3.8.2_PACKAGE_COMPLETE` | Full campaign mode may create / review child seven-doc package after source-conflict checks |
| `11.3.8.4-regression-tests` | `blocked_by_11.3.8.3_matching_contract` | Wait for matcher contract |
| `11.3.8.5-external-black-box-revalidation-closeout` | `blocked_by_11.3.8.4_regression_tests` | Stop for live validation approval before any live run |

## Conflict Rule

If `CURRENT_STATE.md` conflicts with a child package `review.md`,
`technical-design.md`, `plan.md`, or actual git state, stop as
`NEEDS_USER_INPUT`. Do not choose one source silently.

## Live Validation Rule

Do not run live external validation until the current thread explicitly
provides:

- API base URL;
- target URL;
- whether DB state has been cleaned or intentionally preserved;
- approved scenario list;
- whether latest result docs may be updated after actual evidence.

Without all five fields, `11.3.8.5` must stop as `NEEDS_USER_INPUT`.
