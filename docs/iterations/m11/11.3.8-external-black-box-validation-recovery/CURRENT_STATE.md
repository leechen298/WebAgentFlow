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

active_child_package: 11.3.8.5-external-black-box-revalidation-closeout
route_status: NEEDS_USER_INPUT
route_type: await-live-validation-approval
next_action: wait for API base URL, target URL, DB state policy, approved scenario list, and latest-result-doc update approval; after all five are provided, resume 11.3.8.5 pre-live checks before any live run
do_not_reimplement: true
handoff_source: 11.3.8.4-regression-tests PACKAGE_COMPLETE

Route meaning:

- `11.3.8.1` review-closeout reached `PACKAGE_COMPLETE`.
- `11.3.8.2` full child-package cycle reached `PACKAGE_COMPLETE`.
- `11.3.8.3` full child-package cycle reached `PACKAGE_COMPLETE` with
  repo-local matcher / router tests and no live external validation.
- `11.3.8.4` seven-document child package has been created, read-only design /
  safety review has passed, and child `review.md` records
  `implementation_authorized: yes`.
- `11.3.8.4` reached `PACKAGE_COMPLETE` with repo-local regression tests and no
  live external validation.
- `11.3.8.5` seven-document validation / closeout package has been created and
  is stopped at the live validation approval gate.
- Do not treat the parent `11.3.8` campaign as complete; external black-box
  revalidation is still not run and remains pending.

## Package Queue

| Package | Current route status | Next action |
|---|---|---|
| `11.3.8.1-learning-action-goal-preservation` | `PACKAGE_COMPLETE` | Done; stable metadata contract may be consumed by 11.3.8.2 |
| `11.3.8.2-suggested-utterance-generation` | `PACKAGE_COMPLETE` | Done; reusable utterances may be consumed by 11.3.8.3 |
| `11.3.8.3-learned-action-matching-improvement` | `PACKAGE_COMPLETE` | Done; matcher behavior may be consumed by 11.3.8.4 regression tests |
| `11.3.8.4-regression-tests` | `PACKAGE_COMPLETE` | Done; repo-local regression passed and may be consumed by 11.3.8.5 |
| `11.3.8.5-external-black-box-revalidation-closeout` | `NEEDS_USER_INPUT` | Seven-doc validation package exists; wait for all five live validation approval fields before pre-live checks or live run |

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
