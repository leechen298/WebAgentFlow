# Review and Reflection

This review document is initialized for the future 11.1.5 implementation
review.

## Scope Review Checklist

- [ ] Implementation only handles confirmation / consent decisions.
- [ ] Implementation does not execute replay.
- [ ] Implementation does not call autonomous run.
- [ ] Implementation does not read raw HTML.
- [ ] Implementation does not perform hidden relearning.
- [ ] Implementation does not connect an LLM provider.
- [ ] Implementation does not implement real slot binding.
- [ ] Implementation does not implement result verification, Task Result
  Reporter, recovery dialogue, or teaching mode.
- [ ] Implementation does not add user / account / tenant fields.

## Confirmation Input Checklist

- [ ] Confirm inputs are deterministic and explicit.
- [ ] Cancel / abort / stop inputs are deterministic and explicit.
- [ ] Reject inputs are deterministic and explicit.
- [ ] Ambiguous input is not treated as consent.
- [ ] Free text while awaiting confirmation follows the chosen revision policy.
- [ ] No LLM classifier is required.

## Consent Semantics Checklist

- [ ] Confirm records consent or ready-for-execution semantics.
- [ ] Confirm does not execute replay.
- [ ] Cancel stops the pending preview.
- [ ] Reject declines the pending preview.
- [ ] High-risk / flaky / provisional plans still require explicit confirmation.
- [ ] User decision is auditable.

## State Transition Checklist

- [ ] `awaiting_confirmation` is the only entry point for the gate.
- [ ] Confirmed-but-not-executed state semantics are explicit.
- [ ] Cancel / reject / revision state semantics are explicit.
- [ ] Clarification-needed behavior is explicit.
- [ ] State changes are recorded consistently if implementation extends the
  conversation state machine.

## Event Recording Checklist

- [ ] Plan confirmation event is recorded.
- [ ] Plan cancellation event is recorded.
- [ ] Plan rejection event is recorded.
- [ ] Clarification-requested event is recorded.
- [ ] Revision-requested event is recorded if new task input is supported.
- [ ] Event payloads preserve selected path, route summary, warnings, risk
  hints, confirmation requirements, and user decision input.
- [ ] Event payloads explicitly indicate that replay was not executed.

## Assistant Message Checklist

- [ ] Confirm response says the plan is confirmed for future execution, not
  executed.
- [ ] Cancel response says the pending plan is cancelled.
- [ ] Reject response says the plan was not accepted and was not executed.
- [ ] Ambiguous response asks for explicit confirm / cancel / reject / revision.
- [ ] Revision response follows the chosen pending-preview policy.

## Explicit Replay Compatibility Checklist

- [ ] Existing explicit replay command behavior remains compatible.
- [ ] `/replay` while awaiting confirmation follows the documented policy.
- [ ] Confirmation input cannot bypass consent and execute replay.
- [ ] Existing explicit replay tests still pass.

## Boundary Checklist

- [ ] No replay / autonomous / LLM / raw HTML imports are introduced.
- [ ] No new API endpoint is added in 11.1.5.
- [ ] No CLI command is added.
- [ ] No 11.1.6 detail directory is created.
- [ ] Existing 11.1.4 planning preview behavior remains compatible.

## Regression Checklist

- [ ] Conversation dispatcher / orchestrator tests pass.
- [ ] Explicit replay hook tests pass.
- [ ] Task planning preview tests pass.
- [ ] Conversation API / CLI tests pass if touched.
- [ ] `git diff --check` is clean.

## Evidence Checklist

- [ ] Changed files are listed.
- [ ] Input classification examples are recorded.
- [ ] State transition examples are recorded.
- [ ] Event payload examples are recorded.
- [ ] Replay non-execution evidence is recorded.
- [ ] Verification commands and results are recorded.

## Decisions to Confirm Before Implementation

- Which status represents confirmed-but-not-executed.
- Which new `ConversationEventType` values are needed, if any.
- Whether new task input while awaiting confirmation requires explicit
  cancellation or can supersede the pending preview with a revision event.
- Whether `/replay <learned_path_id> <url>` while awaiting confirmation is
  rejected until cancellation or treated as a separate explicit command with
  auditable cancellation / replacement of the pending preview.
- Whether route summary is included in every assistant response after a
  confirmation-related decision.
