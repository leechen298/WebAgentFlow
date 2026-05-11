# Current Testing Backlog

## Scope

本文件整理当前已完成功能的测试缺口和第一批补全计划。

- 只覆盖当前已完成功能（M10 + M11.0.1–11.0.4）。
- 不覆盖未来 M11.0.5 Orchestrator Dispatcher、M11.1 Task-to-Path、M12、M13。
- 不执行测试，只整理 backlog。
- 不改产品代码，不改测试代码，不改 package scripts。

## Existing Baselines

基于 Q1 baseline audit（`docs/testing/results/2026-05-11-existing-test-baseline.md`）：

| Suite | Result |
|---|---|
| API pytest | 811 passed, 65 skipped (fixtures), 0 failed |
| CLI pytest | 67 passed, 0 failed |
| Console Vitest | 140 passed, **2 failed** |
| Worker pytest | 5 passed, 0 failed |
| E2E Playwright | 9 passed, 0 failed |
| **Total** | **1032 passed, 2 failed, 65 skipped** |

Q1 关键发现：

- F-01: 2 console tests failing（`abortRunning` 方法已不存在）
- F-02: 65 API tests skipped（HTML fixtures 不在 checkout 中）
- F-03: E2E 全部通过（9/9 replay）
- F-04: AutonomousWorkbenchPage.vue 无组件测试（1001 行）
- F-05: Conversation 无 E2E smoke

## Backlog Categories

### existing — 当前已有测试，需修

| ID | Item | Files | Issue |
|---|---|---|---|
| FIX-01 | AutonomousUseCasesPage abort tests | `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts` | 2 tests reference `vm.abortRunning` which no longer exists on component. Test/component sync gap. |

### keep-running — 已有基线，持续运行

| ID | Item | Files | Coverage |
|---|---|---|---|
| KR-01 | Conversation domain tests | `test_conversation_commands.py`, `test_conversation_state.py` | parser + state machine |
| KR-02 | Conversation repo tests | `test_conversation_repo.py` | session/message/event store |
| KR-03 | Conversation API tests | `test_conversation_api.py` | HTTP API contract |
| KR-04 | Conversation CLI tests | `test_conversation.py` | wagent conversation (15 tests) |
| KR-05 | LearnedPath trust tests | `test_learned_paths_repo.py` | trust transitions, set_trust, legal/illegal |
| KR-06 | Run review API tests | `test_exploration_learned_paths_api.py` | accept/reject/clear review, 39 tests |
| KR-07 | Replay E2E | `apps/e2e/tests/replay/` | 9 cases: happy path, drift, catalog UI |
| KR-08 | Worker tests | `apps/worker/tests/` | config, logging, main, runner |
| KR-09 | Page verification tests | `test_page_verification.py`, `test_pass_gate.py` | scorecard, gate logic |
| KR-10 | Supervisor observation tests | `test_supervisor_observations.py`, `test_supervisor_prompt.py` | observation atoms, verdict derivation |

### gap — 确认缺口，需补

| ID | Item | Why gap |
|---|---|---|
| GAP-01 | AutonomousWorkbenchPage component test | 1001-line component, zero tests |
| GAP-02 | 2 broken AutonomousUseCasesPage tests | FIX-01 的根因：组件重构后测试未同步 |
| GAP-03 | Validation-site selector stability smoke | fixture 漂移会破坏 replay E2E，无预警测试 |

### proposed — 合理建议，等对应能力进入施工

| ID | Item | Dependency |
|---|---|---|
| PROP-01 | Conversation E2E smoke | 11.0.5 Orchestrator Dispatcher 完成后 |
| PROP-02 | Console history/detail page component smoke | 需先定具体页面范围 |
| PROP-03 | LearnedPath catalog trust tag visual exploratory | 需 headed browser 证据 |

### deferred — 有价值但不是当前批次

| ID | Item | Reason |
|---|---|---|
| DEF-01 | AE 全量 60 case 展开 | 范围过大，偏离当前测试专项 |
| DEF-02 | live autonomous learning → replay smoke | live smoke，不进常规 CI |
| DEF-03 | validation-site 全页面 E2E | 过度 E2E 化 |
| DEF-04 | console 全页面 visual exploratory | 范围过大 |
| DEF-05 | replay DOM obstruction failure | 等 fixture 设计稳定后补 |
| DEF-06 | replay audit persistence | 等实现 replay audit 时补 |

### reject — 不应落地

| Item | Reason |
|---|---|
| 把 LLM / verify-scenario / live autonomous run 标成 deterministic E2E | 依赖 LLM，不是 deterministic |
| 把 LLM-dependent case 标成常规 CI yes | 不符合 evidence type 规则 |
| 把 headless E2E 当成 visual UI exploratory | 证据类型不匹配 |
| conversation 写成 pure-function only | 11.0.1–11.0.4 已完成 |

---

## First Existing-Feature Batch

只列当前可做的测试补全。不推进 M11.0.5，不实现 Orchestrator Dispatcher 测试。

### 1. FIX-01: Fix broken AutonomousUseCasesPage abort tests

- **Case ID**: FIX-01
- **Reason**: 2 tests failing — `vm.abortRunning is not a function`. Tests reference method that no longer exists on component. Must fix before other console work.
- **Layer**: Component
- **Priority**: P0
- **CI**: yes
- **Evidence required**: Vitest output showing 0 failures
- **Implementation target**: `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts`
- **Why now**: Broken tests block confidence in all console test runs. Must fix first.
- **What not to do**: Don't change the component to re-expose `abortRunning` unless product intent requires it. Update tests to match current component API.
- **Status**: **DONE** (2026-05-11) — removed 2 abort tests that referenced deleted `abortRunning` method. Component is fire-and-forget for batch runs. 10/10 tests pass.

### 2. CV-API-SMOKE: Conversation API smoke (keep-running)

- **Case ID**: FIRST-P0-02 (from full-test-matrix.md)
- **Reason**: API is the contract for CLI and future orchestrator. Existing `test_conversation_api.py` covers session create/read, messages, events, transcript. Current task: verify baseline, keep running, only add cases if gap found.
- **Layer**: Repo/API integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/api/tests/test_conversation_api.py`
- **Implementation target**: `apps/api/tests/test_conversation_api.py` (existing)
- **Why now**: Baseline already passing. Confirm no regression.
- **What not to do**: Don't add orchestrator/dispatcher test cases. Don't test endpoints that don't exist yet.

### 3. CV-CLI-SMOKE: Conversation CLI smoke (keep-running)

- **Case ID**: FIRST-P0-03 (from full-test-matrix.md)
- **Reason**: CLI tests for `wagent conversation` (start, status, send, messages, transcript, events). 15 tests all passing. Current task: keep running.
- **Layer**: CLI integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/cli/tests/test_conversation.py`
- **Implementation target**: `apps/cli/tests/test_conversation.py` (existing)
- **Why now**: Baseline already passing. Confirm no regression.
- **What not to do**: Don't add interactive REPL tests. Don't add `/replay` command tests.

### 4. REPLAY-E2E: Replay deterministic E2E (keep-running)

- **Case ID**: FIRST-P0-04 (from full-test-matrix.md)
- **Reason**: M10.2 replay is the established deterministic E2E regression track. 9 tests all passing. Current task: keep running as regression gate.
- **Layer**: Deterministic E2E
- **Priority**: P0
- **CI**: yes (once services orchestrated)
- **Evidence required**: `pnpm run test:e2e` output
- **Implementation target**: `apps/e2e/tests/replay/` (existing)
- **Why now**: Baseline already passing. Core regression track.
- **What not to do**: Don't add conversation E2E here. Don't add live autonomous run cases.

### 5. LP-TRUST-REVIEW: LearnedPath trust / run-review separation smoke

- **Case ID**: FIRST-P1-01 (from full-test-matrix.md)
- **Reason**: Run review (accept/reject on exploration_run) and path trust (trust state machine on learned_path) are independent design invariants from M10.1.3. Tests already exist in `test_exploration_learned_paths_api.py` (run review) and `test_learned_paths_repo.py` (trust transitions). Current task: evaluate whether the separation invariant is explicitly tested.
- **Layer**: API / Repo integration
- **Priority**: P1
- **CI**: yes
- **Evidence required**: gap review of existing tests + pytest output
- **Implementation target**: `apps/api/tests/test_exploration_learned_paths_api.py` (evaluate gap, possibly add invariant test)
- **Why now**: Protects design invariant. Existing tests cover trust and review independently; verify no cross-contamination.
- **What not to do**: Don't add live autonomous run tests. Don't test orchestrator integration.
- **Status**: **DONE** (2026-05-11) — gap review complete. `test_patch_run_review_does_not_modify_learned_path` (line 253 in test_exploration_learned_paths_api.py) already tests the separation invariant: rejecting a run review does NOT change path trust. No new test needed.

### 6. VS-SELECTOR: Validation-site selector stability smoke

- **Case ID**: NEW (from full-test-matrix.md domain 5 gap)
- **Reason**: Replay E2E depends on stable CSS selectors in validation-site pages (`#username`, `#password`, `#search-name`, `#btn-search`, etc.). If selectors drift, replay E2E will fail silently or with confusing errors. A lightweight smoke can catch drift early.
- **Layer**: Unit / API integration
- **Priority**: P1
- **CI**: yes
- **Evidence required**: test output confirming selectors exist in fixture HTML
- **Implementation target**: new file `apps/api/tests/test_validation_site_selectors.py` or `apps/e2e/tests/validation-site/selectors.spec.ts`
- **Why now**: Protects replay E2E from fixture drift. Low cost, high signal.
- **What not to do**: Don't build full validation-site E2E. Don't test login/sessionStorage behavior. Don't add visual UI exploratory here.
- **Status**: **DONE** (2026-05-11) — new test at `apps/console/src/__tests__/validation-site/selector-stability.test.ts`. 14 tests covering LoginPage, UserDirectoryPage, DashboardPage selectors. Reads Vue source files directly, no running server needed. 14/14 pass.

### 7. CONSOLE-SMOKE: Console operator UI basic smoke

- **Case ID**: FIRST-P1-02 (from full-test-matrix.md)
- **Reason**: Console has 19 test files covering APIs, stores, utils, and some components. But main operator pages (history, catalog, workbench) have limited component test coverage. AutonomousWorkbenchPage (1001 lines) has zero tests.
- **Layer**: Component
- **Priority**: P1
- **CI**: yes (component), no (visual)
- **Evidence required**: Vitest output
- **Implementation target**: `apps/console/src/__tests__/components/` (new tests for uncovered pages)
- **Why now**: 1001-line untested component is the largest coverage gap in the console suite.
- **What not to do**: Don't add visual UI exploratory (needs headed browser). Don't add E2E for console pages. Don't test pages that don't exist yet.
- **Status**: **DONE** (2026-05-11) — new test at `apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts`. 6 tests: renders config card, loads specs, renders form, spec matched alert, no-match warning, error handling. 6/6 pass.

---

## Watchlist

暂不做但未来需要关注的测试方向：

| ID | Item | Trigger |
|---|---|---|
| W-01 | M11.0.5 Orchestrator Dispatcher unit matrix | 11.0.5 implementation starts |
| W-02 | Conversation E2E smoke | 11.0.5 dispatcher + API contract stable |
| W-03 | verify-scenario manual live smoke | release smoke only |
| W-04 | Guided teaching tests | L2 teaching enters implementation |
| W-05 | Task-to-path planning tests | M11.1 enters implementation |
| W-06 | AutonomousWorkbenchPage visual UI exploratory | headed browser evidence available |
| W-07 | Replay DOM obstruction failure E2E | fixture design stable |
| W-08 | Replay audit persistence | replay audit feature implemented |

---

## Batch Summary

| Item | Work type | Priority | Layer | CI |
|---|---|---|---|---|
| FIX-01: Fix abort tests | fix existing | P0 | Component | yes |
| CV-API-SMOKE | keep-running | P0 | API integration | yes |
| CV-CLI-SMOKE | keep-running | P0 | CLI integration | yes |
| REPLAY-E2E | keep-running | P0 | Det E2E | yes |
| LP-TRUST-REVIEW | evaluate gap | P1 | API/Repo | yes |
| VS-SELECTOR | new | P1 | Unit/API | yes |
| CONSOLE-SMOKE | new | P1 | Component | yes |

Total: 7 items (1 fix, 3 keep-running, 1 evaluate, 2 new)

## Deferred Count

- 6 deferred items (DEF-01 through DEF-06)
- 8 watchlist items (W-01 through W-08)
- 4 reject items
