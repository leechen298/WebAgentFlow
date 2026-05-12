# 现有测试基线审计

## 元数据

- **日期**: 2026-05-11
- **Commit**: `0b621724d926c842353aa61d5f3f2735ab9310de`
- **工作区**: modified（见下方）
- **分支**: v0.1-local

### 工作区状态

```
 M docs/iterations/m11/README.md
 M docs/iterations/m11/m11-plan.md
 M docs/testing/README.md
?? docs/iterations/m11/11.0.5-orchestrator-dispatcher/
?? docs/testing/features/conversation.md
?? docs/testing/full-test-matrix.md
?? docs/testing/results/2026-05-11-q1-baseline-audit.md
```

## 测试文件盘点

**说明**：这是 Test File Inventory Snapshot，只是测试文件盘点；它不代表覆盖率，
也不代表所有测试都通过。文件数量不是测试数量，也不是 coverage。

```bash
find apps/api/tests -name 'test_*.py' | wc -l       # 30
find apps/cli/tests -name 'test_*.py' | wc -l       # 3
find apps/console/src/__tests__ -name '*.test.*' | wc -l  # 19
find apps/e2e/tests -name '*.spec.ts' | wc -l       # 2
find apps/worker/tests -name 'test_*.py' | wc -l    # 4
```

| 套件 | 测试文件数 |
|---|---|
| API (apps/api/tests/) | 30 |
| CLI (apps/cli/tests/) | 3 |
| Console (apps/console/src/__tests__/) | 19 |
| E2E (apps/e2e/tests/) | 2 |
| Worker (apps/worker/tests/) | 4 |
| **Total** | **58** |

## 执行命令

### API tests

```bash
cd apps/api && ../../.venv/bin/pytest -v --tb=short
```

结果：**876 collected, 811 passed, 65 skipped, 0 failed** (24.43s)

65 skipped tests are HTML fixture-dependent tests in `test_ast_simplifier.py`
and `test_html_ast_parser.py`. Skipped because fixture HTML files are not
present in the current checkout. This is expected behavior.

### CLI tests

```bash
cd apps/cli && ../../.venv/bin/pytest -v --tb=short
```

结果：**67 collected, 67 passed, 0 skipped, 0 failed** (0.11s)

### Console tests

```bash
cd apps/console && npx vitest run
```

结果：**19 test files, 142 tests, 140 passed, 2 failed** (2.70s)

#### 失败测试

Both failures are in `AutonomousUseCasesPage.test.ts`:

1. `abort calls running task abort functions and updates status`
   - `TypeError: vm.abortRunning is not a function` (line 325)
2. `queued tasks are set to aborted on abort without calling abort function`
   - `TypeError: vm.abortRunning is not a function` (line 371)

根因：`AutonomousUseCasesPage.vue` 不再暴露 `abortRunning` public method；
这些测试针对的是旧版组件。

### Worker tests

```bash
cd apps/worker && ../../.venv/bin/pytest -v --tb=short
```

结果：**5 collected, 5 passed, 0 skipped, 0 failed** (0.06s)

### E2E tests

```bash
pnpm run test:e2e
```

结果：**9 passed** (13.8s)

| 测试 | 状态 |
|---|---|
| replay happy path | PASS |
| replay observational path | PASS |
| replay page mismatch | PASS |
| replay catalog UI happy path | PASS |
| replay target missing | PASS |
| replay unsupported action | PASS |
| replay flaky warning | PASS |
| replay deprecated 422 | PASS |
| replay signature changed | PASS |

### git diff --check

```bash
git diff --check
```

结果：**exit code 0**（clean，tracked files 无 whitespace errors）

## 按测试区域汇总

| 区域 | 状态 | 详情 |
|---|---|---|
| API unit / integration | PASS | 811 passed, 65 skipped (fixtures absent) |
| CLI tests | PASS | 67 passed |
| Console component tests | FAIL (2) | 140 passed, 2 failed (abortRunning) |
| Console API / store tests | PASS | all passed |
| Worker tests | PASS | 5 passed |
| E2E replay | PASS | 9 passed |
| E2E conversation | NOT_RUN | no conversation E2E spec exists |
| Visual UI exploratory | NOT_RUN | not in scope for this audit |
| Live autonomous smoke | NOT_RUN | not in scope for this audit |

## 各套件明细

### apps/api/tests/ (30 files)

| 文件 | 域 |
|---|---|
| test_action_executor.py | autonomous action execution |
| test_action_planner.py | rule-based multi-field planner |
| test_assess_outcome.py | outcome verdict logic |
| test_ast_simplifier.py | HTML AST simplification |
| test_autonomous_run_display_verdict.py | run display verdict |
| test_autonomous_supervisor.py | supervisor LLM call |
| test_conversation_api.py | Conversation HTTP API |
| test_conversation_commands.py | slash-command parser |
| test_conversation_repo.py | conversation session/message/event store |
| test_conversation_state.py | state transition machine |
| test_execution_runtime.py | Playwright chromium lifecycle |
| test_exploration_learned_paths_api.py | LearnedPath catalog API |
| test_form_label_extractor.py | form label extraction |
| test_health.py | health endpoint |
| test_html_ast_parser.py | HTML → AST parser |
| test_learned_path_replay.py | replay execution + drift |
| test_learned_paths_repo.py | LearnedPath persistence |
| test_llm_provider.py | LLM provider interface |
| test_locale.py | locale handling |
| test_page_analyzer_classify.py | page element classification |
| test_page_analyzer_selector.py | CSS selector generation |
| test_page_signature.py | path_template / query_signature / dom_fingerprint |
| test_page_verification.py | spec-baseline comparator, 5-score scorecard |
| test_pass_gate.py | pass/fail/unverified gate |
| test_semantic_role_inference.py | semantic role matching |
| test_structure_integrity.py | DOM structure integrity |
| test_supervisor_observations.py | observation-atom schema + verdict derivation |
| test_supervisor_prompt.py | supervisor prompt assembly |
| test_toggle_values.py | toggle values logic |
| test_toggle_values_wiring.py | toggle values wiring in payload |

### apps/cli/tests/ (3 files)

| File | Tests | Domain |
|---|---|---|
| test_conversation.py | 15 | `wagent conversation` CLI |
| test_verify.py | 32 | `wagent verify` / verify-scenario CLI |
| test_skill.py | 20 | skill install/uninstall |

### apps/console/src/__tests__/ (19 files)

| File | Status |
|---|---|
| api/autonomousStream.test.ts | PASS |
| api/client.test.ts | PASS |
| api/exploration.test.ts | PASS |
| api/health.test.ts | PASS |
| api/index.test.ts | PASS |
| components/AutonomousRunDetailPage.test.ts | PASS |
| components/AutonomousRunHistoryPage.test.ts | PASS |
| components/AutonomousUseCasesPage.test.ts | FAIL (2 tests) |
| components/HomePage.test.ts | PASS |
| components/LearnedPathCatalogPage.test.ts | PASS |
| components/MainLayout.test.ts | PASS |
| components/VerificationBlock.test.ts | PASS |
| i18n/locales.test.ts | PASS |
| router/index.test.ts | PASS |
| stores/app.test.ts | PASS |
| stores/index.test.ts | PASS |
| utils/autonomousDisplay.test.ts | PASS |
| utils/index.test.ts | PASS |
| utils/json.test.ts | PASS |

### apps/e2e/tests/ (2 files)

| File | Tests | Domain |
|---|---|---|
| replay/api.spec.ts | 8 | replay API deterministic E2E |
| replay/catalog-ui.spec.ts | 1 | replay catalog UI browser E2E |

### apps/worker/tests/ (4 files)

| File | Tests | Domain |
|---|---|---|
| test_config.py | 1 | worker config defaults |
| test_logging.py | 1 | logging dict config |
| test_main.py | 1 | main entry point |
| test_runner.py | 2 | job runner lifecycle |

## 总计

| Metric | Count |
|---|---|
| Test files | 58 |
| Tests executed | 1099 |
| Passed | 1032 |
| Failed | 2 |
| Skipped | 65 |
| NOT_RUN | 0 |

## Autonomous 边界

| Check | Result |
|---|---|
| Called autonomous endpoint? | **NO** |
| Called /exploration/autonomous-runs? | **NO** |
| Called /exploration/autonomous-runs/stream? | **NO** |
| Depended on LLM provider? | **NO** |
| Modified product code? | **NO** |
| git diff --check | **exit 0** (clean) |

## 备注

1. **2 console test failures**: `AutonomousUseCasesPage.test.ts` references
   `vm.abortRunning` which no longer exists on the component. This is a
   component-test sync gap, not a product bug. The test needs updating to
   match the current component API.

2. **65 API skips**: All in `test_ast_simplifier.py` and `test_html_ast_parser.py`.
   These tests depend on HTML fixture files that are not committed to this
   checkout. The tests themselves are structurally correct; they just can't
   find their input data.

3. **E2E ran successfully**: All 9 replay E2E tests passed. Services (API,
   validation-site, console, PostgreSQL) were running. Replay seed fixtures
   were already in place.

4. **No conversation E2E**: No `apps/e2e/tests/conversation/` spec exists.
   Conversation has unit/repo/API/CLI coverage but no browser E2E.

5. **No visual UI exploratory**: This audit only runs automated tests. Visual
   UI exploratory requires headed browser observation with screenshots/traces.

## 后续候选项

| # | Candidate | Priority | Dependency |
|---|---|---|---|
| FU-01 | Fix 2 failing AutonomousUseCasesPage abort tests | P0 | sync test with current component |
| FU-02 | Run replay E2E as keep-running baseline | P0 | services running |
| FU-03 | Conversation API smoke as keep-running baseline | P0 | already passing |
| FU-04 | Conversation CLI smoke as keep-running baseline | P0 | already passing |
| FU-05 | LearnedPath trust / run-review separation smoke | P1 | new test needed |
| FU-06 | Console operator UI basic smoke | P1 | new test needed |
| FU-07 | Validation-site selector stability smoke | P1 | new test needed |
| FU-08 | AutonomousWorkbenchPage component test | P1 | 1001-line gap |
