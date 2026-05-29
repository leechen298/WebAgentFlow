# GOAL_RUNNER.md

Purpose: provide Codex App `/goal` routing instructions for the M11.3.8
External Black-box Validation Recovery campaign.

This file is an operator / automation routing aid. It does not replace
`plan.md`, any child package contract, or the repository iteration rules.

## Authoritative Inputs

Before running any goal for this campaign, read:

- `CURRENT_STATE.md`
- `plan.md`
- `README.md`
- `contract.md`
- the target child package seven-document set, when it exists
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `AGENTS.md`

If these inputs conflict with actual git state, stop as `NEEDS_USER_INPUT`.
Do not silently reconcile conflicting status, scope, or evidence claims.

## Execution Modes

Default mode: full campaign mode.

- Work on one child package at a time.
- Continue only when the current child status is `PACKAGE_COMPLETE`.
- Stop the entire goal on `BLOCKED`, `FOLLOW_UP_REQUIRED`,
  `NEEDS_USER_INPUT`, evidence insufficiency, unresolved P0 / P1 finding,
  out-of-scope diff, missing live validation approval, or any source conflict.

One child package mode: only when the user explicitly asks for one package or
when `CURRENT_STATE.md` says the next action must stop.

- Work on exactly one child package.
- Stop after the package reaches a final status.
- Do not continue to the next child package.

Full child-package cycle mode: only when the user explicitly requests
`full child-package cycle` for the current or named child package.

- Work on exactly that child package; this does not authorize full campaign
  execution or moving into the next child package.
- Codex may create or repair the child seven-document set, run internal
  read-only subagent review, record `implementation_authorized: yes` when the
  child design review passes, implement the child-scoped changes, run required
  verification, run subagent code review, fix P0 / P1 findings, and close out
  the child package in one goal.
- This mode does not skip gates. It executes the documentation, design,
  authorization, implementation, verification, code-review, fix, and closeout
  gates inside the same goal instead of requiring separate user-driven prompts.
- If any required gate cannot run, lacks evidence, fails, finds unresolved P0 /
  P1 issues, or conflicts with actual git state, stop with the appropriate
  final status instead of continuing.

## Package Selection

Use `CURRENT_STATE.md` first to identify the active child package and next
action.

Current default route: read `active_child_package`, `route_status`,
`route_type`, `next_action`, and `do_not_reimplement` from
`CURRENT_STATE.md`. Do not treat a package id in this file as authoritative
once `CURRENT_STATE.md` has advanced.

If the current child is already `PACKAGE_COMPLETE`, follow `next_action` from
`CURRENT_STATE.md`: either stop the goal, or, when full campaign mode remains
eligible, create / review the next child package from the parent plan. Do not
reimplement a completed child unless review finds a P0 / P1 blocker that
requires a minimal in-scope fix.

## Child Package Lifecycle Routes

A child package may use one of these route types:

- `review-closeout-existing-implementation`
- `create-review-seven-doc-package`
- `implementation-after-reviewed-design`
- `external-validation-closeout`

If the route is `create-review-seven-doc-package`, missing child docs are the
task, not a blocker. Create the seven-document set, update the child
`review.md`, and stop as `REVIEW_READY`.

If the route is `implementation-after-reviewed-design`, missing child docs or
missing reviewed `technical-design.md` are blockers.

## Runtime Authorization

The parent `11.3.8` package never directly authorizes runtime, matcher, test,
eval-runner, replay, API, schema, frontend, fixture, or validation-result
changes.

Runtime or test implementation is allowed only from the relevant child package
after that child package has:

- a complete seven-document set;
- a reviewed `technical-design.md`;
- a current `test-plan.md`;
- a `plan.md` with allowed / forbidden changes and stop conditions.

During child package execution, do not modify `GOAL_RUNNER.md` unless the user
explicitly asks for Goal Runner maintenance.

For code or mixed implementation, `technical-design.md` counts as reviewed only
when the child `review.md` or `FINAL_STATUS` explicitly contains
`implementation_authorized: yes`, or an equivalent human /
reviewer-approved marker required by the repository iteration rules. Codex must
not self-authorize implementation in the same goal run that first creates the
child technical design unless the user explicitly asks for that. A user request
for `full child-package cycle` is such an explicit request, but only when the
same goal actually runs and records the required read-only child design review
before implementation starts.

## Hard Stops

Stop as `NEEDS_USER_INPUT` or `BLOCKED` when any of these occur:

- the selected child package is missing its required documents and the current
  route is not `create-review-seven-doc-package`;
- the child package lacks reviewed technical design for code / mixed work;
- `CURRENT_STATE.md` conflicts with a child `review.md`,
  `technical-design.md`, `plan.md`, or actual git state;
- a planned-package required field is missing;
- product model, Agent role, milestone boundary, or evidence semantics would
  need to change;
- implementation would require target-specific route, selector, seed data,
  answer key, page source, or direct endpoint validation;
- evidence is insufficient for the requested status;
- live external validation is needed but not explicitly approved in the current
  thread.

## Final Status Vocabulary

Use these statuses exactly:

- `PACKAGE_COMPLETE`
- `REVIEW_READY`
- `BLOCKED`
- `FOLLOW_UP_REQUIRED`
- `NEEDS_USER_INPUT`

Do not convert `FAIL`, `BLOCKED`, `UNVERIFIED`, or `FOLLOW_UP` into `PASS` by
changing wording. Evidence controls status.

## Live Validation Approval

`11.3.8.5` must stop before live external validation unless the current thread
explicitly provides all of:

- API base URL;
- target URL;
- whether DB state has been cleaned or intentionally preserved;
- approved scenario list;
- whether latest result docs may be updated after actual evidence.

If any field is absent, record the package as `NEEDS_USER_INPUT` instead of
running live validation or updating latest result docs.

## Closeout Consistency Gate

Before any child goal may write a final status, compare actual changed files
with the changed-files list in the relevant `review.md`.

Required checks:

- `git status --short`
- `git diff --name-only`
- `git diff --check`

Rules:

- Every created, modified, or deleted in-scope file must be listed in the
  relevant `review.md` changed-files section.
- If an in-scope docs-only support file is missing from `review.md`, update
  `review.md` in the same goal and continue.
- If an unlisted runtime, test, eval, external result, fixture, schema, API,
  worker, frontend, or out-of-scope file appears, stop as `NEEDS_USER_INPUT`.
- Do not ask the user to manually repair docs-only changed-file omissions.

## Required Closeout Per Child Package

Before ending a child goal, update the child `review.md` truthfully with:

- changed files;
- commands run;
- commands not run;
- test results;
- compatibility review;
- scope review;
- unresolved P1 / P2 / P3 findings;
- final status.

For the parent package, keep `CURRENT_STATE.md` and the parent `FINAL_STATUS`
block aligned with the latest reviewed child status.
