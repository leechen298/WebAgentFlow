# 已完成功能测试补全批次 — 结果

日期：2026-05-11
分支：v0.1-local

## 范围

Q3 执行：按 `docs/testing/current-testing-backlog.md` 第一批实现测试。
只补已完成功能的测试，不改产品功能代码。

## 完成项

### 1. FIX-01: 修复 AutonomousUseCasesPage 过期 abort 测试

- **动作**：移除 2 个引用已删除 `abortRunning` 方法的测试。
- **修改文件**：`apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts`
- **原因**：组件已改为 batch run fire-and-forget；`abortRunning` 不再存在。
- **说明**：这不是新增 abort 覆盖，而是删除针对旧私有组件实例方法的过期断言；没有为了旧测试改产品组件。
- **结果**：**PASS** — 10/10 tests pass（此前为 10/12，2 个失败）

### 2. CV-API-SMOKE: Conversation API smoke (keep-running)

- **动作**：fresh verification run。
- **命令**：`cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_exploration_learned_paths_api.py -q`
- **结果**：**PASS** — 62/62 tests pass。

### 3. CV-CLI-SMOKE: Conversation CLI smoke (keep-running)

- **动作**：验证 baseline。
- **命令**：`cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -q`
- **结果**：**PASS** — 15/15 tests pass

### 4. CV-O-SMOKE: Conversation Orchestrator smoke (keep-running)

- **动作**：复跑 API + LearnedPath review + Orchestrator baseline。
- **命令**：`cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_exploration_learned_paths_api.py tests/test_conversation_orchestrator.py -q`
- **结果**：**PASS** — 79/79 tests pass。

### 5. REPLAY-E2E: Replay deterministic E2E (keep-running)

- **动作**：本轮尝试 fresh rerun。
- **历史证据**：Q1 baseline 显示 9/9 E2E tests pass。
- **本轮复跑**：`pnpm run test:e2e`
- **本轮结果**：**BLOCKED / exit 1** — API request tests failed with
  `connect EPERM 127.0.0.1:8001`; catalog UI failed to launch Chromium with
  `bootstrap_check_in ... Permission denied`.
- **结果策略**：不能把这次算作 fresh PASS；Q1 baseline 仍是最近一次已记录成功运行。

### 6. LP-TRUST-REVIEW: LearnedPath trust / run-review separation smoke

- **动作**：审阅已有测试缺口。
- **发现**：`test_patch_run_review_does_not_modify_learned_path`（`test_exploration_learned_paths_api.py` 第 253 行）已经覆盖 separation invariant：reject run review 后 learned path trust 仍为 `provisional`。
- **结果**：**EXISTING** — 不需要新增测试；该 invariant 已覆盖。

### 7. VS-SELECTOR: Validation-site selector stability smoke

- **动作**：新增测试。
- **新增文件**：`apps/console/src/__tests__/validation-site/selector-stability.test.ts`
- **覆盖**：3 个页面共 14 个测试：
  - LoginPage: #username, #password, role=alert, data-testid=login-error, submit button
  - UserDirectoryPage: #search-name, #search-email, #search-role, #search-status, #btn-search, #btn-reset, #user-search-form, data-user-id, data-testid=user-detail
  - DashboardPage: data-testid=dashboard-welcome
- **结果**：**PASS** — 14/14 tests pass

### 8. CONSOLE-SMOKE: AutonomousWorkbenchPage basic smoke

- **动作**：新增测试。
- **新增文件**：`apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts`
- **覆盖**：6 个测试：
  - renders config card on mount
  - loads specs on mount
  - renders form inputs for URL and goal
  - shows spec matched alert when URL matches
  - shows no-match warning when URL doesn't match
  - shows error handling when listSpecs fails
- **结果**：**PASS** — 6/6 tests pass

## 全量套件验证

After all changes, ran the complete console test suite:

```
Test Files: 21 passed (21)
Tests:      160 passed (160)
Duration:   3.35s
```

Improvement from Q1 baseline: 140 passed + 2 failed → 160 passed + 0 failed.

## 新增 / 修改测试文件

| 文件 | 动作 |
|---|---|
| `apps/console/src/__tests__/components/AutonomousUseCasesPage.test.ts` | Modified (removed 2 broken abort tests) |
| `apps/console/src/__tests__/validation-site/selector-stability.test.ts` | **New** (14 selector stability tests) |
| `apps/console/src/__tests__/components/AutonomousWorkbenchPage.test.ts` | **New** (6 workbench smoke tests) |

## 摘要

| 项目 | 状态 | 测试 |
|---|---|---|
| FIX-01: Fix abort tests | DONE | 10/10 pass |
| CV-API-SMOKE | DONE | 62/62 pass |
| CV-CLI-SMOKE | DONE | 15/15 pass |
| CV-O-SMOKE | DONE | 79/79 targeted API/orchestrator pass |
| REPLAY-E2E | BLOCKED on current rerun; Q1 baseline pass | Current run exit 1; Q1 baseline 9/9 pass |
| LP-TRUST-REVIEW | EXISTING | invariant already tested |
| VS-SELECTOR | DONE | 14/14 pass |
| CONSOLE-SMOKE | DONE | 6/6 pass |

## Autonomous 边界

| 检查 | 结果 |
|---|---|
| Modified product code? | **NO** |
| Called autonomous endpoint? | **NO** |
| Called /exploration/autonomous-runs? | **NO** |
| Called /exploration/autonomous-runs/stream? | **NO** |
| Depended on LLM provider? | **NO** |
| git diff --check | **exit 0** (clean) |

## 未完成项

- REPLAY-E2E current rerun: blocked by local sandbox / permission / localhost access errors
  (`connect EPERM 127.0.0.1:8001`, Chromium `bootstrap_check_in ... Permission denied`).
  Q1 baseline confirms a prior 9/9 pass, but this report does not claim a fresh E2E PASS.
