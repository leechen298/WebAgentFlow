# GOAL_RUNNER.md

Purpose: define the Codex App `/goal` routing contract for `<campaign name>`.

This file is an automation contract. It does not replace `plan.md`, child
package contracts, or repository execution-boundary rules.

## Authoritative Inputs

Before running this campaign, read:

- `CURRENT_STATE.md`
- `plan.md`
- `README.md`
- `contract.md`
- the active child package seven-document set, when it exists
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `AGENTS.md`

If these inputs conflict with actual git state, stop as `NEEDS_USER_INPUT`.
Do not silently reconcile conflicting status, scope, or evidence claims.

## Execution Modes

Default mode: `full_campaign_mode`.

- Work on one child package at a time.
- Continue to the next child only when the current child reaches
  `PACKAGE_COMPLETE`.
- Stop the campaign on `BLOCKED`, `FOLLOW_UP_REQUIRED`,
  `NEEDS_USER_INPUT`, evidence insufficiency, status conflict, or unresolved
  P0 / P1 finding.

Stricter campaigns may override this to `one_goal_per_child_package`, but the
override must be explicit in this file and `CURRENT_STATE.md`.

## Package Selection

Use `CURRENT_STATE.md` first to identify:

- `active_child_package`
- `route_status`
- `route_type`
- `next_action`
- whether the child may be implemented or only documented / reviewed

Do not hardcode a stale current child package in this file.

## Child Package Lifecycle

For each code or mixed child package:

1. Create or repair the seven-document package.
2. Run read-only design review.
3. Record `implementation_authorized: yes` in child `review.md`.
4. Implement only the child-scoped approved changes.
5. Run required tests and static checks from `test-plan.md`.
6. Run read-only code / test / evidence review.
7. Fix P0 / P1 findings and rerun affected checks.
8. Close out child `review.md`.
9. Update parent `CURRENT_STATE.md` checkpoint.

Documentation-only child packages may omit implementation steps, but still need
review evidence and a final checkpoint.

## Runtime Authorization

The parent campaign never directly authorizes runtime, matcher, test,
eval-runner, replay, API, schema, frontend, fixture, or validation-result
changes.

Runtime or test implementation is allowed only from the relevant child package
after that child package has:

- a complete required document set;
- a reviewed `technical-design.md` for code / mixed work;
- a current `test-plan.md` when required;
- a `plan.md` with allowed / forbidden changes and stop conditions;
- `implementation_authorized: yes` in `review.md`.

## Hard Stops

Stop as `NEEDS_USER_INPUT` or `BLOCKED` when any of these occur:

- selected child package is missing required documents;
- child package lacks reviewed technical design for code / mixed work;
- `CURRENT_STATE.md` conflicts with child docs, parent plan, review records, or
  actual git state;
- a planned-package required field is missing;
- product model, Agent role, milestone boundary, or evidence semantics would
  need to change;
- implementation would require target-specific route, selector, seed data,
  answer key, page source, or direct endpoint validation;
- evidence is insufficient for the requested status;
- live validation is needed but not explicitly approved in the current thread.

## Final Status Vocabulary

Use these statuses unless the campaign contract defines a narrower set:

- `PACKAGE_COMPLETE`
- `REVIEW_READY`
- `BLOCKED`
- `FOLLOW_UP_REQUIRED`
- `NEEDS_USER_INPUT`

Do not convert `FAIL`, `BLOCKED`, `UNVERIFIED`, or `FOLLOW_UP` into `PASS` by
changing wording. Evidence controls status.

## Live Validation Approval

Stop before live validation unless the current thread explicitly provides all
required inputs, including:

- API base URL;
- target URL;
- whether DB state has been cleaned or intentionally preserved;
- approved scenario list;
- whether latest result docs may be updated after actual evidence.

If any required field is absent, record `NEEDS_USER_INPUT` instead of running
live validation or updating latest result docs.

## Closeout Consistency Gate

Before any child goal writes a final status, compare actual changed files with
the changed-files list in child `review.md`.

Required checks:

- `git status --short`
- `git diff --name-only`
- `git diff --check`

Every in-scope created, modified, or deleted file must be listed in the
relevant `review.md`. If an out-of-scope file appears, stop as
`NEEDS_USER_INPUT`.

## Required Child Closeout

Before ending a child goal, update the child `review.md` truthfully with:

- changed files;
- commands run;
- commands not run;
- test results;
- compatibility review;
- scope review;
- unresolved P1 / P2 / P3 findings;
- final status.

For the parent package, keep `CURRENT_STATE.md` aligned with the latest
reviewed child status.
