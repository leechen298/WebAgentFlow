# Intent

Status: proposed
Milestone: M12
Type: mixed

## Goal

Define the evidence closure package for M12 recovery work.

12.6 specifies how to validate and record that M12.1-M12.5 remain deterministic
pure recovery services and do not introduce hidden recovery, hidden relearning,
browser continuation, retry execution, replan execution, takeover execution, or
unverified pass claims.

## Motivation

M12 now contains five shipped recovery service layers:

- 12.1 failure classification and recovery boundary;
- 12.2 user abort / stop handling;
- 12.3 recovery proposal generation;
- 12.4 retry / re-run policy evaluation;
- 12.5 recovery conversation flow.

Each layer has focused tests, but M12 needs a single closure package that says
which commands prove the full chain, which evidence counts, which surfaces were
not run, and what decision can be made from the evidence.

Saying "tests passed" is not enough. 12.6 must record commands, result
summaries, scope, excluded surfaces, and unresolved risks. `NOT_RUN` and
`UNVERIFIED` cannot be presented as pass evidence.

## Boundary / Non-goals

12.6 does not add recovery behavior.

This design package does not:

- implement retry, re-run, replan, browser continuation, takeover, teaching
  mode, or LearnedPath write-back;
- add API routes, CLI behavior, frontend UI, DB migrations, workers, or
  conversation runtime integration;
- run `verify-scenario`, autonomous exploration, UI smoke, or E2E by default;
- modify `apps/**` or `packages/**`;
- backfill old 12.0-12.5 iteration package structures.

The later evidence-closure submission may add focused tests only if validation
finds a concrete M12 coverage gap. That addition must be documented with the
gap, affected boundary, command, and result.

## Success Criteria

- M12 deterministic recovery unit suite has a documented command and result
  recording requirement.
- M12 recovery forbidden dependency scan has a documented command and evidence
  requirement.
- M12 review evidence distinguishes API / CLI / UI / E2E / `verify-scenario` /
  autonomous run as `PASS`, `FAIL`, `SKIP`, `NOT_RUN`, or `UNVERIFIED`.
- M12 no-hidden-recovery, no-hidden-relearning, no-browser-continuation, and
  no-retry-execution boundaries have evidence or explicit uncovered-risk notes.
- M12 completion decision can be made as `m12_completed`,
  `m12_completed_with_followups`, `m12_blocked`, or `m12_not_complete`.
- This design package itself records only design-package validation and does
  not declare M12 completed.
