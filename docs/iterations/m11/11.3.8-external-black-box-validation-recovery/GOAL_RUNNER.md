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

Default mode: one child package per `/goal`.

- Work on exactly one child package.
- Stop after the package reaches a final status.
- Do not continue to the next child package unless the prompt explicitly asks
  for full campaign mode.

Full campaign mode: only when the user explicitly asks for full 11.3.8
campaign execution.

- Still work on one child package at a time.
- Continue only when the current child status is `PACKAGE_COMPLETE`.
- Stop the entire goal on `BLOCKED`, `FOLLOW_UP_REQUIRED`,
  `NEEDS_USER_INPUT`, evidence insufficiency, or any source conflict.

## Package Selection

Use `CURRENT_STATE.md` first to identify the active child package and next
action.

Current default route:

```text
11.3.8.1 review-closeout-existing-implementation
```

This is a review / closeout route for existing HEAD state. It is not a fresh
implementation route. Do not reimplement `11.3.8.1` unless the child package
review finds a P0 / P1 blocker that requires a minimal in-scope fix.

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

## Hard Stops

Stop as `NEEDS_USER_INPUT` or `BLOCKED` when any of these occur:

- the selected child package is missing its required documents;
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
