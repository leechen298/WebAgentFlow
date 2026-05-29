# CURRENT_STATE.md

This file is the current routing snapshot for Codex App `/goal` work on
`11.3.8 External Black-box Validation Recovery`.

It is intentionally short. Historical details remain in package docs,
milestone docs, and review records.

## Snapshot

current_mode: one_goal_per_child_package
parent_package: 11.3.8-external-black-box-validation-recovery
parent_status: ready for review / umbrella planning
parent_authorizes_runtime_implementation: no
latest_external_black_box_result: FAIL

## Active Child Package

active_child_package: 11.3.8.1-learning-action-goal-preservation
route_status: implementation_complete_pending_followup
route_type: review-closeout-existing-implementation
next_action: review-closeout-existing-implementation
do_not_reimplement: true
handoff_target: 11.3.8.2-suggested-utterance-generation

Route meaning:

- Review the existing `11.3.8.1` implementation and child docs.
- Confirm whether the metadata contract is stable enough for `11.3.8.2`.
- Do not start `11.3.8.2` from this goal unless explicitly requested and
  `11.3.8.1` reaches `PACKAGE_COMPLETE`.

## Package Queue

| Package | Current route status | Next action |
|---|---|---|
| `11.3.8.1-learning-action-goal-preservation` | `implementation_complete_pending_followup` | Review and close out existing implementation |
| `11.3.8.2-suggested-utterance-generation` | `blocked_by_11.3.8.1_metadata_contract` | Create / review child seven-doc package after 11.3.8.1 closes; route type `create-review-seven-doc-package` |
| `11.3.8.3-learned-action-matching-improvement` | `blocked_by_11.3.8.2_utterance_contract` | Wait for utterance contract |
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
