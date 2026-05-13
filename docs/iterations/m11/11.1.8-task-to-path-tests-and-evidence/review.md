# Review and Reflection

This review document is initialized for the future 11.1.8 tests and evidence
review.

## Scope Review Checklist

- [ ] 11.1.8 remains a tests and evidence package.
- [ ] No runtime feature implementation is added by this package.
- [ ] No API endpoint or CLI command is added.
- [ ] No 11.1.9 detail directory is created.
- [ ] M12 / recovery / teaching scope remains future.

## Test Matrix Checklist

- [ ] Domain schema tests are included.
- [ ] Retrieval / ranking tests are included.
- [ ] Task Path Planner tests are included.
- [ ] Planning preview tests are included.
- [ ] Confirmation gate tests are included.
- [ ] Execution via replay tests are included.
- [ ] Task Result Reporter tests are included.
- [ ] Conversation API runtime tests are included.
- [ ] Scoped E2E tests are included.
- [ ] Explicit `/replay` regression tests are included.
- [ ] Negative / blocked / uncertain paths are included.

## API / Unit Regression Checklist

- [ ] Focused API tests pass.
- [ ] Full API pytest result is recorded.
- [ ] Result reporter tests preserve `replay completed != task succeeded`.
- [ ] Confirmation tests preserve explicit consent.
- [ ] Execution tests preserve missing-context blocked behavior.
- [ ] No test depends on LLM provider, autonomous run, or raw HTML planning.

## Scoped E2E Checklist

- [ ] Ordinary task -> planning preview is covered.
- [ ] Planning preview -> awaiting confirmation is covered.
- [ ] Confirm -> plan confirmed is covered.
- [ ] Execute -> replay started / completed is covered.
- [ ] `task_result_reported` event is covered.
- [ ] Final report is uncertain / needs_review when no postcondition evidence
  exists.
- [ ] Event order is recorded and consistent with state transitions.
- [ ] E2E environment caveats are recorded.

## Negative Path Checklist

- [ ] No candidates returns unable-to-plan.
- [ ] Ambiguous confirmation remains awaiting confirmation.
- [ ] `/cancel` returns to task intake.
- [ ] `/replay` while awaiting confirmation is blocked.
- [ ] `/replay` while plan confirmed does not bypass confirmed-plan execution.
- [ ] Execute without target URL is blocked.
- [ ] Replay failed reports failed and no recovery.
- [ ] Replay completed without postcondition evidence reports uncertain /
  needs_review.

## Result Reporter Checklist

- [ ] Reporter does not infer verified success from replay completion.
- [ ] Reporter records evidence used.
- [ ] Reporter records evidence missing.
- [ ] Reporter includes `no_recovery`, `no_autonomous`, and `no_llm` markers.
- [ ] Reporter user-facing message matches event payload outcome.
- [ ] Reporter does not claim artifact production without artifact evidence.

## Explicit Replay Compatibility Checklist

- [ ] Explicit `/replay <learned_path_id> <url>` still works where the existing
  state machine allows it.
- [ ] Explicit `/replay` remains separate from confirmed-plan execution.
- [ ] `/replay` does not bypass `awaiting_confirmation`.
- [ ] `/replay` does not bypass `plan_confirmed` execution intent handling.

## Codex Autonomous Review Checklist

- [ ] Review checks for replay completion treated as task success.
- [ ] Review checks for confirmation bypass.
- [ ] Review checks for `/replay` bypass.
- [ ] Review checks for target URL guessing.
- [ ] Review checks for result reporter success invention.
- [ ] Review checks for failed / uncertain triggering recovery.
- [ ] Review checks for event order mismatch.
- [ ] Review checks for final assistant message contradictions.
- [ ] Review checks for docs status drift.
- [ ] Findings include severity, file / line, reasoning, coverage, and
  recommended fix.

## Evidence Quality Checklist

- [ ] Each evidence record includes command, result, and environment.
- [ ] Evidence distinguishes deterministic, exploratory, manual, and
  review-only results.
- [ ] Evidence records representative API response and event sequence where
  useful.
- [ ] Evidence records assistant message summary where useful.
- [ ] Evidence does not collapse skipped, flaky, blocked, and passed results.
- [ ] Evidence does not use `PASS` without supporting details.

## Environment Caveat Checklist

- [ ] Sandbox restrictions are recorded.
- [ ] Browser permission issues are recorded.
- [ ] Missing local service issues are recorded.
- [ ] DB migration state is recorded.
- [ ] External rerun evidence is recorded when needed.
- [ ] Environment-blocked runs are not counted as product failures.

## Exit Criteria Checklist

- [ ] Focused API tests pass.
- [ ] Full API pytest passes or unresolved failures are documented.
- [ ] Scoped E2E passes or environment-blocked status has rerun evidence.
- [ ] `ruff` is clean for any touched Python files during execution.
- [ ] `git diff --check` is clean.
- [ ] Codex autonomous review has no unresolved P1 / P2.
- [ ] M11.1 docs reflect final statuses.
- [ ] Future scopes remain future.
- [ ] No 11.1.9 detail directory exists.

## Decisions to Confirm Before Execution

- [ ] Final canonical focused API command list.
- [ ] Final scoped E2E command list.
- [ ] Final evidence report filename and location.
- [ ] Whether manual UI smoke is required or supplementary.
- [ ] Whether Codex autonomous review is run once after deterministic tests or
  iterated after fixes.
