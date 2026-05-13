# Review and Reflection

This review document is initialized for the future 11.1.7 implementation
review. It is not a completion report.

## Scope Review Checklist

- [ ] 11.1.7 consumes replay execution evidence from 11.1.6.
- [ ] 11.1.7 does not execute or re-execute replay.
- [ ] 11.1.7 does not call autonomous run.
- [ ] 11.1.7 does not read raw HTML.
- [ ] 11.1.7 does not call LLM provider.
- [ ] 11.1.7 does not call Page Understanding Agent.
- [ ] 11.1.7 does not implement recovery or teaching mode.
- [ ] 11.1.7 does not create 11.1.8 detail docs.

## Verification Input Checklist

- [ ] Verification reads explicit execution evidence.
- [ ] Verification does not infer success from raw user text.
- [ ] Verification does not reconstruct a plan.
- [ ] Verification does not call Task Path Planner again.
- [ ] Verification input includes replay-level status and learned path context
  when available.
- [ ] Missing evidence remains visible in the result.

## Outcome Semantics Checklist

- [ ] `verified` requires postcondition evidence.
- [ ] `failed` is used for replay failure or negative evidence.
- [ ] `uncertain` is used when replay completed but business success is not
  proven.
- [ ] `needs_review` is available when user or later system review is needed.
- [ ] `blocked` is available when execution or verification could not run.
- [ ] `plan_execution_completed` alone does not produce `verified`.

## Postcondition Evidence Checklist

- [ ] Evidence sources are explicit and stable.
- [ ] Artifact references are required before reporting artifact production.
- [ ] Success message or marker evidence is structured, not raw HTML scraping.
- [ ] Missing evidence summary is populated when verification is incomplete.
- [ ] No screenshot payload or raw page payload is stored in events.

## Task Result Reporter Checklist

- [ ] Uses the primary name Task Result Reporter.
- [ ] Agent E appears only as a legacy alias when needed.
- [ ] Report includes execution status and verification outcome.
- [ ] Report includes evidence used and evidence missing.
- [ ] Report does not claim task success unless outcome is `verified`.
- [ ] Report does not claim recovery was attempted.
- [ ] Report does not claim autonomous learning was started.

## Conversation Event Checklist

- [ ] Verification/reporting events are named clearly.
- [ ] Event payload includes learned path id and replay/execution id if
  available.
- [ ] Event payload includes verification outcome.
- [ ] Event payload includes evidence summary and missing evidence summary.
- [ ] Event payload includes `no_recovery` and `no_autonomous` markers.
- [ ] Event payload avoids raw HTML, screenshot payload, and
  user/account/tenant fields.

## State Transition Checklist

- [ ] Verified state is only entered with evidence.
- [ ] Uncertain / needs-review state is valid when evidence is incomplete.
- [ ] Failed state does not trigger recovery automatically.
- [ ] Blocked state or event does not imply execution success.
- [ ] State names fit existing `ConversationStatus` style if new statuses are
  added.

## Assistant Message Checklist

- [ ] Verified message cites evidence.
- [ ] Uncertain message clearly says business result could not be verified.
- [ ] Failed message says no recovery was attempted.
- [ ] Blocked message says verification could not run.
- [ ] Needs-review message asks for review without claiming success.

## Recovery Boundary Checklist

- [ ] Failed / uncertain results do not re-run replay.
- [ ] Failed / uncertain results do not call Failure Recovery Agent.
- [ ] Failed / uncertain results do not trigger autonomous run.
- [ ] Failed / uncertain results do not repair LearnedPath.
- [ ] Failed / uncertain results do not enter teaching mode.

## Regression Checklist

- [ ] 11.1.6 execution tests continue to pass.
- [ ] 11.1.5 confirmation gate behavior is unchanged.
- [ ] Explicit `/replay` compatibility is unchanged.
- [ ] Task planning schema tests continue to pass.
- [ ] No new user/account/tenant fields are introduced.

## Evidence Checklist

- [ ] Implementation review records changed files.
- [ ] Implementation review records verification outcome examples.
- [ ] Implementation review records reporter message examples.
- [ ] Implementation review records event payload examples.
- [ ] Implementation review records test commands and results.
- [ ] Implementation review records remaining limitations.

## Decisions to Confirm Before Implementation

- Which first-version postcondition evidence source is available and stable?
- Should result outcomes be persisted as conversation statuses, events, or both?
- Should Task Result Reporter reuse `AgentEReporterOutput` directly?
- Which event enum names should be added for verification/reporting?
- How should manual verification signals be represented?
- Should `uncertain` and `needs_review` remain distinct in service output,
  conversation state, and user messages?
