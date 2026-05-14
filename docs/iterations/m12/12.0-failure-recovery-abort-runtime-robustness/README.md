# 12.0 · Failure Recovery / Abort / Runtime Robustness

Status: documentation initialized.

## Required Reading

Before implementing any M12 runtime behavior, read:

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/roadmap.md`
5. `docs/architecture.md`
6. `docs/iterations/m11/README.md`
7. `docs/iterations/m11/m11-plan.md`
8. `docs/iterations/m11/11.1-task-to-path-planning-execution/plan.md`
9. `docs/iterations/m11/11.1.6-execution-via-replay/review.md`
10. `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/review.md`
11. `docs/iterations/m11/11.1.8-task-to-path-tests-and-evidence/review.md`
12. `docs/testing/results/2026-05-13-11-1-8-task-to-path-tests-and-evidence.md`

## Scope

12.0 establishes the M12 safety vocabulary and boundary. It does not implement
runtime behavior yet.

M12 exists because M11.1 deliberately stops before recovery. M11.1 can produce
evidence-bound outcomes, but it must not decide that a failure should be
retried, a path should be relearned, or the browser should continue operating.
Those choices need an explicit, auditable recovery / abort layer.

## Safety Contract

- Failure recovery proposals require user confirmation before execution.
- Recovery is not automatic by default.
- Retry is allowed only when the action is safe, evidence is clear, and the
  user confirms.
- Stop is required when side effects are unknown, state is unsafe, required
  context is missing, or the user aborts.
- Ask user is required when WebAgentFlow lacks context, permission, target page
  state, or verification evidence.
- Re-teach / update LearnedPath can be suggested when path coverage is missing
  or repeated drift shows the path is stale, but write-back is not automatic.
- User abort must immediately pause or stop runtime action and record what was
  known at the time of interruption.

## Relationship to M11.2 Runtime Observation

M11.2 Runtime Observation / Wait-for-change is intentionally separate. 12.0
does not design observation mechanics, wait policies, or runtime signal
collection. M12 can later consume observation evidence when it exists, but the
first M12 boundary is about decisions after known outcomes.

## Acceptance Criteria

- M12 overview and 12.0 documents exist.
- The docs define failure, blocked, uncertain, needs_review, retry, stop, ask
  user, re-teach suggestion, user abort, evidence, and confirmation policy.
- The docs state that recovery is not automatic by default.
- The docs state that hidden recovery, hidden relearning, and browser
  continuation without user consent are not allowed.
- No `12.1-*` directory is created in this initialization.
- No code, tests, package files, or M11 history documents are changed.
