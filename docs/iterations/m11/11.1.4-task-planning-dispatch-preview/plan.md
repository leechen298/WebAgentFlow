# Implementation Plan

## Inputs and Dependencies

Future implementation should inspect the current conversation dispatcher before
choosing final module boundaries. The expected dependencies are:

- conversation session / message / event store from M11.0;
- explicit replay command hook from 11.0.6;
- `TaskIntent` and planner schemas from 11.1.1;
- LearnedPath retrieval / ranking from 11.1.2;
- Task Path Planner service from 11.1.3.

Potential implementation locations:

- inspect existing conversation dispatcher / orchestrator service before
  choosing the final path;
- likely under `apps/api/app/services/conversation/` for dispatch integration;
- task planning services remain under `apps/api/app/services/task_planning/`;
- tests likely live under `apps/api/tests/`.

Do not create code files in this documentation pass.

## Conversation Dispatch Entrypoint

The future preview path should be triggered from the conversation runtime input
flow. It must keep command handling explicit:

- slash commands continue through the command parser and existing command
  behavior;
- `/replay <learned_path_id> <url>` remains the explicit replay command path;
- ordinary free-text user input may enter task planning preview when state and
  command semantics allow it.

The dispatch integration should coordinate services without turning the
conversation orchestrator into retrieval, planning, execution, and reporting
logic all at once.

## Ordinary Task Request Detection

MVP detection can be conservative:

- input that is not a slash command may be treated as ordinary task text;
- malformed slash commands should not fall through into task planning preview;
- empty or whitespace-only input should return a validation error or existing
  invalid command semantics;
- explicit replay commands must never be interpreted as ordinary task requests.

No LLM classifier is introduced in 11.1.4.

## TaskIntent Construction

The MVP construction should be deterministic and minimal:

- `raw_text` preserves the original user input;
- `normalized_goal` is optional and should not be invented without a
  deterministic rule;
- `normalization_source` remains `none` or the documented deterministic source;
- optional page / scenario hints may be populated only from explicit metadata or
  existing conversation context if available;
- no slot binding occurs;
- no business parameter inference occurs.

The implementation should avoid adding user / account / tenant fields.

## Retrieval + Planner Orchestration

The future orchestration path should stay layered:

```text
user input
-> TaskIntent
-> LearnedPathRetrievalService.retrieve_candidates(...)
-> TaskPathPlanner.plan(task_intent, candidates)
-> planning preview response
```

Retrieval remains responsible for catalog lookup and ranking. Task Path Planner
remains responsible for selecting from passed candidates and producing planner
output. The dispatcher coordinates both and records conversation artifacts.

## Planning Preview Message Shape

The preview should produce an assistant-facing conversation message or response
hint with enough structure for a later UI or CLI to display:

- planning status: plan proposed, confirmation needed, ambiguous, or
  unable-to-plan;
- selected LearnedPath id when a candidate was selected;
- route-plan summary when available;
- warnings and risk hints;
- confirmation requirements;
- unable-to-plan reason when no route is available.

The preview must not claim that execution happened.

## Conversation Event Recording

The future implementation should record auditable events for planning preview.
Possible event names can be finalized during implementation, but the audit
payload should preserve:

- task intent summary;
- retrieved candidate ids and relevant match reasons;
- selected candidate id if any;
- planner output status;
- warnings and risk hints;
- confirmation requirements;
- unable-to-plan reason;
- no replay execution marker.

The event payload should avoid full screenshots, raw HTML, and user / account /
tenant fields.

## Confirmation Pending Semantics

When the planner output requires confirmation, the conversation should enter a
clear planning-pending state or equivalent status. The exact state name can be
finalized during implementation, but the semantics should be:

- a plan preview exists;
- execution has not started;
- user confirmation or clarification is required before any replay execution;
- cancellation or new task input should remain auditable.

This documentation pass does not implement state machine changes.

## No-Candidate / Unable-to-Plan Semantics

When no candidates are available:

- return unable-to-plan semantics;
- create a clear user-readable response;
- record an event;
- do not create a fake `RoutePlan`;
- do not call autonomous run;
- do not perform hidden relearning;
- do not operate the browser.

The later caller can decide whether to ask the user for more details or route
to a future teaching / learning flow, but 11.1.4 does not implement that.

## Test Plan

Future implementation tests should cover:

- ordinary free text triggers planning preview, not replay;
- explicit `/replay <learned_path_id> <url>` remains compatible and does not
  enter task planning preview;
- malformed slash command does not fall through to planning preview;
- `TaskIntent.raw_text` preserves the original input;
- deterministic metadata-based hints are preserved when available;
- retrieval service is called with `TaskIntent`;
- Task Path Planner is called with retrieved candidates;
- no candidates produce unable-to-plan response and event;
- planner output with confirmation requirements produces confirmation-pending
  semantics;
- warnings / risk hints / match reasons are preserved in message and event
  output;
- no replay, autonomous, raw HTML, LLM, CLI, or browser-operation imports are
  introduced;
- existing explicit replay, conversation API, conversation CLI, retrieval, and
  planner tests still pass.

## Evidence Plan

Future implementation review should record:

- changed files;
- dispatch entrypoint behavior;
- explicit replay compatibility evidence;
- `TaskIntent` construction examples;
- retrieval + planner orchestration behavior;
- preview message / event shape;
- no-candidate behavior;
- boundary verification;
- test command output;
- `git diff --check` result.

11.1.4 documentation initialization only runs:

```bash
git diff --check
```

## Out of Scope

- Writing implementation code.
- Modifying 11.1.1 schemas.
- Modifying 11.1.2 retrieval implementation.
- Modifying 11.1.3 planner implementation.
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
- Creating a 11.1.5 detail directory.

## Open Questions

- Which conversation status name should represent planning preview pending:
  `plan_preview_pending`, `awaiting_confirmation`, or an existing status?
- Should the preview be stored as an assistant message, an event only, or both?
- Should retrieved candidate ids be stored in full, limited to top N, or stored
  only through summary fields?
- Should ordinary task preview be exposed through the existing dispatch endpoint
  only, or later through a dedicated preview endpoint?
- How should later Slot Binding attach to an existing planning preview without
  rewriting the original audit trail?
