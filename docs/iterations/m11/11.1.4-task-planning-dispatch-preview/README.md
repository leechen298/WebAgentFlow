# 11.1.4 · Task Planning Dispatch Preview

Status: **已完成**。实现包含在 `apps/api/app/services/task_planning/preview.py`、`apps/api/app/services/conversation/orchestrator.py` 和相关测试中。

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
12. This directory's `intent.md`
13. This directory's `plan.md`

## Background

M11.0 established the runtime conversation foundation. 11.1.1 defined the
task-to-path contracts, 11.1.2 retrieves and ranks LearnedPath candidates, and
11.1.3 introduced the Task Path Planner MVP service boundary.

11.1.4 designs the first conversation-runtime integration point for ordinary
task requests: the system should turn a user task into a planning preview and
then stop for confirmation or report unable-to-plan. It does not execute the
plan.

## Current Relationship

- Prerequisites: M11.0 conversation runtime foundation, 11.1.1 Task Planning
  Domain Contract, 11.1.2 LearnedPath Retrieval and Ranking, and 11.1.3 Task
  Path Planner MVP.
- This package: design conversation dispatch integration for planning preview.
- Future scope: confirmation / consent gate, execution via replay, result
  verification, Task Result Reporter, recovery dialogue, and teaching mode.
- Explicit replay command compatibility must be preserved.

## Goals

- Define how ordinary task requests enter the conversation dispatcher preview
  path.
- Keep explicit `/replay <learned_path_id> <url>` behavior separate and
  compatible.
- Define deterministic `TaskIntent` construction for preview.
- Define orchestration from `TaskIntent` to retrieval / ranking to Task Path
  Planner output.
- Define assistant message and conversation event output for plan proposal,
  confirmation-needed, and unable-to-plan cases.
- Define confirmation-pending semantics without executing replay.

## Non-Goals

- Do not write implementation code.
- Do not modify 11.1.1 schemas.
- Do not modify 11.1.2 retrieval implementation.
- Do not modify 11.1.3 planner implementation.
- Do not add API endpoints or CLI commands.
- Do not execute replay.
- Do not call autonomous run.
- Do not perform hidden relearning.
- Do not read raw HTML.
- Do not connect an LLM provider.
- Do not implement real slot binding, form filling, result verification, Task
  Result Reporter, recovery dialogue, teaching mode, or browser operation.
- Do not create a 11.1.5 detail directory.

## Document Index

- `intent.md` — why planning preview belongs before execution.
- `plan.md` — future implementation plan for conversation dispatch preview.
- `review.md` — checklist for the future implementation review.

## Development Preconditions

A future implementation should start only after:

- the local branch contains the 11.1.1 task planning schemas;
- retrieval / ranking is available through the 11.1.2 service or explicitly
  stubbed in the implementation plan;
- Task Path Planner behavior is available through the 11.1.3 service;
- conversation dispatcher behavior is inspected before choosing final module
  boundaries.

## Acceptance Summary

- The core path is `conversation runtime -> planning preview`, not
  `conversation runtime -> execution`.
- Ordinary task request handling does not break explicit replay command
  handling.
- Planning preview preserves warnings, risk hints, match reasons, and
  confirmation requirements.
- No-candidate results do not trigger autonomous learning, hidden relearning,
  browser operation, or fake plans.
- Task Path Planner and Task Result Reporter are the primary names; legacy
  Agent D / E aliases are not used as primary terminology.
