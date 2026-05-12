# 11.1.3 · Task Path Planner MVP Design

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
9. `docs/iterations/m11/11.1.1-task-planning-domain-contract/review.md`
10. `docs/iterations/m11/11.1.2-learned-path-retrieval-ranking/review.md`
11. This directory's `intent.md`
12. This directory's `plan.md`

Status: **documentation initialized**.

## Background

M11.0 established the runtime conversation loop and explicit replay hook.
11.1.1 defined the task-to-path domain contracts. 11.1.2 defines the
LearnedPath retrieval and deterministic ranking layer. The next design step is
to define how a future Task Path Planner consumes task intent plus ranked
LearnedPath candidates and turns them into a minimal, explainable route plan.

11.1.2 documentation is present in the remote branch, while implementation
availability depends on the local / pushed repository state. Do not assume the
remote branch contains the 11.1.2 implementation without checking the local
workspace or branch state.

## Current Relationship

- Prerequisites: 11.1.1 Task Planning Domain Contract and 11.1.2 LearnedPath
  Retrieval and Ranking.
- This package: design the Task Path Planner MVP boundary.
- Future scope: Slot Binding, execution via replay, result verification,
  recovery dialogue, and teaching mode.
- This package only initializes documentation. It does not implement the
  planner.

## Goals

- Define the future Task Path Planner service shape.
- Define how future planner implementation will consume `TaskInput`,
  `TaskIntent`, and ranked `LearnedPathCandidate` values.
- Define the minimum candidate-to-RoutePlan mapping policy.
- Define no-candidate, ambiguous-candidate, risky-candidate, and flaky-candidate
  planning semantics.
- Preserve `match_reasons`, `warnings`, and confirmation requirements for later
  user review and execution.
- Keep the planner deterministic-first and auditable.

## Non-Goals

- Do not write implementation code.
- Do not modify 11.1.1 schemas.
- Do not modify or complete 11.1.2 implementation.
- Do not add retrieval preview API or CLI commands.
- Do not execute replay.
- Do not call autonomous run.
- Do not perform hidden relearning.
- Do not plan from raw HTML.
- Do not connect an LLM provider.
- Do not implement real slot binding, form filling, result verification,
  recovery dialogue, teaching mode, or artifact lifecycle.
- Do not create a 11.1.4 detail directory.

## Document Index

- `intent.md` — why this package exists and what it must not become.
- `plan.md` — implementation plan for a future Task Path Planner MVP package.
- `review.md` — checklist for the future implementation review.

## Development Preconditions

A future implementation package should start only after:

- 11.1.1 schema contracts are available in the working branch.
- 11.1.2 retrieval / ranking behavior is available or explicitly stubbed in the
  implementation plan.
- Planner behavior is limited to selecting and explaining candidate route
  plans; execution remains out of scope.

## Acceptance Summary

- Task Path Planner is the primary name; Agent D is only a legacy alias when
  needed.
- RoutePlan is a future design target, not a deliverable of this documentation
  pass.
- Slot Binding remains future scope and is not assigned a new package number in
  this pass.
- The documentation clearly forbids replay execution, autonomous run, raw HTML
  planning, LLM free planning, and hidden relearning.
