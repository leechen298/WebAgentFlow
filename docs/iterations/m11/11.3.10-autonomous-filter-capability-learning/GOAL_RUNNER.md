# GOAL_RUNNER.md

Purpose: define the Codex App `/goal` routing contract for
`11.3.10-autonomous-filter-capability-learning`.

This file is an automation contract. It does not replace `plan.md`, child
package contracts, or repository execution-boundary rules.

## Authoritative Inputs

Before running this campaign, read:

- `CURRENT_STATE.md`
- `plan.md`
- `README.md`
- `contract.md`
- active child package seven-document set
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `AGENTS.md`
- `docs/product-model.md`
- `docs/roadmap.md`

If these inputs conflict with actual git state, stop as `NEEDS_USER_INPUT`.
Do not silently reconcile conflicting status, scope, or evidence claims.

## Execution Modes

Default mode: `full_campaign_mode`.

- Work on one child package at a time.
- Child 1 must complete before child 2 implementation starts.
- Stop the campaign on `BLOCKED`, `FOLLOW_UP_REQUIRED`, `NEEDS_USER_INPUT`,
  evidence insufficiency, status conflict, or unresolved P0 / P1 finding.

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

1. Confirm the seven-document package exists.
2. Run read-only design review.
3. Confirm `implementation_authorized: yes` in child `review.md`.
4. Implement only child-scoped approved changes.
5. Run required tests and static checks from `test-plan.md`.
6. Run read-only code / test / evidence review.
7. Fix P0 / P1 findings and rerun affected checks.
8. Close out child `review.md`.
9. Update parent `CURRENT_STATE.md` checkpoint.

## Runtime Authorization

The parent campaign never directly authorizes runtime, matcher, test,
eval-runner, replay, API, schema, frontend, fixture, or validation-result
changes.

Runtime or test implementation is allowed only from the active child package
after that child package has:

- a complete required document set;
- a reviewed `technical-design.md`;
- a current `test-plan.md`;
- a `plan.md` with allowed / forbidden changes and stop conditions;
- `implementation_authorized: yes` in `review.md`.

## Subagent Delegation Policy

Use subagents by default for implementation or review checkpoints when
available. Good delegation axes:

- autonomous explorer / action planner impact mapping;
- learning run result / LearnedPath ingest review;
- chat feedback / history UI review;
- test matrix and evidence integrity review.

Single-threaded execution is allowed only for documentation generation or when
delegation would violate live-run or evidence boundaries. Record the reason in
the child checkpoint.

## Hard Stops

Stop as `BLOCKED` or `NEEDS_USER_INPUT` if:

- child 2 implementation is requested before child 1 is `PACKAGE_COMPLETE`;
- live autonomous validation is needed but user has not explicitly approved target,
  API state, scenario, and result-doc updates;
- product runtime or prompt hardcodes `/users`, field labels, button labels,
  fixture data, DOM ids, or operation aliases outside tests/docs/fixtures;
- failed / unverified learning evidence is used to claim user-facing success;
- implementation diff exceeds the active child package scope;
- required docs, tests, or review evidence are missing.

## Final Status Vocabulary

- `PACKAGE_COMPLETE`: child or parent completed with required evidence.
- `FOLLOW_UP_REQUIRED`: scoped work complete but a documented non-blocking follow-up remains.
- `BLOCKED`: hard stop or unresolved P0 / P1 finding.
- `NEEDS_USER_INPUT`: cannot safely choose route or validation boundary.
- `UNVERIFIED`: checks or evidence are insufficient for the requested claim.

## Live Validation Approval Requirements

Do not run live autonomous validation, `verify-scenario`, product UI live smoke,
or autonomous-run endpoints unless the current user explicitly asks for that
surface and provides the required target and evidence-update scope.

If live validation is approved, record invocation surface, run_id,
`pass_gate.status`, supervisor verdict, scorecard, and raw output / artifact
path in the active child `review.md`.
