# Existing Feature Test Batch — Results

Date: 2026-05-11
Branch: v0.1-local

## Scope

Q3 执行：按 `docs/testing/current-testing-backlog.md` 第一批实现测试。
只补已完成功能的测试，不改产品功能代码。

## Items Completed

### 1. FIX-01: Fix broken AutonomousUseCasesPage abort tests

- **Action**: Removed 2 tests that referenced deleted `abortRunning` method.
- **File modified**: `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts`
- **Reason**: Component changed to fire-and-forget for batch runs. `abortRunning` no longer exists.
- **Clarification**: This is not new abort coverage. It removes stale assertions against a deleted private component instance method. The product component was not changed to satisfy old tests.
- **Result**: **PASS** — 10/10 tests pass (was 10/12 with 2 failures)

### 2. CV-API-SMOKE: Conversation API smoke (keep-running)

- **Action**: Fresh verification run.
- **Command**: `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_exploration_learned_paths_api.py -q`
- **Result**: **PASS** — 62/62 tests pass.

### 3. CV-CLI-SMOKE: Conversation CLI smoke (keep-running)

- **Action**: Verified baseline.
- **Command**: `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -q`
- **Result**: **PASS** — 15/15 tests pass

### 4. CV-O-SMOKE: Conversation Orchestrator smoke (keep-running)

- **Action**: Fresh verification run with API + LearnedPath review + Orchestrator baseline.
- **Command**: `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_exploration_learned_paths_api.py tests/test_conversation_orchestrator.py -q`
- **Result**: **PASS** — 79/79 tests pass.

### 5. REPLAY-E2E: Replay deterministic E2E (keep-running)

- **Action**: Fresh rerun attempted in this session.
- **Previous evidence**: Q1 baseline shows 9/9 E2E tests pass.
- **Current rerun**: `pnpm run test:e2e`
- **Current result**: **BLOCKED / exit 1** — API request tests failed with
  `connect EPERM 127.0.0.1:8001`; catalog UI failed to launch Chromium with
  `bootstrap_check_in ... Permission denied`.
- **Result policy**: Do not count this as a fresh PASS. Q1 baseline remains the last recorded successful run.

### 6. LP-TRUST-REVIEW: LearnedPath trust / run-review separation smoke

- **Action**: Gap review of existing tests.
- **Finding**: `test_patch_run_review_does_not_modify_learned_path` (line 253 in `test_exploration_learned_paths_api.py`) already tests the separation invariant: after rejecting a run review, the learned path's trust remains "provisional".
- **Result**: **EXISTING** — no new test needed. Invariant already covered.

### 7. VS-SELECTOR: Validation-site selector stability smoke

- **Action**: New test created.
- **File created**: `apps/console/src/__tests__/validation-site/selector-stability.test.ts`
- **Coverage**: 14 tests across 3 pages:
  - LoginPage: #username, #password, role=alert, data-testid=login-error, submit button
  - UserDirectoryPage: #search-name, #search-email, #search-role, #search-status, #btn-search, #btn-reset, #user-search-form, data-user-id, data-testid=user-detail
  - DashboardPage: data-testid=dashboard-welcome
- **Result**: **PASS** — 14/14 tests pass

### 8. CONSOLE-SMOKE: AutonomousWorkbenchPage basic smoke

- **Action**: New test created.
- **File created**: `apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts`
- **Coverage**: 6 tests:
  - renders config card on mount
  - loads specs on mount
  - renders form inputs for URL and goal
  - shows spec matched alert when URL matches
  - shows no-match warning when URL doesn't match
  - shows error handling when listSpecs fails
- **Result**: **PASS** — 6/6 tests pass

## Full Suite Verification

After all changes, ran the complete console test suite:

```
Test Files: 21 passed (21)
Tests:      160 passed (160)
Duration:   3.35s
```

Improvement from Q1 baseline: 140 passed + 2 failed → 160 passed + 0 failed.

## New/Modified Test Files

| File | Action |
|---|---|
| `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts` | Modified (removed 2 broken abort tests) |
| `apps/console/src/__tests__/validation-site/selector-stability.test.ts` | **New** (14 selector stability tests) |
| `apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts` | **New** (6 workbench smoke tests) |

## Summary

| Item | Status | Tests |
|---|---|---|
| FIX-01: Fix abort tests | DONE | 10/10 pass |
| CV-API-SMOKE | DONE | 62/62 pass |
| CV-CLI-SMOKE | DONE | 15/15 pass |
| CV-O-SMOKE | DONE | 79/79 targeted API/orchestrator pass |
| REPLAY-E2E | BLOCKED on current rerun; Q1 baseline pass | Current run exit 1; Q1 baseline 9/9 pass |
| LP-TRUST-REVIEW | EXISTING | invariant already tested |
| VS-SELECTOR | DONE | 14/14 pass |
| CONSOLE-SMOKE | DONE | 6/6 pass |

## Autonomy Boundary

| Check | Result |
|---|---|
| Modified product code? | **NO** |
| Called autonomous endpoint? | **NO** |
| Called /exploration/autonomous-runs? | **NO** |
| Called /exploration/autonomous-runs/stream? | **NO** |
| Depended on LLM provider? | **NO** |
| git diff --check | **exit 0** (clean) |

## Uncompleted Items

- REPLAY-E2E current rerun: blocked by local sandbox / permission / localhost access errors
  (`connect EPERM 127.0.0.1:8001`, Chromium `bootstrap_check_in ... Permission denied`).
  Q1 baseline confirms a prior 9/9 pass, but this report does not claim a fresh E2E PASS.
