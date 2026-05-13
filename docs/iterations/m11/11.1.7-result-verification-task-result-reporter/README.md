# 11.1.7 · Result Verification and Task Result Reporter

Status: **implementation complete, review passed**.

## Required Reading

Before implementing this package, read these documents in order:

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/architecture.md`
6. `docs/iterations/m11/m11-plan.md`
7. `docs/iterations/m11/11.1-task-to-path-planning-execution/intent.md`
8. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
9. `docs/iterations/m11/11.1.1-task-planning-domain-contract/review.md`
10. `docs/iterations/m11/11.1.5-plan-confirmation-consent-gate/review.md`
11. `docs/iterations/m11/11.1.6-execution-via-replay/review.md`
12. This directory's `intent.md`
13. This directory's `plan.md`

## Background

11.1.6 can execute a confirmed plan through deterministic replay. That only
closes the replay invocation layer. It does not prove that the user's business
task succeeded.

11.1.7 designs the next boundary: consume replay execution evidence, derive an
honest verification outcome, and produce a Task Result Reporter message that
does not invent success.

Core rule:

```text
Replay completed != task succeeded.
```

## Current Relationship

- Prerequisite: 11.1.6 Execution via Replay.
- Schema foundation: 11.1.1 task planning schemas, including result/reporting
  contracts where available.
- Input surface: conversation execution events and replay-level evidence.
- This package: result verification semantics and Task Result Reporter design.
- Future: task-to-path tests and evidence.

## Goal

Design how WebAgentFlow turns replay execution evidence into:

- a verification outcome such as `verified`, `failed`, `uncertain`,
  `needs_review`, or `blocked`;
- an evidence summary and missing-evidence summary;
- an honest user-facing Task Result Reporter response.

The result report must say when evidence is missing. It must not present replay
completion as business success.

## Non-Goals

- Do not write implementation code in this documentation package.
- Do not modify 11.1.1 schemas.
- Do not modify 11.1.6 execution implementation.
- Do not add an API endpoint or CLI command.
- Do not execute replay or re-execute replay.
- Do not call autonomous run.
- Do not do hidden relearning.
- Do not read raw HTML.
- Do not call an LLM provider.
- Do not call Page Understanding Agent.
- Do not do slot binding or form filling.
- Do not implement recovery dialogue.
- Do not implement teaching mode.
- Do not do browser exploration.
- Do not create an 11.1.8 detail directory.

## Document Index

- `intent.md` — why result verification and Task Result Reporter are required
  after replay execution.
- `plan.md` — future implementation plan, boundaries, and open questions.
- `review.md` — future implementation review checklist.

## Development Prerequisites

Future implementation should first confirm:

- execution events from 11.1.6 are available and auditable;
- `plan_execution_completed` is treated as replay-level completion only;
- any postcondition evidence source is explicit and stable;
- missing verification evidence maps to `uncertain` or `needs_review`, not
  success;
- Task Result Reporter uses the primary role name, with Agent E only as a
  legacy alias when needed.

## Acceptance Summary

- Core path:

```text
replay execution evidence -> verification outcome -> honest task result report
```

- Not allowed:

```text
replay completed -> task succeeded
failed / uncertain -> automatic recovery
```

- `uncertain` and `needs_review` are valid outputs when evidence is incomplete.
