# CURRENT_STATE.md

This file is the current routing snapshot for Codex App `/goal` work on
`<campaign name>`.

It is intentionally short. Historical details remain in package docs,
milestone docs, and review records.

## Snapshot

current_mode: full_campaign_mode
parent_package: <parent-package-id>
parent_status: <active / ready for review / complete / blocked>
parent_authorizes_runtime_implementation: no
latest_external_validation_result: <N/A / PASS / FAIL / UNVERIFIED / BLOCKED>

## Active Child Package

active_child_package: <child-package-id>
route_status: <READY / PACKAGE_COMPLETE / BLOCKED / NEEDS_USER_INPUT>
route_type: <create-review-seven-doc-package / implementation-after-reviewed-design / child-package-complete / external-validation-closeout>
next_action: <exact next action>
do_not_reimplement: <true / false>
handoff_source: <review.md / parent plan / prior package / N/A>

Route meaning:

- <short explanation of what is complete>
- <short explanation of what remains>
- <explicit instruction about whether the next child may start in this goal>

## Package Queue

| Package | Current route status | Next action |
|---|---|---|
| `<child-1>` | `<status>` | `<next action>` |
| `<child-2>` | `<status>` | `<next action>` |

## Conflict Rule

If `CURRENT_STATE.md` conflicts with a child package `review.md`,
`technical-design.md`, `plan.md`, parent plan, or actual git state, stop as
`NEEDS_USER_INPUT`. Do not choose one source silently.

## Live Validation Rule

Do not run live validation until the current thread explicitly provides every
required input named in `GOAL_RUNNER.md`.
