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
plans into `awaiting_confirmation`. 11.1.5 implements the next gate: converting
the user's confirmation, cancellation, rejection, clarification, or revision
intent into an auditable conversation decision.

This package does not execute replay. It records the decision step after a
preview exists and leaves execution via replay to future scope.

## Current Relationship

- Prerequisites: M11.0 conversation runtime foundation, 11.1.1 Task Planning
  Domain Contract, 11.1.2 LearnedPath Retrieval and Ranking, 11.1.3 Task Path
  Planner MVP, and 11.1.4 Task Planning Dispatch Preview.
- This package: implements the confirmation / consent gate after
  `awaiting_confirmation`.
- Future scope: execution via replay, result verification, Task Result
  Reporter, recovery dialogue, and teaching mode.

## Goals

- Handle explicit user decisions while a session is in `awaiting_confirmation`.
- Classify confirm, cancel, reject, clarification, and revision intent with
  deterministic keyword rules.
- Record user decisions without executing replay.
- Record confirmed, cancelled, rejected, clarification-needed, and replay-blocked
  event payloads.
- Preserve explicit replay compatibility without allowing confirmation input or
  slash decision commands to bypass consent.

## Non-Goals

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
- `plan.md` - implementation plan and decision closure for the confirmation /
  consent gate.
- `review.md` - implementation review, evidence, and post-review fixes.

## Implemented Behavior

- Confirm inputs such as `confirm`, `yes`, `proceed`, `continue`, `确认`, `继续`,
  and slash forms such as `/confirm` move the session to `plan_confirmed`.
- Cancel inputs such as `cancel`, `abort`, `stop`, `取消`, `停止`, and slash
  forms such as `/cancel`, `/abort`, `/stop` cancel the pending preview and
  return to `task_intake`.
- Reject inputs such as `reject`, `no`, `不要`, and slash forms such as
  `/reject` reject the pending preview and return to `task_intake`.
- Ambiguous input stays in `awaiting_confirmation` and asks for an explicit
  decision.
- `/replay <learned_path_id> <url>` is blocked while confirmation is pending and
  does not call the replay handler.

## Review Evidence

- `ConversationStatus.PLAN_CONFIRMED` records confirmed-but-not-executed
  semantics.
- Confirmation events record `replay_executed: false`.
- `conversation_events.type` has been widened to `String(64)` with Alembic
  migration `df9ed1494afd` so all confirmation event names fit PostgreSQL.
- The confirmation gate uses the existing dispatch endpoint; no API endpoint or
  CLI command was added.
- Latest review pass includes slash decision commands (`/confirm`, `/cancel`,
  `/abort`, `/stop`, `/reject`) entering the confirmation gate instead of the
  legacy state machine.

## Acceptance Summary

- The core path is `awaiting_confirmation -> explicit user decision`, not
  `awaiting_confirmation -> replay execution`.
- Ambiguous input is not treated as consent.
- Confirmation records consent or ready-for-execution semantics but does not
  execute replay.
- Cancel / reject / revision intent are auditable.
- Explicit `/replay <learned_path_id> <url>` behavior remains separated from
  confirmation input and is blocked while a preview is pending.
