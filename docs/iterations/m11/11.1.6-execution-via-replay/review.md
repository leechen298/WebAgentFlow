# Review and Reflection

This review document is initialized for the future 11.1.6 implementation
review.

## Scope Review Checklist

- [ ] Implementation only executes already confirmed plans.
- [ ] Implementation does not reconstruct a plan from raw user text.
- [ ] Implementation does not call Task Path Planner for re-planning.
- [ ] Implementation does not call autonomous run.
- [ ] Implementation does not read raw HTML.
- [ ] Implementation does not perform hidden relearning.
- [ ] Implementation does not connect an LLM provider.
- [ ] Implementation does not implement slot binding, result verification, Task
  Result Reporter, recovery dialogue, or teaching mode.
- [ ] Implementation does not add user / account / tenant fields.

## Execution Precondition Checklist

- [ ] Conversation is in confirmed-but-not-executed semantics.
- [ ] User consent was recorded through 11.1.5.
- [ ] Plan has not already executed.
- [ ] Plan is not cancelled, rejected, or superseded.
- [ ] Selected LearnedPath id is available.
- [ ] Target URL or replay entry context is available.
- [ ] Missing context blocks execution rather than guessing.

## Confirmed Plan Lookup Checklist

- [ ] Confirmed plan is recovered from auditable conversation events.
- [ ] `plan_preview_proposed` evidence is used for selected path / route
  summary.
- [ ] `plan_confirmed` evidence is used for consent.
- [ ] Raw user text is not used to reconstruct a plan.
- [ ] Task Path Planner is not called again.

## Replay Invocation Checklist

- [ ] Existing deterministic replay service / explicit replay hook is reused.
- [ ] No HTTP self-call is introduced if a service-level replay function exists.
- [ ] Replay is called only with explicit `learned_path_id + url` or equivalent
  confirmed entry context.
- [ ] No autonomous execution, hidden relearning, raw HTML planning, LLM, slot
  binding, or invented actions are introduced.

## Missing Context Checklist

- [ ] Missing LearnedPath id records execution-blocked semantics.
- [ ] Missing target URL / entry context records execution-blocked semantics.
- [ ] Assistant message explains that execution context is missing.
- [ ] No replay handler is called when context is incomplete.

## Conversation Event Checklist

- [ ] Execution started event is recorded.
- [ ] Execution completed event is recorded when replay invocation completes.
- [ ] Execution failed event is recorded when replay invocation fails.
- [ ] Execution blocked event is recorded when preconditions are missing.
- [ ] Payload includes learned_path_id and target URL / entry context when
  available.
- [ ] Payload includes no-autonomous marker.
- [ ] Payload includes no result verification marker.
- [ ] Payload does not include raw HTML, screenshots, or user/account/tenant
  fields.

## State Transition Checklist

- [ ] Confirmed plan enters executing semantics only after preconditions pass.
- [ ] Completion state does not imply result verification.
- [ ] Failure state does not attempt recovery.
- [ ] State changes are recorded consistently if implementation extends the
  conversation state machine.

## Assistant Message Checklist

- [ ] Execution-started response says replay execution started.
- [ ] Execution-completed response says result verification is not implemented.
- [ ] Execution-failed response says no recovery was attempted.
- [ ] Execution-blocked response says required context is missing.
- [ ] No response claims task success or business-result verification.

## Explicit Replay Compatibility Checklist

- [ ] Existing `/replay <learned_path_id> <url>` command still works.
- [ ] `/replay` while `awaiting_confirmation` remains blocked by 11.1.5.
- [ ] Confirmed-plan execution and explicit replay remain separate entry paths.

## Result Verification Boundary Checklist

- [ ] Replay completed is not reported as task succeeded.
- [ ] Business result verified is not emitted by 11.1.6.
- [ ] Artifact produced is not emitted by 11.1.6.
- [ ] Task Result Reporter is not invoked.

## Regression Checklist

- [ ] Conversation orchestrator tests pass.
- [ ] Conversation API tests pass if touched.
- [ ] Explicit replay hook tests pass.
- [ ] 11.1.5 confirmation gate tests pass.
- [ ] Replay service tests pass if replay integration is touched.
- [ ] `git diff --check` is clean.

## Evidence Checklist

- [ ] Changed files are listed.
- [ ] Execution precondition examples are recorded.
- [ ] Confirmed plan lookup evidence is recorded.
- [ ] Replay invocation evidence is recorded.
- [ ] Missing-context behavior is recorded.
- [ ] Event payload examples are recorded.
- [ ] Result verification non-goal evidence is recorded.
- [ ] Verification commands and results are recorded.

## Decisions to Confirm Before Implementation

- Exact source of target URL / replay entry context for confirmed plan
  execution.
- Whether new execution statuses are required or event-only semantics are
  sufficient for first implementation.
- Exact event type names for execution started / completed / failed / blocked.
- Whether execution is triggered by dispatch input, engine event, or future
  internal command.
- Replay result summary shape that remains distinct from task verification.
