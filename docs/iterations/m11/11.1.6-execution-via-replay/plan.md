# Implementation Plan

## Inputs and Dependencies

Future implementation should inspect the current conversation orchestrator,
confirmation gate, replay hook, and replay service before choosing final module
boundaries.

Expected inputs:

- conversation session with `plan_confirmed` status or equivalent
  confirmed-but-not-executed semantics;
- most recent confirmed plan evidence from conversation events;
- selected LearnedPath id;
- target URL or replay entry context;
- route summary / route step metadata when available;
- existing deterministic replay service / explicit replay hook.

Potential implementation locations:

- inspect existing replay service / replay handler before choosing the final
  path;
- likely integration under `apps/api/app/services/conversation/`;
- replay logic should reuse existing replay service or command hook;
- tests likely live under `apps/api/tests/`.

Do not create code files in this documentation pass.

## Execution Preconditions

Replay execution is allowed only when all of the following are true:

- the conversation has a confirmed plan;
- the user consent was recorded through 11.1.5;
- the plan has not already executed;
- the plan was not cancelled, rejected, or superseded;
- a selected LearnedPath id is available;
- a target URL or replay entry context is available;
- the route plan / selected path is still auditable from conversation events.

If any required input is missing, 11.1.6 must not guess. It should return
unable-to-execute or needs-more-context semantics and record a blocked event.

## Confirmed Plan Lookup

The first implementation should recover confirmed plan evidence from
conversation events:

- recent `plan_preview_proposed` event for selected path, warnings, risk hints,
  and route summary;
- `plan_confirmed` event for user consent and decision timestamp;
- optional assistant message metadata if needed as supporting evidence.

11.1.6 must not reconstruct a plan from raw user text.

11.1.6 must not call the Task Path Planner again unless a future package
explicitly designs re-planning.

Future packages may introduce persisted execution context. That is not required
for the first execution-via-replay design.

## Replay Invocation Boundary

The first implementation should reuse existing deterministic replay capability.
It should not perform an HTTP self-call if a service-level replay function is
available.

If the existing replay hook only accepts:

```text
learned_path_id + url
```

then 11.1.6 first implementation may execute only when both fields are
explicitly available.

Replay invocation must not:

- call autonomous run;
- trigger browser exploration;
- read raw HTML for planning;
- call an LLM provider;
- perform slot binding;
- invent browser actions.

## Missing Execution Context Behavior

When selected path or target URL / entry context is missing:

- do not execute replay;
- do not call Task Path Planner;
- do not call autonomous learning;
- append an execution-blocked event;
- return a user-facing message explaining that execution context is missing.

Suggested assistant message:

```text
The confirmed plan is not executable because required replay context is missing.
```

## Conversation Event Recording

Event semantics to plan for:

- `plan_execution_started`
- `plan_execution_completed`
- `plan_execution_failed`
- `plan_execution_blocked`

`completed` means replay invocation completed. It does not mean business result
verification succeeded.

Event payload should include:

- `learned_path_id`;
- target URL / entry context if available;
- route step id or route summary if available;
- replay run id / execution id if available;
- replay result summary if available;
- no result verification marker;
- error summary if failed;
- no autonomous marker;
- `task_verified: false`.

Do not store raw HTML, screenshots, user/account/tenant fields, or result
verification verdicts in 11.1.6 events.

## Conversation State Transition Options

Future implementation may need new conversation statuses. Candidate semantics:

```text
plan_confirmed -> executing
executing -> execution_finished
executing -> execution_failed
execution_finished -> task_intake or awaiting_result_review
execution_failed -> task_intake or needs_review
```

This documentation pass does not modify schema.

Execution finished does not mean result verified.

## Assistant Message Behavior

Execution started:

```text
Replay execution started for the confirmed plan.
```

Execution completed:

```text
Replay execution completed. Result verification is not implemented in this package.
```

Execution failed:

```text
Replay execution failed before result verification. No recovery was attempted.
```

Execution blocked:

```text
The confirmed plan is not executable because required replay context is missing.
```

The exact text may change during implementation, but it must not claim task
success.

## Explicit Replay Compatibility

`/replay <learned_path_id> <url>` remains an explicit replay command.

Confirmed-plan execution and explicit replay command are related but separate
entry paths:

- explicit replay uses user-provided path id and URL;
- confirmed-plan execution uses a previously confirmed plan and its replay
  context;
- 11.1.6 must not break direct explicit replay;
- 11.1.6 must not break 11.1.5 behavior where `/replay` is blocked while a
  plan is still awaiting confirmation.

## Result Verification Boundary

11.1.6 must not claim business success. It may record:

```text
replay execution completed
```

It must not record:

```text
task succeeded
business result verified
artifact produced
form submission confirmed
```

Those belong to future Result Verification and Task Result Reporter work.

## Test Plan

Future implementation tests should cover:

- execution is blocked when session is not `plan_confirmed`;
- execution is blocked when selected LearnedPath id is missing;
- execution is blocked when target URL / entry context is missing;
- confirmed plan lookup uses existing events and does not reconstruct from raw
  text;
- replay service is called with explicit learned_path_id + URL only when both
  are present;
- started / completed / failed / blocked events are recorded with audit fields;
- replay completed response does not claim task verified;
- explicit `/replay <learned_path_id> <url>` remains compatible;
- `/replay` while `awaiting_confirmation` remains blocked;
- no autonomous, raw HTML, LLM, Task Path Planner re-planning, or recovery
  imports are introduced.

## Evidence Plan

Future implementation review should record:

- changed files;
- execution precondition examples;
- confirmed plan lookup evidence;
- replay invocation evidence;
- missing-context behavior;
- event payload examples;
- assistant message examples;
- explicit replay compatibility behavior;
- result verification non-goal evidence;
- test command output;
- `git diff --check` result.

11.1.6 documentation initialization only runs:

```bash
git diff --check
```

## Out of Scope

- Writing implementation code in this documentation pass.
- Modifying 11.1.1 schemas.
- Modifying 11.1.2 retrieval implementation.
- Modifying 11.1.3 planner implementation.
- Modifying 11.1.4 preview implementation.
- Modifying 11.1.5 confirmation implementation.
- Adding API endpoints.
- Adding CLI commands.
- Calling autonomous run.
- Hidden relearning.
- Reading raw HTML.
- Connecting an LLM provider.
- Real slot binding.
- Form filling.
- Result verification.
- Task Result Reporter implementation.
- Recovery dialogue.
- Teaching mode.
- Browser exploration.
- Creating a 11.1.7 detail directory.

## Open Questions

- Where should target URL / replay entry context be captured for confirmed plan
  execution?
- Should 11.1.6 introduce `executing`, `execution_finished`, and
  `execution_failed` statuses, or use event-only semantics around
  `plan_confirmed`?
- Should execution be triggered by a dedicated confirmation follow-up command,
  a future internal engine event, or an existing dispatch branch?
- Should execution consume a single selected LearnedPath or a multi-step route
  plan once slot binding exists?
- How should replay result summary be shaped so it remains distinct from
  result verification?
