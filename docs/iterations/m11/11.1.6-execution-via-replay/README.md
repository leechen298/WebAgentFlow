# 11.1.6 · Execution via Replay

Status: **documentation initialized**.

## Execution Prerequisites

Before working from this package, read these documents in order:

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/architecture.md`
6. `docs/iterations/m11/m11-plan.md`
7. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
8. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
9. `docs/iterations/m11/11.1.4-task-planning-dispatch-preview/review.md`
10. `docs/iterations/m11/11.1.5-plan-confirmation-consent-gate/review.md`
11. This directory's `intent.md`
12. This directory's `plan.md`

## Background

11.1.4 exposes planning preview through the conversation runtime. 11.1.5 turns
the pending preview into an auditable user decision and introduces
`plan_confirmed` as confirmed-but-not-executed semantics.

11.1.6 is the next design package: execute an already confirmed plan through
existing deterministic replay capability. It does not re-plan, learn a new
path, verify the business result, report final task success, or recover from
failure.

## Current Relationship

- Prerequisites: M11.0 conversation runtime foundation, 11.1.4 Task Planning
  Dispatch Preview, 11.1.5 Plan Confirmation and Consent Gate, and the existing
  M10 replay foundation / 11.0.6 explicit replay hook.
- This package: design confirmed-plan execution through deterministic replay.
- Future scope: result verification, Task Result Reporter, recovery dialogue,
  teaching mode, and broader task-to-path evidence.

## Goals

- Define preconditions for executing a confirmed plan.
- Define how execution locates the confirmed plan / selected LearnedPath.
- Define the replay invocation boundary for first implementation.
- Define conversation event and assistant-message semantics for execution
  started / completed / failed / blocked.
- Preserve explicit replay compatibility.
- Keep result verification and Task Result Reporter outside 11.1.6.

## Non-Goals

- Do not write implementation code in this documentation pass.
- Do not modify 11.1.1 schemas.
- Do not modify 11.1.2 retrieval implementation.
- Do not modify 11.1.3 planner implementation.
- Do not modify 11.1.4 preview implementation.
- Do not modify 11.1.5 confirmation implementation.
- Do not add API endpoints or CLI commands.
- Do not call autonomous run.
- Do not perform hidden relearning.
- Do not read raw HTML.
- Do not connect an LLM provider.
- Do not implement real slot binding or form filling.
- Do not implement result verification.
- Do not implement Task Result Reporter.
- Do not implement recovery dialogue or teaching mode.
- Do not perform browser exploration.
- Do not create a 11.1.7 detail directory.

## Document Index

- `intent.md` - why confirmed plans execute through deterministic replay and
  why replay completion is not business success.
- `plan.md` - future implementation plan for execution via replay.
- `review.md` - checklist for the future implementation review.

## Development Preconditions

A future implementation should start only after:

- 11.1.5 `plan_confirmed` behavior is available in the working branch;
- the current replay service / explicit replay hook has been inspected;
- the implementation can locate a confirmed plan and selected LearnedPath from
  auditable conversation events;
- required replay context is explicitly available, including `learned_path_id`
  and target URL / entry context;
- missing context behavior is decided before code changes.

## Acceptance Summary

- The core path is `confirmed plan -> deterministic replay execution`.
- 11.1.6 is not `ordinary task -> autonomous execution`.
- `replay completed` does not mean `task verified` or `business success`.
- Execution is blocked when selected path or target URL / entry context is
  missing.
- Explicit `/replay <learned_path_id> <url>` remains a separate entry path.
