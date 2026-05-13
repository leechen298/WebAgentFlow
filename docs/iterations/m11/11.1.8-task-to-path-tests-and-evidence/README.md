# 11.1.8 · Task-to-path Tests and Evidence

Status: **documentation initialized**.

## Required Reading

Before executing this package, read these documents in order:

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/architecture.md`
6. `docs/iterations/m11/README.md`
7. `docs/iterations/m11/m11-plan.md`
8. `docs/iterations/m11/11.1-task-to-path-planning-execution/README.md`
9. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
10. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
11. `docs/iterations/m11/11.1.4-task-planning-dispatch-preview/review.md`
12. `docs/iterations/m11/11.1.5-plan-confirmation-consent-gate/review.md`
13. `docs/iterations/m11/11.1.6-execution-via-replay/review.md`
14. `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/review.md`
15. This directory's `intent.md`
16. This directory's `plan.md`
17. This directory's `review.md`

## Background

M11.1 now has the main task-to-path runtime chain:

```text
TaskIntent
-> LearnedPath retrieval / ranking
-> Task Path Planner
-> planning preview
-> confirmation / consent gate
-> execution via deterministic replay
-> Task Result Reporter
```

11.1.8 is not a new runtime feature package. It is the tests and evidence
closure package for the M11.1 task-to-path MVP.

The goal is to turn the implemented chain into evidence that can be reviewed:
focused regression tests, scoped deterministic E2E, explicit negative-path
coverage, Codex autonomous review output, and documented caveats.

Core rule preserved:

```text
Replay completed != task succeeded.
```

## Dependencies

- 11.1.1 Task Planning Domain Contract.
- 11.1.2 LearnedPath Retrieval and Ranking.
- 11.1.3 Task Path Planner MVP.
- 11.1.4 Task Planning Dispatch Preview.
- 11.1.5 Plan Confirmation and Consent Gate.
- 11.1.6 Execution via Replay.
- 11.1.7 Result Verification and Task Result Reporter.
- Existing API tests, E2E tests, and `docs/testing/` evidence structure.

11.1.7 focused fixes and tests should be treated as an execution prerequisite
before running 11.1.8 test evidence work.

## Goal

Define the evidence plan for proving the scoped M11.1 MVP behavior:

- deterministic API / service regression coverage;
- scoped E2E covering task preview, confirmation, execution, and reporting;
- negative / blocked / uncertain path coverage;
- explicit `/replay` compatibility regression coverage;
- Codex autonomous review focused on task-to-path safety boundaries;
- evidence reports that distinguish deterministic pass, exploratory findings,
  manual smoke, and environment-blocked runs.

## Non-Goals

- Do not write implementation code.
- Do not add test code in this documentation package.
- Do not run tests in this documentation package.
- Do not modify 11.1.1 through 11.1.7 business logic.
- Do not add an API endpoint or CLI command.
- Do not execute replay.
- Do not call autonomous run.
- Do not do hidden relearning.
- Do not read raw HTML.
- Do not call an LLM provider.
- Do not do slot binding.
- Do not implement recovery.
- Do not implement teaching mode.
- Do not create an 11.1.9 detail directory.
- Do not pull M12, recovery, or teaching work into M11.1.

## Document Index

- `intent.md` — why M11.1 needs a tests and evidence closure package.
- `plan.md` — future test matrix, scoped E2E, review, and evidence plan.
- `review.md` — future 11.1.8 execution review checklist.

## Execution Prerequisites

Before executing 11.1.8 test work:

- confirm 11.1.7 focused fixes are complete or explicitly documented as open;
- confirm current branch and dirty worktree scope;
- decide which commands are deterministic acceptance gates;
- decide which E2E commands are allowed in the current environment;
- prepare evidence report locations under `docs/testing/results/`;
- keep environment-blocked runs separate from deterministic failures.

## Acceptance Summary

11.1.8 execution should leave evidence for:

```text
M11.1 task-to-path MVP tests and evidence closure
```

It must not redefine M11.1 as:

```text
new runtime feature implementation
```

It must continue to preserve:

```text
replay completed != task succeeded
uncertain / needs_review is a valid result
failed / blocked does not trigger recovery or hidden learning
```
