# Review

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
next_action: Do not extend this package. Future live validation requires explicit approval and a separate evidence record.
parent_authorizes_runtime_implementation: N/A
active_child_package: N/A
implementation_authorized: yes
do_not_start_next_package: false
blocking_findings: none
last_verified_at: 2026-06-06
commands_run: source inspection; subagent placement review; subagent browser lifecycle review; design review; scoped implementation; py_compile; scoped pytest; scoped ruff; hardcoding scan; `git diff --check`
commands_not_run: live autonomous validation, `verify-scenario`, `wagent chat`, Console UI smoke

## Design Review

- Reviewer: parent agent with Feynman / Pauli read-only subagent inputs
- Decision: PASS
- Notes:
  - This package is a code-gated design package.
  - It must not reopen 11.3.12 parent state.
  - No unresolved P0 / P1 design blocker was found.
  - This `/goal` run treated design review as the first gate, then recorded implementation authorization and
    closeout evidence in this review.

## Implementation Review

- Reviewer: Faraday (read-only subagent), parent follow-up, user review follow-up
- Decision: PASS after fixes; no remaining P0 / P1.
- Notes:
  - Runtime implementation is limited to `LearningRunService._run_capability_discovery()` and
    `BrowserEventRecorder` / terminal-state evidence hardening.
  - No live run, direct autonomous-run endpoint call, or `verify-scenario` was executed.
  - Initial code review found one P1 reset-baseline gap and two P2 evidence / feedback gaps.
  - Fixed by adding reset baseline analysis compatibility checks, fail result status on reset failure after partial
    assets, and explicit runtime close assertions for seed / scenario / persistence exception paths.
  - Re-review found two P2 closeout issues: reset failure skipped/unverified double counting and stale pending review
    wording. Both were fixed before final closeout.
  - User review then found two P1 evidence-integrity issues and four P2 hardening gaps. Fixed by:
    target-agnostic runtime page-state reset fingerprints, request/response action-scope pairing for network terminal
    evidence, minimal reset-failure ExplorationRun persistence, exception closeout browser-session summaries,
    idempotent recorder attach/detach semantics, and stronger non-live spy tests.
  - Follow-up user review found one remaining P1: result-region reset evidence still compared counts, so same-row-count
    content pollution could pass. Fixed by adding target-agnostic result-region content / structure fingerprinting and a
    same-row-count reset rejection regression.

## Subagent Findings Integrated

Placement review:

- Recommended new sibling package `11.3.13-learning-batch-browser-session-reuse`.
- Do not append `11.3.12.5`, because 11.3.12 is already `PACKAGE_COMPLETE`.
- Keep this in M11.3 post-closeout, not M12 or M14.

Browser lifecycle review:

- `ExecutionRuntime` starts/stops browser in its context manager.
- `run_autonomous_exploration()` accepts caller-owned runtime.
- Repeated browser popup comes from `LearningRunService._run_capability_discovery()` opening a runtime for seed analysis and then one runtime per scenario.
- Recommended design: one batch-scoped runtime with scenario reset gates and finally cleanup.

## User Feedback

- The user observed repeated browser popup/close cycles during automatic exploration. Accepted.
- The user asked whether the whole learning process can use one browser and close after learning. Accepted as target design.
- The user asked to decide where the iteration belongs. Accepted; this package chooses `11.3.13`.

## Final Delta

### Actual Delivery

- Created 11.3.13 seven-document package.
- Defined `LearningBatchBrowserSession`, scenario reset, evidence isolation, cleanup, and compatibility contracts.
- Defined implementation and test plan.
- Updated M11 index and roadmap.
- Implemented one batch-scoped runtime for product-level capability discovery:
  seed analysis and all planned scenarios share one caller-managed runtime.
- Added target-agnostic `navigate_only` scenario reset before each scenario.
- Added fail-closed reset baseline snapshots that compare URL / title / control counts plus target-agnostic control
  state fingerprint, result-region count summary, result-region content / structure fingerprint, and lightweight
  page-state fingerprint.
- Added reset fail-closed behavior: reset failure marks the scenario unverified, stops the batch, and avoids
  LearnedPath / LearnedCapability ingestion.
- Added minimal reset-failure `ExplorationRun` persistence so failed reset scenarios are visible in batch history
  without ingesting LearnedPath / LearnedCapability records.
- Added `browser_session_reuse`, `scenario_reset_count`, and reset warning metadata to learning batch summaries.
- Added BrowserEventRecorder listener detach on `stop()` and idempotent `attach()` handling so reused pages do not
  accumulate old recorder listeners.
- Added request / response `request_key` metadata and terminal-state request/response pairing so a response that lands
  in the current action window is not enough unless its request also started in the same action scope.
- Added browser-session setup-failure summary semantics so a runtime setup error records
  `browser_session_reuse: false` and `browser_session_setup_failed: true`.
- Deduplicated reset warnings in batch summaries so the same reset failure is not reported twice via
  `warnings` and `scenario_reset_warnings`.
- Added scoped regression tests for runtime reuse, reset failure, dirty control-state reset rejection, same-row-count
  result-region content / structure pollution reset rejection, reset-failure run persistence, exception closeout
  summaries, browser-session setup failure, terminal-state network pairing, and recorder detach.

### Deviations

- The original generated package was docs-only / implementation-not-authorized. This `/goal` run completed the design
  review gate, authorized scoped implementation, and closed the repo-local implementation in the same package.

### Live Run Boundary

No live run was authorized or executed.

### Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| Source inspection | Identify current browser lifecycle | Completed | 0 | pass | local file reads | No runtime execution |
| Subagent placement review | Decide iteration placement | Completed | 0 | pass | subagent summary | Read-only |
| Subagent browser lifecycle review | Identify current start/stop cause and design risks | Completed | 0 | pass | subagent summary | Read-only |
| `PYTHONPYCACHEPREFIX=/tmp/waf_pycache python3 -m py_compile apps/api/app/services/learning/learning_run_service.py apps/api/app/services/execution/browser_event_recorder.py apps/api/app/services/learning/terminal_state.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_browser_event_recorder.py apps/api/tests/test_terminal_state.py` | Changed Python files compile | No output | 0 | pass | command output | Non-live |
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_learning_run_service.py apps/api/tests/test_browser_event_recorder.py apps/api/tests/test_terminal_state.py -q` | User-review focused reset / recorder / terminal tests pass | 49 passed | 0 | pass | command output | Non-live; includes same-row-count result-region pollution and browser-session setup-failure regressions |
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_learning_run_service.py apps/api/tests/test_browser_event_recorder.py apps/api/tests/test_terminal_state.py apps/api/tests/test_attempt_evaluation.py apps/api/tests/test_bounded_learning_batch_lifecycle.py apps/api/tests/test_page_analyzer_selector.py apps/api/tests/test_filter_capability_discovery.py apps/api/tests/test_capability_hints.py apps/api/tests/test_capability_composer.py apps/api/tests/test_learning_batches_repo.py -q` | 11.3.12 / 11.3.13 scoped regression passes | 138 passed | 0 | pass | command output | Non-live |
| `uv run ruff check apps/api/app/services/learning/learning_run_service.py apps/api/app/services/execution/browser_event_recorder.py apps/api/app/services/learning/terminal_state.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_browser_event_recorder.py apps/api/tests/test_terminal_state.py` | Changed Python files pass lint | All checks passed | 0 | pass | command output | Scoped ruff |
| Hardcoding scan | No new runtime target hardcoding | Only existing generic `data-testid` evidence collection hit in `autonomous_explorer.py`; no `/users` / validation-site target constants in changed runtime files | 0 | pass | `rg -n ...` | Reviewed |
| `git diff --check` | No whitespace errors | No output | 0 | pass | command output | Final diff check |
| `wagent chat` | Not authorized | Not run | N/A | skip | N/A | No live validation |
| `verify-scenario` | Not authorized | Not run | N/A | skip | N/A | No live validation |

### Not Run / Unverified

| Item | Reason | Risk / Follow-up |
|---|---|---|
| Live visible browser validation | Not authorized in this goal | Needed only if user explicitly approves live run |
| `verify-scenario` | Not the validation surface for this non-live package | Do not run unless a future task explicitly requests it |

## Compatibility Review

- Spec-backed autonomous run and LearnedPath replay runtime ownership were not changed.
- Product-level non-capability single learning still uses `_run_pipeline()` and its original one-run runtime context.
- Capability discovery now reuses exactly one runtime for seed analysis plus scenario loop, scoped to one batch only.
- Default reset mode preserves target-site storage; no cookies or localStorage are cleared.

## Scope Review

- In scope: `LearningRunService._run_capability_discovery()`, small private reset helpers, BrowserEventRecorder cleanup,
  focused tests, and closeout docs.
- Out of scope and not implemented: cross-batch browser reuse, L2 teaching, M12 recovery / abort, replay runtime rewrite,
  Console UI batch detail, public API changes, live validation, and direct autonomous-run endpoint evidence.

### Follow-ups

- Optional future live validation may be run only with explicit user approval and a separate evidence record.
