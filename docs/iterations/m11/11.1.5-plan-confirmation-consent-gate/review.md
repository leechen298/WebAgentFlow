# Review and Reflection

This review document is initialized for the future 11.1.5 implementation
review.

## Implementation Decision Closure

These decisions close the initial 11.1.5 open questions before implementation.
They are still documentation-stage decisions; this package remains
`documentation initialized` until code and tests are implemented.

- Confirmed-but-not-executed status: future implementation should use
  `plan_confirmed`. It means user consent is recorded and the plan is ready for
  a future execution package, but replay has not run.
- Confirm transition: `awaiting_confirmation -> plan_confirmed`.
- Cancel transition: `awaiting_confirmation -> task_intake`, with a
  `plan_cancelled` event and an assistant message that no execution occurred.
- Reject transition: `awaiting_confirmation -> task_intake`, with a
  `plan_rejected` event and an assistant message that the plan was not accepted
  or executed.
- Ambiguous input: keep `awaiting_confirmation`, record
  `confirmation_clarification_requested`, and ask the user for explicit confirm
  / cancel / reject. Ambiguous input is never consent.
- New task while awaiting confirmation: do not silently replace the pending
  preview and do not re-run planning. Record clarification / revision intent,
  ask the user to cancel or reject the current plan first, and keep
  `awaiting_confirmation`.
- `/replay` while awaiting confirmation: block it until the pending preview is
  resolved. Do not call the replay handler. Record
  `explicit_replay_blocked_by_pending_confirmation` or equivalent event
  semantics and keep `awaiting_confirmation`.
- Event semantics: first implementation should plan for `plan_confirmed`,
  `plan_cancelled`, `plan_rejected`,
  `confirmation_clarification_requested`, and
  `explicit_replay_blocked_by_pending_confirmation`.
  `plan_revision_requested` remains optional future scope.
- Implementation boundary: future code may add
  `apps/api/app/services/conversation/confirmation.py` with
  `PlanConfirmationDecision`, `PlanConfirmationResult`, and
  `PlanConfirmationService` contracts. That service only classifies
  awaiting-confirmation input and must not call replay, retrieval, the Task Path
  Planner, autonomous run, raw HTML readers, or an LLM provider.
- Orchestrator boundary: the confirmation branch should run before planning
  preview for sessions already in `awaiting_confirmation`, and it should block
  `/replay` from bypassing the pending preview.
- Router boundary: continue using the existing dispatch endpoint. Do not add an
  API endpoint or CLI command in 11.1.5.

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

- Confirm the exact schema spelling for `plan_confirmed` when updating
  `ConversationStatus`.
- Confirm exact `ConversationEventType` enum names against existing naming
  conventions before code changes.
- Confirm whether route summary appears in every assistant response or only in
  event payloads; either way, the event payload must remain auditable.
