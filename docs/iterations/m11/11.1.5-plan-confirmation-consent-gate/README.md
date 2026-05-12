# 11.1.5 · Plan Confirmation and Consent Gate

Status: **implementation complete, review passed**.

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
11. `docs/iterations/m11/11.1.3-task-path-planner-mvp/review.md`
12. `docs/iterations/m11/11.1.4-task-planning-dispatch-preview/review.md`
13. This directory's `intent.md`
14. This directory's `plan.md`

## Background

11.1.4 connects ordinary task input to planning preview and moves proposed
plans into `awaiting_confirmation`. 11.1.5 designs the next gate: converting
the user's confirmation, cancellation, rejection, clarification, or revision
intent into an auditable conversation decision.

This package does not execute replay. It only designs how WebAgentFlow should
handle the decision step after a preview exists.

## Current Relationship

- Prerequisites: M11.0 conversation runtime foundation, 11.1.1 Task Planning
  Domain Contract, 11.1.2 LearnedPath Retrieval and Ranking, 11.1.3 Task Path
  Planner MVP, and 11.1.4 Task Planning Dispatch Preview.
- This package: design the confirmation / consent gate after
  `awaiting_confirmation`.
- Future scope: execution via replay, result verification, Task Result
  Reporter, recovery dialogue, and teaching mode.

## Goals

- Define how `awaiting_confirmation` handles explicit user decisions.
- Define deterministic input classification for confirm, cancel, reject,
  clarification, and revision intent.
- Define consent gate semantics that record user decisions without executing
  replay.
- Define future event payload expectations for confirmed, cancelled, rejected,
  clarification-needed, and revision-requested paths.
- Preserve explicit replay compatibility without allowing confirmation input to
  bypass consent.

## Non-Goals

- Do not write implementation code.
- Do not modify 11.1.1 schemas.
- Do not modify 11.1.2 retrieval implementation.
- Do not modify 11.1.3 planner implementation.
- Do not modify 11.1.4 preview implementation.
- Do not add API endpoints or CLI commands.
- Do not execute replay.
- Do not call autonomous run.
- Do not perform hidden relearning.
- Do not read raw HTML.
- Do not connect an LLM provider.
- Do not implement real slot binding, form filling, result verification, Task
  Result Reporter, recovery dialogue, teaching mode, or browser operation.
- Do not create a 11.1.6 detail directory.

## Document Index

- `intent.md` - why explicit confirmation and consent are required before
  execution.
- `plan.md` - future implementation plan for the confirmation / consent gate.
- `review.md` - checklist for the future implementation review.

## Development Preconditions

A future implementation should start only after:

- 11.1.4 preview behavior is available in the working branch;
- `awaiting_confirmation` state behavior is inspected in the current
  conversation state machine;
- the implementation chooses whether new confirmation event types or statuses
  are needed;
- explicit replay behavior while a preview is pending is decided.

## Acceptance Summary

- The core path is `awaiting_confirmation -> explicit user decision`, not
  `awaiting_confirmation -> replay execution`.
- Ambiguous input is not treated as consent.
- Confirmation records consent or ready-for-execution semantics but does not
  execute replay.
- Cancel / reject / revision intent are auditable.
- Explicit `/replay <learned_path_id> <url>` behavior remains separated from
  confirmation input until the pending-preview policy is explicitly decided.
