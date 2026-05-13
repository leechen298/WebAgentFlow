# Implementation Plan

## Inputs and Dependencies

11.1.8 depends on the implemented M11.1 packages:

- 11.1.1 Task Planning Domain Contract.
- 11.1.2 LearnedPath Retrieval and Ranking.
- 11.1.3 Task Path Planner MVP.
- 11.1.4 Task Planning Dispatch Preview.
- 11.1.5 Plan Confirmation and Consent Gate.
- 11.1.6 Execution via Replay.
- 11.1.7 Result Verification and Task Result Reporter.

Before executing tests, confirm any latest 11.1.7 focused fixes have landed or
are explicitly recorded as open risks. 11.1.8 should not assume unresolved
11.1.7 code is final.

Potential evidence locations:

- `docs/testing/results/`
- `docs/testing/e2e/`
- `docs/testing/features/`

## Test Matrix

The future 11.1.8 execution should cover:

- domain schema tests;
- LearnedPath retrieval / ranking tests;
- Task Path Planner tests;
- planning preview tests;
- confirmation gate tests;
- execution via replay tests;
- Task Result Reporter tests;
- conversation API runtime tests;
- scoped E2E tests;
- explicit `/replay` regression tests;
- negative / blocked / uncertain paths.

The matrix should map each test command to the package behavior it protects.

## Deterministic API / Unit Test Plan

The deterministic regression plan should include focused commands for:

- task planning schemas;
- retrieval and ranking;
- planner output;
- planning preview service and conversation integration;
- confirmation decision handling;
- execution gate and replay invocation boundary;
- result reporter outcome derivation and event payloads;
- conversation API dispatch paths.

These tests should not call autonomous run, browser exploration, raw HTML
planning, Page Understanding Agent, or an LLM provider.

## Scoped E2E Plan

The scoped E2E plan should cover the representative happy-path wiring without
claiming business success:

```text
ordinary task
-> planning preview
-> awaiting_confirmation
-> confirm
-> plan_confirmed
-> execute
-> replay started
-> replay completed
-> task_result_reported
-> uncertain / needs_review report
```

Expected evidence:

- session status progression;
- event sequence;
- dispatch responses;
- final assistant message;
- `task_result_reported` payload with `verification_outcome=uncertain`;
- no unsupported task success assertion.

## Negative / Blocked Path Plan

Negative coverage should include:

- no candidates -> unable-to-plan;
- ambiguous confirmation input -> remains `awaiting_confirmation`;
- `/cancel` -> `task_intake`;
- `/replay` while `awaiting_confirmation` -> blocked;
- `/replay` while `plan_confirmed` -> does not bypass confirmed-plan flow;
- execute without target URL -> `plan_execution_blocked`;
- replay failed -> failed report, no recovery;
- replay completed without postcondition evidence -> uncertain / needs_review.

Blocked and uncertain are valid outcomes. They should not be collapsed into
pass/fail summaries without evidence.

## Result Reporter Validation Plan

Reporter tests should prove:

- `plan_execution_completed` alone does not mean verified;
- no postcondition evidence defaults to `uncertain` / `needs_review`;
- failed replay evidence reports `failed`;
- blocked execution reports `blocked`;
- report payload includes evidence used and evidence missing;
- user-facing messages do not claim success unless outcome is `verified`;
- `no_recovery`, `no_autonomous`, and `no_llm` markers remain present.

If structured reporter payload fields evolve, E2E should assert stable fields
instead of parsing human-readable summary text.

## Explicit Replay Compatibility Plan

The explicit `/replay <learned_path_id> <url>` command remains a separate entry
path from confirmed-plan execution.

11.1.8 should verify:

- explicit `/replay` still works in states where the existing state machine
  allows it;
- `/replay` while `awaiting_confirmation` remains blocked by 11.1.5;
- `/replay` while `plan_confirmed` does not bypass the confirmed-plan execution
  flow;
- task-to-path execution intent does not fake a slash replay command.

## Codex Autonomous Review Plan

Codex autonomous review should be scoped to code and documentation review, not
product-internal autonomous exploration.

Review focus:

- replay completed incorrectly treated as task succeeded;
- confirmation bypass;
- `/replay` bypass under `awaiting_confirmation` or `plan_confirmed`;
- missing target URL guessed from user text;
- result reporter inventing success;
- failed / uncertain triggering recovery;
- event order inconsistent with state transitions;
- final assistant message contradicting event payloads;
- implemented / future status drift in docs.

Expected review output:

- findings;
- severity;
- file / line;
- reproduction or reasoning;
- whether tests cover the behavior;
- recommended fix.

Codex review is auxiliary evidence. It is not a replacement for deterministic
tests.

## Manual / Visual Exploratory Evidence Plan

Manual UI smoke and visual exploratory evidence may be useful after
deterministic tests pass, but they must be reported separately.

Manual / visual reports should include:

- environment;
- exact UI route;
- steps taken;
- observed response;
- screenshots only if needed;
- whether the result is deterministic, exploratory, or blocked by environment.

Do not present manual UI smoke as deterministic API or E2E proof.

## Evidence Report Structure

Each evidence report should include:

- test command;
- pass / fail / blocked result;
- changed files if any;
- relevant event sequence;
- representative API response;
- assistant message summary;
- environment caveats;
- failures and follow-up issues;
- whether results were deterministic, exploratory, manual, or review-only.

Avoid:

- writing only `PASS`;
- treating exploratory review as deterministic proof;
- treating Codex self-review as final acceptance;
- mixing skipped, flaky, blocked, and passed results.

## Environment Caveats

The report should explicitly record:

- sandbox restrictions;
- browser permission issues;
- missing local services;
- database migration state;
- Playwright / browser availability;
- whether an external rerun was needed.

Environment-blocked runs must be distinct from product failures.

## Exit Criteria

11.1.8 can be considered complete when:

- focused API tests pass;
- full API pytest passes or failures are documented with owner and scope;
- scoped E2E passes or is documented as environment-blocked with external rerun
  evidence;
- `ruff` is clean for touched Python files if any were touched during later
  execution;
- `git diff --check` is clean;
- Codex autonomous review has no unresolved P1 / P2;
- docs reflect final implemented statuses;
- no 11.1.9 detail directory is created;
- future scopes remain future.

## Out-of-Scope Items

- No implementation code in this documentation package.
- No new test code in this documentation package.
- No test execution in this documentation package.
- No API endpoint or CLI command.
- No replay execution as part of doc initialization.
- No autonomous run.
- No hidden relearning.
- No raw HTML reading.
- No LLM provider dependency.
- No slot binding.
- No recovery.
- No teaching mode.
- No M12 scope.
- No 11.1.9 detail directory.

## Open Questions

- Which final focused API command list should become the canonical 11.1.8
  acceptance command set?
- Should the scoped E2E evidence remain in the existing conversation
  task-execution spec, or should 11.1.8 split a dedicated evidence spec?
- Which evidence report filename should be used for the final M11.1 closure?
- Should manual UI smoke be required for M11.1 closure, or remain optional
  supplementary evidence?
