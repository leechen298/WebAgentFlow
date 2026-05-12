# Review and Reflection

This review document is initialized for the future 11.1.3 implementation
review.

## Scope Review Checklist

- Task Path Planner is the primary name.
- Agent D appears only as a legacy alias when needed.
- Implementation does not execute replay.
- Implementation does not call autonomous run.
- Implementation does not read raw HTML.
- Implementation does not perform hidden relearning.
- Implementation does not connect an LLM provider without a separate bounded
  design.
- Implementation does not add CLI or API surface unless a later package
  explicitly plans it.

## Contract Compatibility Checklist

- Inputs align with 11.1.1 `TaskIntent` and `LearnedPathCandidate`.
- Output aligns with 11.1.1 planner output contract.
- No user / account / tenant fields are introduced.
- 11.1.2 retrieval remains a separate dependency, not planner-internal logic.

## Planner Determinism Checklist

- Candidate selection is deterministic.
- Tie handling is deterministic.
- No external search, embeddings, or vector DB are required.
- No LLM call is required for default behavior.

## Candidate Selection Checklist

- Empty candidate list has explicit unable-to-plan semantics.
- Deprecated candidates are ignored defensively.
- Confirmed candidates are preferred when other signals are acceptable.
- Provisional candidates preserve uncertainty.
- Flaky candidates preserve warnings and require confirmation.
- Ambiguous candidate sets require confirmation instead of silent execution.

## RoutePlan Mapping Checklist

- RoutePlan is generated only by future implementation, not this documentation
  pass.
- Route steps reference known LearnedPath ids.
- Planner does not invent browser actions outside path assets.
- `match_reasons` and warnings remain traceable.

## Risk / Warning / Confirmation Checklist

- Flaky / drift / negative evidence warnings are propagated.
- Risky actions require confirmation.
- Destructive, external-send, bulk-modification, and permission-modification
  plans are not silently executable.
- Slot Binding remains future scope.

## Regression Checklist

- 11.1.1 schema tests still pass.
- 11.1.2 retrieval tests still pass if implementation depends on retrieval.
- No autonomous / replay / LLM imports are introduced in planner core.
- `git diff --check` is clean.

## Evidence Checklist

- Implementation review records changed files.
- Tests and command outputs are recorded.
- Boundary verification is recorded.
- Any deviation from this design is explained.

## Decisions to Confirm Before Implementation

- Exact unable-to-plan representation.
- Ambiguous candidate threshold.
- Whether future Slot Binding must happen before executable route plans.
- Whether the first implementation remains fully deterministic or only
  documents a future bounded LLM adapter.
