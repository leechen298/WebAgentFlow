# Implementation Plan

## Inputs and Dependencies

Future implementation should inspect the current conversation orchestrator and
state transition helpers before choosing final module boundaries. Expected
dependencies:

- `awaiting_confirmation` status from the M11 conversation schema;
- planning preview assistant message and events from 11.1.4;
- existing slash command parser and state transition helpers;
- conversation session / message / event repository.

Potential implementation locations:

- inspect existing conversation orchestrator before choosing the final path;
- likely under `apps/api/app/services/conversation/` for confirmation handling;
- planning preview remains under `apps/api/app/services/task_planning/`;
- tests likely live under `apps/api/tests/`.

Do not create code files in this documentation pass.

## Awaiting Confirmation Entry Condition

The gate only applies when a conversation is in `awaiting_confirmation` and a
planning preview exists. The implementation should not infer confirmation state
from free text alone.

The pending preview should be auditable through existing conversation messages
and preview events before any user decision is accepted.

## Confirmation Input Classification

MVP classification should be deterministic:

- confirm: `confirm`, `yes`, `proceed`, `continue`, `确认`, `继续`
- cancel / abort / stop: `cancel`, `abort`, `stop`, `取消`, `停止`
- reject: `reject`, `no`, `不要`
- other free text: clarification or revision intent

No LLM classifier is introduced in 11.1.5. Ambiguous text does not count as
consent.

## Consent Gate State Transitions

Future implementation may need new statuses or may reuse existing status with
events. The implementation must inspect current `ConversationStatus` and
`next_state()` before changing schema.

Candidate semantics:

- `awaiting_confirmation -> plan_confirmed` or equivalent ready-for-execution
  semantics when the user explicitly confirms;
- `awaiting_confirmation -> task_intake` when the user cancels, rejects, or
  requests revision;
- `awaiting_confirmation -> clarification_needed` or equivalent event-only
  semantics for ambiguous input.

No transition in 11.1.5 executes replay.

## Cancel / Abort / Reject Behavior

Cancel / abort / stop input should stop the pending preview and record an
auditable cancellation decision. Reject / no input should record that the user
declined the plan and can describe a new task.

The assistant response should clearly say that no execution occurred.

## Ambiguous Input Behavior

Ambiguous input should ask the user to explicitly confirm, cancel, reject, or
revise the task. It should not move to ready-for-execution.

Examples of ambiguous input:

- `maybe`
- `looks ok?`
- unrelated free text that does not clearly revise the task
- partial phrases that are not in the deterministic allowlist

## New Task While Awaiting Confirmation

New free-text task input while a preview is pending must be explicit and
auditable. Future implementation should choose one policy:

- require the user to cancel the existing preview before submitting a new task;
- or record a plan revision request, cancel / supersede the pending preview, and
  return to task intake.

The first implementation should not silently replace a pending preview without
an event.

## Event Recording Design

Event semantics to plan for:

- `plan_confirmed`
- `plan_cancelled`
- `plan_rejected`
- `confirmation_clarification_requested`
- `plan_revision_requested`

Payload should preserve:

- selected path id;
- route summary;
- warnings;
- risk hints;
- confirmation requirements;
- user decision input;
- prior preview event id if available;
- no replay execution marker.

This documentation pass does not add schema values. If implementation adds
`ConversationEventType` values, tests must cover them.

## Assistant Message Behavior

Confirm:

- say the plan is confirmed or ready for future execution;
- state that replay has not executed.

Cancel / abort:

- say the pending plan is cancelled;
- return to task intake or equivalent state.

Reject:

- say the plan was not accepted and was not executed;
- invite the user to describe a revised task.

Ambiguous input:

- ask for explicit confirm, cancel, reject, or revised task.

Revision intent:

- record revision intent;
- either require cancellation first or route back to task intake according to
  the final implementation decision.

## Explicit Replay Compatibility

`/replay <learned_path_id> <url>` remains an explicit replay command. 11.1.5
does not change the replay hook and does not execute replay.

Open implementation decision: if `/replay <learned_path_id> <url>` is entered
while a plan preview is awaiting confirmation, choose one policy before coding:

- reject it until the pending preview is cancelled;
- or treat it as a separate explicit command with auditable cancellation /
  replacement of the pending preview.

Confirmation input must never bypass this decision and execute replay.

## Test Plan

Future implementation tests should cover:

- explicit confirm records consent / ready-for-execution and does not call
  replay;
- cancel / abort / stop cancels pending preview and records event;
- reject / no rejects pending preview and records event;
- ambiguous input asks for clarification and does not confirm;
- new task while awaiting confirmation follows the chosen revision policy;
- `/replay` while awaiting confirmation follows the explicitly chosen policy;
- assistant messages say no execution occurred;
- event payload preserves selected path, route summary, warnings, risk hints,
  confirmation requirements, and user decision input;
- no replay, autonomous, raw HTML, LLM, CLI, or browser-operation imports are
  introduced;
- existing 11.1.4 preview, explicit replay, conversation API, and CLI tests
  still pass.

## Evidence Plan

Future implementation review should record:

- changed files;
- input classification examples;
- state transition behavior;
- event payload examples;
- assistant message examples;
- explicit replay compatibility behavior;
- boundary verification;
- test command output;
- `git diff --check` result.

11.1.5 documentation initialization only runs:

```bash
git diff --check
```

## Out of Scope

- Writing implementation code.
- Modifying 11.1.1 schemas.
- Modifying 11.1.2 retrieval implementation.
- Modifying 11.1.3 planner implementation.
- Modifying 11.1.4 preview implementation.
- Adding API endpoints.
- Adding CLI commands.
- Executing replay.
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
- Browser operation.
- Creating a 11.1.6 detail directory.

## Open Questions

- Which status represents confirmed-but-not-executed: a new status, existing
  `task_intake`, or event-only semantics?
- Which event types should be added to `ConversationEventType`, if any?
- Should a new task while awaiting confirmation require explicit cancellation,
  or can it create a revision event and supersede the pending preview?
- How should `/replay <learned_path_id> <url>` behave while a preview is
  awaiting confirmation?
- Should the assistant response include a compact route summary on every
  confirmation-related message?
