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

## Implementation Decision Closure

11.1.5 implementation should use the following decisions unless a later review
explicitly updates this document before code changes start:

- explicit confirm moves the session from `awaiting_confirmation` to
  `plan_confirmed`;
- `plan_confirmed` means the user consented and the plan is ready for a future
  execution package, but replay has not run;
- cancel / abort / stop returns the session to `task_intake` after recording a
  cancellation decision;
- reject / no returns the session to `task_intake` after recording a rejection
  decision;
- ambiguous input keeps the session in `awaiting_confirmation` and asks for an
  explicit decision;
- new task text while awaiting confirmation does not silently replace the
  pending preview; it records clarification / revision intent and asks the user
  to cancel or reject the current preview first;
- `/replay <learned_path_id> <url>` while awaiting confirmation is blocked until
  the pending preview is resolved;
- 11.1.5 records consent / cancellation / rejection / clarification evidence
  only and never executes replay.

## Confirmation Input Classification

MVP classification should be deterministic:

- confirm: `confirm`, `yes`, `proceed`, `continue`, `确认`, `继续`
- cancel / abort / stop: `cancel`, `abort`, `stop`, `取消`, `停止`
- reject: `reject`, `no`, `不要`
- other free text: clarification or revision intent

No LLM classifier is introduced in 11.1.5. Ambiguous text does not count as
consent.

## Consent Gate State Transitions

Future implementation should add or use an explicit `plan_confirmed` status
for confirmed-but-not-executed semantics. The implementation must inspect
current `ConversationStatus` and `next_state()` before changing schema, but the
intended first implementation behavior is:

- `awaiting_confirmation -> plan_confirmed` when the user explicitly confirms;
- `awaiting_confirmation -> task_intake` when the user cancels or rejects;
- `awaiting_confirmation -> awaiting_confirmation` for ambiguous input or
  revision intent that still needs an explicit cancel / reject / confirm
  decision.

`plan_confirmed` means:

- user consent has been recorded;
- the pending plan is ready for a future execution package;
- replay has not executed;
- no browser operation has occurred.

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
auditable. The first implementation should use the conservative policy:

- do not silently replace the pending preview;
- do not re-run retrieval or planning;
- record clarification / revision intent;
- ask the user to cancel or reject the current pending plan before submitting a
  new task;
- keep the session in `awaiting_confirmation`.

## Event Recording Design

Event semantics to plan for:

- `plan_confirmed`
- `plan_cancelled`
- `plan_rejected`
- `confirmation_clarification_requested`
- `explicit_replay_blocked_by_pending_confirmation`

`plan_revision_requested` remains optional future scope for a later package or a
follow-up 11.1.5 hardening pass. The first 11.1.5 implementation can record
revision-like input through `confirmation_clarification_requested`.

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

If `/replay <learned_path_id> <url>` is entered while a plan preview is awaiting
confirmation, the first implementation must block it until the pending preview
is resolved. It should:

- not call the replay handler;
- append an assistant message that asks the user to confirm, cancel, or reject
  the current pending plan first;
- record `explicit_replay_blocked_by_pending_confirmation` or equivalent event
  semantics;
- keep the session in `awaiting_confirmation`.

Confirmation input must never bypass this decision and execute replay.

## Implementation Boundary

Future implementation may add:

```text
apps/api/app/services/conversation/confirmation.py
```

Potential contracts:

```text
PlanConfirmationDecision
PlanConfirmationResult
PlanConfirmationService
```

The confirmation service is responsible only for classifying and representing
user input while a session is in `awaiting_confirmation`. It must not call
replay, retrieval, the Task Path Planner, autonomous run, raw HTML readers, or
an LLM provider.

The orchestrator should:

- check `session.status == awaiting_confirmation` before normal command
  handling branches that could trigger planning preview;
- route awaiting-confirmation input through the confirmation service first;
- block `/replay` from bypassing the pending preview;
- record messages, events, and status updates.

The router should continue using the existing dispatch endpoint. 11.1.5 does
not add an API endpoint or CLI command.

## Test Plan

Future implementation tests should cover:

- explicit confirm records consent / ready-for-execution and does not call
  replay;
- explicit confirm transitions to `plan_confirmed` or the chosen exact schema
  spelling;
- cancel / abort / stop cancels pending preview and records event;
- reject / no rejects pending preview and records event;
- ambiguous input asks for clarification and does not confirm;
- new task while awaiting confirmation records clarification / revision intent,
  keeps the session awaiting confirmation, and does not re-run planning;
- `/replay` while awaiting confirmation is blocked, records an event, and does
  not call the replay handler;
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

- Exact schema spelling for `plan_confirmed` must be confirmed during
  implementation when updating `ConversationStatus`.
- Exact `ConversationEventType` enum additions should be verified against
  existing naming conventions before code changes.
- Whether route summary is included in every assistant response after a
  confirmation-related decision can remain an implementation detail as long as
  the event payload remains auditable.
