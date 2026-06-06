# GOAL_RUNNER.md

Purpose: define the Codex App `/goal` routing contract for
`11.3.12-bounded-learning-composable-capability-assets`.

This parent package is an umbrella / campaign package. It does not directly
authorize runtime implementation.

## Authoritative Inputs

Before running this campaign, read:

- `CURRENT_STATE.md`
- `plan.md`
- `README.md`
- `contract.md`
- child package seven-document set for the active child
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `AGENTS.md`
- `docs/product-model.md`

If these inputs conflict with actual git state, stop as `NEEDS_USER_INPUT`.

## Execution Modes

Default mode: `full_campaign_mode`.

- Work on one child package at a time.
- Continue to the next child only when the current child reaches
  `PACKAGE_COMPLETE`.
- Stop on `BLOCKED`, `FOLLOW_UP_REQUIRED`, `NEEDS_USER_INPUT`, evidence
  insufficiency, status conflict, or unresolved P0 / P1 finding.

## Package Selection

Use `CURRENT_STATE.md` first to identify:

- `active_child_package`
- `route_status`
- `route_type`
- `next_action`
- whether implementation is authorized.

Do not implement this parent package directly.

## Child Package Lifecycle

For each code or mixed child package:

1. Create or repair the seven-document package.
2. Run read-only design review, using subagents when independent review axes exist.
3. Record `implementation_authorized: yes` in child `review.md` before code work.
4. Implement only child-scoped approved changes.
5. Run required tests and static checks from child `test-plan.md`.
6. Run code / test / evidence review.
7. Fix P0 / P1 findings and rerun affected checks.
8. Close out child `review.md`.
9. Update this parent `CURRENT_STATE.md`.

## Runtime Authorization

Parent package runtime implementation is never authorized.

Runtime or test implementation is allowed only from the active child package
after that child package has:

- a complete required document set;
- a reviewed `technical-design.md`;
- a current `test-plan.md`;
- a `plan.md` with allowed / forbidden changes and stop conditions;
- `implementation_authorized: yes` in `review.md`.

## Hard Stops

Stop when any of these occur:

- selected child package is missing required documents;
- child package lacks reviewed technical design;
- `CURRENT_STATE.md` conflicts with child docs, parent plan, review records, or
  actual git state;
- implementation would require target-specific route, selector, seed data,
  answer key, page source, or direct autonomous endpoint validation;
- implementation would require changing L1 / L2 / L3 lifecycle or adding a new
  Agent role;
- live validation is needed but not explicitly approved in the current thread.

## Final Status Vocabulary

- `PACKAGE_COMPLETE`
- `REVIEW_READY`
- `BLOCKED`
- `FOLLOW_UP_REQUIRED`
- `NEEDS_USER_INPUT`

Evidence controls status. Do not convert `UNVERIFIED`, `FOLLOW_UP`, or
`BLOCKED` into `PASS` by wording.

## Live Validation Approval

Do not run live validation until the current thread explicitly provides every
required input:

- API base URL;
- target URL;
- DB state policy;
- approved scenario list;
- permission to update latest result docs after actual evidence.

## Required Child Closeout

Before ending a child goal, update the child `review.md` with:

- changed files;
- commands run;
- commands not run;
- test results;
- compatibility review;
- scope review;
- unresolved findings;
- final status.

Keep `CURRENT_STATE.md` aligned with the latest reviewed child status.
