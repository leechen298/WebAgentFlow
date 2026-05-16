# 12.6 · Recovery Tests and Evidence

Status: proposed
Milestone: M12
Type: mixed
Current stage: evidence closure design package

12.6 defines how M12 recovery / abort / proposal / retry-policy /
conversation-flow work is proven complete. It is an evidence closure package,
not a new recovery feature.

This design package prepares the next evidence-closure submission. The next
submission may run tests, collect command-backed evidence, update review /
testing reports, and add focused tests only if a coverage gap is found.

## Package Documents

- `intent.md` - goal, motivation, boundary, success criteria.
- `contract.md` - evidence closure concepts, result states, not-run rules, and
  completion decision contract.
- `technical-design.md` - evidence report shape, validation command design, and
  recovery boundary coverage.
- `test-plan.md` - required M12 recovery suite, ruff, diff check, and not-run
  table requirements.
- `plan.md` - design-package steps and later evidence-closure steps.
- `review.md` - design-package validation evidence and follow-ups.

## Design Gate

- [x] `intent.md` exists.
- [x] `contract.md` exists and defines evidence closure semantics.
- [x] `technical-design.md` exists because 12.6 is mixed and prepares evidence
  closure work.
- [x] `test-plan.md` exists because 12.6 closes recovery / abort / retry /
  conversation evidence.
- [x] `plan.md` matches the contract, technical design, and test plan.
- [ ] Evidence closure has been executed.
- [ ] M12 completion decision has been recorded from command-backed evidence.

## Current Status

- 12.1 classifier shipped as a deterministic recovery boundary service.
- 12.2 abort handler shipped as a deterministic stop handling service.
- 12.3 proposal generator shipped as a deterministic non-executable recovery
  proposal service.
- 12.4 retry policy evaluator shipped as a deterministic policy service.
- 12.5 recovery conversation flow shipped as a deterministic non-execution
  conversation response service.
- 12.6 is currently a design package for M12 evidence closure.

## Evidence Boundary

Evidence closure is not new feature expansion.

12.6 must prove boundaries with command-backed evidence or explicitly mark
missing coverage as `not run / unverified`. A statement in docs is not runtime
evidence. A test that was not run is not a pass.

Default exclusions for this design package:

- no API / CLI expansion;
- no DB migration;
- no frontend UI;
- no retry / replan / takeover execution;
- no browser continuation;
- no hidden relearning;
- no `verify-scenario`;
- no autonomous run;
- no E2E / UI smoke.

## Completion Guard

This design package must not declare `m12_completed` or
`m12_completed_with_followups`. Those decisions belong only to the later
evidence-closure submission after required validation has actually run and
been recorded.
