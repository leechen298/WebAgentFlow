# Review and Reflection

This review document is initialized for the future 11.1.4 implementation
review.

## Scope Review Checklist

- [ ] Implementation only connects conversation runtime to planning preview.
- [ ] Implementation does not execute replay.
- [ ] Implementation does not call autonomous run.
- [ ] Implementation does not read raw HTML.
- [ ] Implementation does not perform hidden relearning.
- [ ] Implementation does not connect an LLM provider.
- [ ] Implementation does not implement real slot binding.
- [ ] Implementation does not implement result verification, recovery dialogue,
  or teaching mode.
- [ ] Implementation does not add user / account / tenant fields.

## Conversation Integration Checklist

- [ ] Ordinary free-text task requests can enter the preview path.
- [ ] Slash command behavior remains explicit.
- [ ] Malformed slash commands do not fall through to task planning preview.
- [ ] Conversation message / event records the preview output.
- [ ] Planner output remains reviewable by later confirmation / execution
  layers.

## Explicit Replay Compatibility Checklist

- [ ] `/replay <learned_path_id> <url>` behavior is unchanged.
- [ ] Replay hook is not called for ordinary task preview.
- [ ] Task planning preview does not wrap replay result as a plan execution.
- [ ] Existing replay tests still pass.

## TaskIntent Construction Checklist

- [ ] `raw_text` preserves original user input.
- [ ] `normalized_goal` is optional and deterministic-only.
- [ ] Page / scenario hints are populated only from explicit metadata or
  existing context.
- [ ] No slot binding or business parameter inference occurs.
- [ ] No LLM classifier is required.

## Retrieval / Planner Orchestration Checklist

- [ ] Retrieval service receives `TaskIntent`.
- [ ] Task Path Planner receives ranked candidates from retrieval.
- [ ] Dispatcher coordinates retrieval and planning without merging their
  responsibilities.
- [ ] Planner does not call retrieval internally.

## Planning Preview Output Checklist

- [ ] Preview response includes plan-proposed / confirmation-needed /
  ambiguous / unable-to-plan semantics.
- [ ] Selected LearnedPath id is preserved when available.
- [ ] Warnings are preserved.
- [ ] Risk hints are preserved.
- [ ] Match reasons are preserved.
- [ ] Confirmation requirements are preserved.
- [ ] Preview does not claim execution.

## Confirmation State Checklist

- [ ] Confirmation-pending semantics are explicit.
- [ ] Execution is blocked until future confirmation / consent logic allows it.
- [ ] User cancellation or clarification remains auditable.
- [ ] State changes are recorded consistently if the implementation extends the
  conversation state machine.

## No-Candidate Checklist

- [ ] No candidates returns unable-to-plan.
- [ ] No fake `RoutePlan` is generated.
- [ ] No autonomous learning starts automatically.
- [ ] No hidden relearning starts automatically.
- [ ] No browser operation occurs.
- [ ] User-facing response is clear and auditable.

## Boundary Checklist

- [ ] No replay / autonomous / LLM / raw HTML imports.
- [ ] No new API endpoint is added in 11.1.4.
- [ ] Existing conversation dispatch endpoint behavior may be extended only for
  planning preview.
- [ ] Dedicated planning preview API remains future scope.
- [ ] No CLI command is added.
- [ ] No 11.1.5 detail directory is created.
- [ ] Existing M11.0 conversation behavior remains compatible.

## Regression Checklist

- [ ] Conversation dispatcher / orchestrator tests pass.
- [ ] Explicit replay hook tests pass.
- [ ] Task planning schema tests pass.
- [ ] LearnedPath retrieval tests pass.
- [ ] Task Path Planner tests pass.
- [ ] `git diff --check` is clean.

## Evidence Checklist

- [ ] Changed files are listed.
- [ ] Dispatch behavior examples are recorded.
- [ ] Preview message / event payload examples are recorded.
- [ ] Boundary checks are recorded.
- [ ] Verification commands and results are recorded.

## Decisions to Confirm Before Implementation

- Which conversation status represents planning preview pending.
- Whether preview output is stored as assistant message, event, or both.
- Whether a dedicated planning preview event type is needed.
- Whether retrieved candidates are stored as ids, summaries, or full candidate
  payloads.
- Whether ordinary task preview remains only behind the existing dispatch
  endpoint in the first implementation.
