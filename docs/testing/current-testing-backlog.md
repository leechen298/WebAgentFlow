# 当前测试 Backlog

## 范围

本文件整理当前已完成功能的测试缺口和第一批补全计划。

- 只覆盖当前已完成功能（M10 + M11.0.1–11.0.7）。
- 不覆盖未来 M11.1 Task-to-Path、M12、M13。
- 不执行测试，只整理 backlog。
- 不改产品代码，不改测试代码，不改 package scripts。
- 本文件会混合 unit / API / CLI / component / E2E。
- 如果任务目标专指 deterministic E2E，请使用 `e2e/README.md`。
- 如果任务目标专指 Agent-operated UI exploratory，请使用
  `agent-operated-ui/README.md`。

## 现有基线

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
- F-05: Conversation 无 E2E smoke（已在 11.0.7 补齐）

## Backlog 分类

### existing — 当前已有测试，需处理

| ID | 项目 | 文件 | 问题 |
|---|---|---|---|
| FIX-01 | AutonomousUseCasesPage abort tests | `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts` | 2 tests reference `vm.abortRunning` which no longer exists on component. Test/component sync gap. |

### keep-running — 已有基线，持续运行

| ID | 项目 | 文件 | 覆盖 |
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
| KR-11 | Conversation orchestrator tests | `test_conversation_orchestrator.py` | service-only orchestrator / dispatcher baseline |
| KR-12 | Conversation replay hook tests | `test_conversation_replay_hook.py` | explicit replay hook |
| KR-13 | Conversation runtime E2E | `apps/e2e/tests/conversation/runtime.spec.ts` | session dispatch `/replay` -> transcript/events |
| KR-14 | Conversation CLI-driven E2E | `apps/e2e/tests/conversation/cli-runtime.spec.ts` | real `wagent conversation` subprocess -> API -> replay hook |

### gap — 确认缺口，需补

| ID | 项目 | 缺口原因 |
|---|---|---|
| GAP-01 | AutonomousWorkbenchPage component test | 1001-line component, zero tests |
| GAP-02 | 2 broken AutonomousUseCasesPage tests | FIX-01 的根因：组件重构后测试未同步 |
| GAP-03 | External fixture selector stability smoke | fixture 漂移会破坏 replay E2E，无预警测试 |

### proposed — 合理建议，等对应能力进入施工

| ID | 项目 | 依赖 |
|---|---|---|
| PROP-01 | Additional conversation E2E variants | M11.1 或更多 runtime behavior 进入施工后 |
| PROP-02 | Console history/detail page component smoke | 需先定具体页面范围 |
| PROP-03 | LearnedPath catalog trust tag visual exploratory | 需 headed browser 证据 |

### deferred — 有价值但不是当前批次

| ID | 项目 | 原因 |
|---|---|---|
| DEF-01 | AE 全量 60 case 展开 | 范围过大，偏离当前测试专项 |
| DEF-02 | live autonomous learning → replay smoke | live smoke，不进常规 CI |
| DEF-03 | external fixture provider 全页面 E2E | 过度 E2E 化，应由 fixture provider 自己维护 |
| DEF-04 | console 全页面 visual exploratory | 范围过大 |
| DEF-05 | replay DOM obstruction failure | 等 fixture 设计稳定后补 |
| DEF-06 | replay audit persistence | 等实现 replay audit 时补 |

### reject — 不应落地

| 项目 | 原因 |
|---|---|
| 把 LLM / verify-scenario / live autonomous run 标成 deterministic E2E | 依赖 LLM，不是 deterministic |
| 把 LLM-dependent case 标成常规 CI yes | 不符合 evidence type 规则 |
| 把 headless E2E 当成 Agent-operated UI exploratory | 证据类型不匹配 |
| conversation 写成 pure-function only | 11.0.1–11.0.4 已完成 |

---

## 第一批已完成功能测试补全

只列当前可做的测试补全。不推进 M11.1，不实现 task-to-path 测试。

### 1. FIX-01: 修复 AutonomousUseCasesPage 过期 abort 测试

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

### 2. CV-API-SMOKE: Conversation API smoke（keep-running）

- **Case ID**: FIRST-P0-02 (from full-test-matrix.md)
- **Reason**: API is the contract for CLI, orchestrator baseline, and explicit replay hook. Existing `test_conversation_api.py` covers session create/read, messages, events, transcript, and dispatch. Current task: verify baseline, keep running, only add cases if gap found.
- **Layer**: Repo/API integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/api/tests/test_conversation_api.py`
- **Implementation target**: `apps/api/tests/test_conversation_api.py` (existing)
- **Why now**: Baseline already passing. Confirm no regression.
- **What not to do**: Don't add orchestrator/dispatcher test cases. Don't test endpoints that don't exist yet.

### 3. CV-CLI-SMOKE: Conversation CLI smoke（keep-running）

- **Case ID**: FIRST-P0-03 (from full-test-matrix.md)
- **Reason**: CLI tests for `wagent conversation` (start, status, send, messages, transcript, events). 15 tests all passing. Current task: keep running.
- **Layer**: CLI integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/cli/tests/test_conversation.py`
- **Implementation target**: `apps/cli/tests/test_conversation.py` (existing)
- **Why now**: Baseline already passing. Confirm no regression.
- **What not to do**: Don't add interactive REPL tests. Don't add `/replay` command tests.

### 4. CV-O-SMOKE: Conversation Orchestrator smoke（keep-running）

- **Case ID**: CV-O-SMOKE
- **Reason**: 11.0.5 service-only Orchestrator Dispatcher 已完成，`test_conversation_orchestrator.py` 是当前 baseline。当前任务是持续运行，只有发现 contract 缺口时才新增。
- **Layer**: Unit / integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/api/tests/test_conversation_orchestrator.py`
- **Implementation target**: `apps/api/tests/test_conversation_orchestrator.py` (existing)
- **Why now**: Orchestrator 是 conversation 后续 replay hook / dispatch integration 的前置边界。
- **What not to do**: Don't add path selection or task-to-path tests.

### 5. CV-RH-SMOKE: Conversation replay hook smoke（keep-running）

- **Case ID**: CV-RH-SMOKE
- **Reason**: 11.0.6 Explicit Replay Command Hook 已完成，`test_conversation_replay_hook.py` 是当前 baseline。当前任务是持续运行。
- **Layer**: API / integration
- **Priority**: P0
- **CI**: yes
- **Evidence required**: pytest output from `apps/api/tests/test_conversation_replay_hook.py`
- **Implementation target**: `apps/api/tests/test_conversation_replay_hook.py` (existing)
- **Why now**: replay hook 是 M10 replay 和 M11 runtime loop 的第一条确定性桥。
- **What not to do**: Don't add path selection or task-to-path tests.
- **Status**: **DONE** (2026-05-11) — included in conversation baseline report, 179 passed targeted API baseline.

### 6. CV-E2E: Conversation runtime E2E（keep-running）

- **Case ID**: CV-E2E
- **Reason**: 11.0.6 已提供 dispatch + replay hook；11.0.7 已新增 deterministic E2E，验证 session -> `/replay` -> replay summary -> transcript/events。
- **Layer**: Deterministic E2E
- **Priority**: P0
- **CI**: yes, once local services are orchestrated
- **Evidence required**: Playwright output from `apps/e2e/tests/conversation/runtime.spec.ts`
- **Implementation target**: `apps/e2e/tests/conversation/runtime.spec.ts` (existing)
- **Why now**: 这是 M10 replay 和 M11 runtime loop 的第一个端到端闭环。
- **What not to do**: Don't call autonomous run. Don't depend on LLM. Don't add M11.1 task-to-path expectations.
- **Status**: **DONE** (2026-05-11) — scoped conversation E2E 1/1 passed；full `pnpm run test:e2e` 10/10 passed.

### 7. REPLAY-E2E: Replay deterministic E2E（keep-running）

- **Case ID**: FIRST-P0-04 (from full-test-matrix.md)
- **Reason**: M10.2 replay is the established deterministic E2E regression track. 9 tests all passing. Current task: keep running as regression gate.
- **Layer**: Deterministic E2E
- **Priority**: P0
- **CI**: yes (once services orchestrated)
- **Evidence required**: `pnpm run test:e2e` output
- **Implementation target**: `apps/e2e/tests/replay/` (existing)
- **Why now**: Baseline already passing. Core regression track.
- **What not to do**: Don't add conversation E2E here. Don't add live autonomous run cases.

### 7B. CV-CLI-E2E: Conversation CLI-driven E2E（keep-running）

- **Case ID**: CV-CLI-E2E
- **Reason**: `wagent conversation` 是 M11 runtime conversation CLI 入口。现在已有真实 CLI subprocess E2E，验证 start / send `/replay` / status / transcript / events 打真实 API。
- **Layer**: Deterministic E2E
- **Priority**: P0
- **CI**: yes, once local services and CLI environment are orchestrated
- **Evidence required**: Playwright output from `apps/e2e/tests/conversation/cli-runtime.spec.ts`
- **Implementation target**: `apps/e2e/tests/conversation/cli-runtime.spec.ts` (existing)
- **Why now**: 区分 CLI mocked tests 和真实 runtime CLI E2E，保护用户入口。
- **What not to do**: Don't call autonomous run. Don't depend on LLM. Don't add M11.1 task-to-path expectations.
- **Status**: **DONE** (2026-05-11) — scoped CLI E2E 1/1 passed outside sandbox；full `pnpm run test:e2e` 11/11 passed.

### 8. LP-TRUST-REVIEW: LearnedPath trust / run-review separation smoke

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

### 9. EXT-FIXTURE-SELECTOR: External fixture selector stability smoke

- **Case ID**: NEW (from full-test-matrix.md domain 5 gap)
- **Reason**: Replay E2E depends on stable selectors owned by the external fixture provider. If selectors drift, replay E2E will fail silently or with confusing errors. The selector smoke belongs with the provider, not in this repository.
- **Layer**: Unit / API integration
- **Priority**: P1
- **CI**: yes
- **Evidence required**: provider-side test output plus a redacted manifest/result consumed by WebAgentFlow.
- **Implementation target**: external fixture provider repository.
- **Why now**: Protects replay E2E from fixture drift while keeping WebAgentFlow target-agnostic.
- **What not to do**: Don't keep provider page selectors, page names, or browser-smoke tests in this repository. Don't add Agent-operated UI exploratory here.
- **Status**: **MOVED OUT** (2026-05-30) — WebAgentFlow now consumes external replay fixture manifests instead of maintaining provider-page selector smoke.

### 10. CONSOLE-SMOKE: Console operator UI basic smoke

- **Case ID**: FIRST-P1-02 (from full-test-matrix.md)
- **Reason**: Console has 19 test files covering APIs, stores, utils, and some components. But main operator pages (history, catalog, workbench) have limited component test coverage. AutonomousWorkbenchPage (1001 lines) has zero tests.
- **Layer**: Component
- **Priority**: P1
- **CI**: yes (component), no (visual)
- **Evidence required**: Vitest output
- **实施目标**：`apps/console/src/__tests__/components/`（为未覆盖页面新增测试）
- **为什么现在做**：1001 行未测试组件是 console 套件里最大的覆盖缺口。
- **不做什么**：不新增 Agent-operated UI exploratory（需要 headed browser）；不为 console 页面新增 E2E；不测试尚不存在的页面。
- **状态**：**DONE** (2026-05-11) — 新增 `apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts`。6 个测试：renders config card, loads specs, renders form, spec matched alert, no-match warning, error handling。6/6 pass。

---

## 观察列表

暂不做但未来需要关注的测试方向：

| ID | 项目 | 触发条件 |
|---|---|---|
| W-01 | Additional conversation E2E variants | M11.1 或更多 runtime behavior 进入施工 |
| W-02 | Conversation Agent-operated UI exploratory | 需要观察 console 呈现时 |
| W-03 | verify-scenario manual live smoke | release smoke only |
| W-04 | Guided teaching tests | L2 teaching enters implementation |
| W-05 | Task-to-path planning tests | M11.1 enters implementation |
| W-06 | AutonomousWorkbenchPage Agent-operated UI exploratory | headed browser evidence available |
| W-07 | Replay DOM obstruction failure E2E | fixture design stable |
| W-08 | Replay audit persistence | replay audit feature implemented |

---

## 批次摘要

| 项目 | 工作类型 | 优先级 | 层级 | CI |
|---|---|---|---|---|
| FIX-01: Fix abort tests | fix existing | P0 | Component | yes |
| CV-API-SMOKE | keep-running | P0 | API integration | yes |
| CV-CLI-SMOKE | keep-running | P0 | CLI integration | yes |
| CV-O-SMOKE | keep-running | P0 | Unit/integration | yes |
| CV-RH-SMOKE | keep-running | P0 | API/integration | yes |
| CV-E2E | keep-running | P0 | Det E2E | yes |
| CV-CLI-E2E | keep-running | P0 | Det E2E | yes |
| REPLAY-E2E | keep-running | P0 | Det E2E | yes |
| LP-TRUST-REVIEW | evaluate gap | P1 | API/Repo | yes |
| VS-SELECTOR | new | P1 | Unit/API | yes |
| CONSOLE-SMOKE | new | P1 | Component | yes |

总计：10 项（1 个 fix，6 个 keep-running，1 个 evaluate，2 个 new）

## Deferred / Watchlist 计数

- 6 deferred items (DEF-01 through DEF-06)
- 8 watchlist items (W-01 through W-08)
- 4 reject items
