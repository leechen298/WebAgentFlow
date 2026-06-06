# GOAL_RUNNER.md

Purpose: define the Codex App `/goal` routing contract for
`11.3.11-terminal-state-agent-learning-stop-control`.

This file is an automation contract. It does not replace `plan.md`, child
package contracts, product-model rules, or repository execution-boundary rules.

## Authoritative Inputs

Before running this campaign, read:

- `CURRENT_STATE.md`
- `plan.md`
- `README.md`
- `contract.md`
- active child package seven-document set, once it exists
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
- Child packages must follow the sequence in parent `plan.md`.
- A child may create its own seven-document set only when `CURRENT_STATE.md`
  routes to child-doc-generation.
- Runtime implementation starts only after the active child package records
  `implementation_authorized: yes`.

## Package Selection

Use `CURRENT_STATE.md` first to identify:

- `active_child_package`
- `route_status`
- `route_type`
- `next_action`
- whether the child may be documented, reviewed, implemented, validated, or
  must wait

Do not hardcode a stale child package in this file.

## Child Package Lifecycle

For each child package:

1. Create the child seven-document package if route permits docs generation.
2. Run read-only design review.
3. Confirm `implementation_authorized: yes` in child `review.md`.
4. Implement only child-scoped approved changes.
5. Run required tests and static checks from child `test-plan.md`.
6. Run read-only code / test / evidence review.
7. Fix P0 / P1 findings and rerun affected checks.
8. Close out child `review.md`.
9. Update parent `CURRENT_STATE.md` checkpoint.

## Runtime Authorization

The parent campaign never directly authorizes runtime, matcher, schema, API,
database, frontend, CLI, fixture, prompt, eval-runner, replay, autonomous-run,
or validation-result changes.

Runtime or test implementation is allowed only from the active child package
after that child has:

- a complete required document set;
- a reviewed `technical-design.md`;
- a current `test-plan.md`;
- a `plan.md` with allowed / forbidden changes and stop conditions;
- `implementation_authorized: yes` in `review.md`.

## Subagent Delegation Policy

Use subagents by default for implementation or review checkpoints when
available. Good delegation axes:

- browser event recorder / redaction review;
- Page Understanding terminal hint boundary review;
- Terminal State Agent / autonomous explorer stop-controller impact mapping;
- Attempt Evaluation / LearnedPath ingest gate review;
- Console / history evidence presentation review;
- test matrix and evidence integrity review.

Single-threaded execution is allowed only for documentation generation or when
delegation would violate the iteration contract, sandbox, live-run boundary,
evidence rules, or Git safety rules. Record the reason in the child checkpoint.

## Hard Stops

Stop as `BLOCKED` or `NEEDS_USER_INPUT` if:

- implementation is requested before the active child package exists and is
  reviewed;
- a child is skipped or the sequence is changed without updating parent docs;
- product runtime, prompt, schema, or tests hardcode `/users`, field labels,
  button labels, DOM ids, fixture data, or operation aliases outside tests/docs/fixtures;
- a new Agent role is implemented before product-model update, or any legacy Agent letter is introduced
  without product-model update;
- failed / unverified terminal evidence is used to claim user-facing success;
- event recording stores raw secrets, unredacted request bodies, tokens, cookies,
  or personal data;
- live autonomous validation is needed but user has not explicitly approved target,
  scenario, surface and result-doc update scope;
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
`pass_gate.status`, supervisor verdict, scorecard, terminal evidence summary,
and raw output / artifact path in the active child `review.md`.

## Closeout Consistency Gate

Before closing parent or child status:

- compare child `review.md`, parent `CURRENT_STATE.md`, M11 README and actual git diff;
- verify no live-run claim exists without run_id / pass_gate evidence;
- verify no parent-only doc authorizes runtime work;
- verify failed / unverified evidence cannot be ingested as successful LearnedPath.
