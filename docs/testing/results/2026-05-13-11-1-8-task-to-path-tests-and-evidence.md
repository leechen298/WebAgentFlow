# 11.1.8 Task-to-path Tests and Evidence

## Scope

M11.1 task-to-path MVP 测试与证据收口包。验证 11.1.1–11.1.7 实现链的
确定性回归、负面路径覆盖、E2E 证据和静态审查结果。

```text
ordinary task -> preview -> awaiting_confirmation -> confirm -> plan_confirmed
-> execute -> executing -> replay -> task_result_reported -> execution_finished/execution_failed
```

## Commands Run

### Focused API / Service Tests

```bash
cd apps/api
../../.venv/bin/pytest \
  tests/test_task_path_planner.py \
  tests/test_task_planning_preview.py \
  tests/test_conversation_confirmation.py \
  tests/test_conversation_execution.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py \
  -q
```

结果：`223 passed in 0.81s`

补充 schema / retrieval 测试：

```bash
cd apps/api
../../.venv/bin/pytest tests/test_task_planning_schemas.py tests/test_task_planning_retrieval.py -q
```

结果：`71 passed in 0.18s`

### Full API Regression

```bash
cd apps/api
../../.venv/bin/pytest -q
```

结果：`1104 passed, 65 skipped in 24.55s`

### Ruff

```bash
cd apps/api
../../.venv/bin/ruff check \
  app/schemas/conversation.py \
  app/services/conversation \
  app/services/task_planning \
  tests/test_task_path_planner.py \
  tests/test_task_planning_preview.py \
  tests/test_conversation_confirmation.py \
  tests/test_conversation_execution.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py \
  tests/test_task_planning_schemas.py \
  tests/test_task_planning_retrieval.py
```

结果：`All checks passed!`

### Scoped E2E (task-execution)

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/task-execution.spec.ts
```

结果：`3 passed (4.0s)`

### Full E2E

```bash
pnpm run test:e2e
```

结果：`25 passed (13.4s)`

## Results

### Focused API / Service Tests

| 测试文件 | 通过 | 说明 |
|---|---|---|
| `test_task_path_planner.py` | 21 | Task Path Planner MVP：无候选、confirmed、provisional、flaky、ambiguous |
| `test_task_planning_preview.py` | 9 | Planning preview service：retrieval + planner 串联 |
| `test_conversation_confirmation.py` | 32 | Confirmation gate：confirm/cancel/reject/ambiguous/slash commands |
| `test_conversation_execution.py` | 14 | Execution service：intent classification、context extraction、validation、multi-step block |
| `test_task_planning_result_reporter.py` | 24 | Result Reporter：blocked/failed/drift/error/uncertain/observed、payload markers、structured fields |
| `test_conversation_orchestrator.py` | 95 | Orchestrator：planning preview、confirmation gate、execution gate、event order、replay hook |
| `test_conversation_api.py` | 28 | API dispatch：preview、confirm、execute、blocked、failed、explicit replay |
| **合计** | **223** | — |

补充：

| 测试文件 | 通过 | 说明 |
|---|---|---|
| `test_task_planning_schemas.py` | 33 | Task planning domain contract：17 schema 定义 |
| `test_task_planning_retrieval.py` | 38 | LearnedPath retrieval and ranking：评分、过滤、排序 |
| **合计** | **71** | — |

### Full API Regression

`1104 passed, 65 skipped in 24.55s`

Skipped 测试均为外部服务依赖（LLM provider、autonomous run、browser sandbox
相关），不触及 M11.1 业务逻辑。

### Scoped E2E

`task-execution.spec.ts`（3 tests）：

- **E2E-11-1-6-001A**：seeded confirmed execution context executes replay
  - session status: idle → awaiting_confirmation → plan_confirmed → executing → execution_finished
  - event order: plan_preview_proposed → plan_confirmed → command_parsed → state_changed(executing) → plan_execution_started → plan_execution_completed → task_result_reported → state_changed(execution_finished)
  - `task_result_reported.verification_outcome = "uncertain"`
  - `task_result_reported.needs_review = true`
  - `task_result_reported.task_verified = false`
  - final assistant message: contains "could not verify"
  - **PASS**

- **E2E-11-1-6-001B**：natural planning flow blocks execution without target_url
  - session status stays plan_confirmed
  - events contain `plan_execution_blocked` and `task_result_reported`
  - no `plan_execution_started` / `plan_execution_completed` / `replay_completed`
  - `task_result_reported.verification_outcome = "blocked"`
  - **PASS**

- **E2E-11-1-6-002**：explicit replay cannot bypass pending or confirmed plan flow
  - `/replay` while awaiting_confirmation → blocked by confirmation gate
  - `/replay` while plan_confirmed → blocked by state machine
  - **PASS**

### Full E2E

25 tests passed across:

- `tests/replay/api.spec.ts` — LearnedPath replay API (happy path, drift, flaky, deprecated)
- `tests/replay/catalog-ui.spec.ts` — catalog list, trust filter, drawer, seeded replay
- `tests/conversation/runtime.spec.ts` — explicit replay dispatch + transcript/events
- `tests/conversation/cli-runtime.spec.ts` — CLI-driven replay
- `tests/conversation/task-execution.spec.ts` — 11.1.6 scoped execution
- `tests/conversation/task-result-reporter.spec.ts` — 11.1.7 reporter (uncertain/failed/blocked)
- `tests/validation-site/browser-smoke.spec.ts` — fixture page controls

## Event / State Evidence

### Happy path event sequence (E2E-11-1-6-001A)

```
1. plan_preview_proposed
2. plan_confirmed
3. command_parsed (gate=plan_confirmed, raw=execute)
4. state_changed (plan_confirmed -> executing)
5. plan_execution_started
6. plan_execution_completed
7. task_result_reported (verification_outcome=uncertain)
8. state_changed (executing -> execution_finished)
```

### Blocked path event sequence (E2E-11-1-6-001B)

```
1. plan_execution_blocked (reason=missing_execution_context, missing_fields=[target_url])
2. task_result_reported (verification_outcome=blocked)
```

No `plan_execution_started` / `replay_completed`.

### Failed path event sequence (E2E-11-1-7-002)

```
1. plan_execution_started
2. plan_execution_failed
3. task_result_reported (verification_outcome=failed)
4. state_changed (executing -> execution_failed)
```

## Result Reporter Evidence

### Outcome matrix (from service tests + E2E)

| 条件 | Outcome | needs_review | task_verified |
|---|---|---|---|
| Execution blocked | `blocked` | False | False |
| Replay failed / drifted / error | `failed` | False | False |
| Replay succeeded/observed + no postcondition | `uncertain` | True | False |
| Replay succeeded/observed + explicit postcondition | `verified` | False | True |

第一版 `_check_postconditions` 恒返回 `False`，所以 `verified` 路径当前未被触发。

### Payload markers

所有 `task_result_reported` payload 包含：
- `no_recovery: true`
- `no_autonomous: true`
- `no_llm: true`

E2E `expectNoForbiddenReporterPayload` 验证 payload 不含：
- `raw_html`, `screenshot`, `llm_output`, `supervisor_output`, `autonomous_run_id`
- `user_id`, `account_id`, `tenant_id`
- `task_succeeded`, `success_assertion`, `verified_success`

### Structured payload fields (follow-up fix)

`task_result_reported` payload 新增：
- `execution_status`
- `replay_status`
- `drift_status`
- `error_summary`
- `final_url`
- `final_title`

E2E 已断言这些字段在 completed / failed / blocked 场景下的正确值。

## Static Review Findings

### P1 (阻塞 / 会导致错误执行或错误成功结论)

**无。**

### P2 (重要正确性 / 审计链缺陷)

**无。**

### P3 (文案、覆盖、证据质量问题)

**无必须修复项。**

审查确认：

1. **replay completed != task succeeded**：`result_reporter.py` 中 replay succeeded + no postcondition → `uncertain`。E2E 和 service tests 均验证。
2. **confirmation 不可绕过**：`confirmation.py` 使用精确匹配 allowlist；ambiguous 输入不视为 consent。orchestrator 的 confirmation gate 拦截所有 FREE_TEXT 输入。E2E 验证 `/replay` 在 awaiting_confirmation 下被阻断。
3. **`/replay` 不绕过 plan_confirmed**：state machine 对 plan_confirmed + REPLAY 返回 blocked；E2E 验证。
4. **missing target_url 不脑补**：`execution.py` `validate` 中无 target_url → blocked；E2E 验证。
5. **Reporter 不脑补成功**：`_check_postconditions` 恒返回 `False`；无 postcondition → `uncertain`。
6. **failed/uncertain 不触发 recovery**：所有 outcome payload 含 `no_recovery: true`；user response 明确说明 "no recovery was attempted"。
7. **event order 与 state transition 一致**：orchestrator 中 started → completed/failed → reported → state_changed 的顺序与 E2E event index 验证一致。
8. **final assistant message 与 event payload 一致**：orchestrator 使用 reporter `user_response` 作为 final message；metadata 中的 `verification_outcome` 与 event payload 一致；E2E transcript 验证。
9. **docs 状态正确**：11.1.1–11.1.7 标记为完成；11.1.8 标记为 documentation initialized；slot binding 标记为 future。

## Environment Caveats

- 测试在本地开发环境运行（macOS，PostgreSQL 16 via Docker，Redis，MinIO）。
- Full E2E 使用 Playwright Chromium headless，依赖 validation-site 和 API backend。
- 65 个 skipped 测试均为外部依赖（LLM provider、browser sandbox、autonomous run），非 M11.1 业务缺陷。
- 无 environment-blocked 的 E2E 失败。

## Follow-up Issues

- `_check_postconditions` 当前恒返回 `False`。`verified` outcome 需要未来显式 postcondition evidence 集成（如 artifact reference、structured success signal）。这不是 11.1.8 的缺陷，是已知实现边界。
- `ConversationStatus` 没有 `result_verified`/`result_failed`/`result_uncertain` 状态。verification outcome 仅通过 event payload 和 message metadata 承载。这是设计选择，不是缺陷。
- Slot Binding 仍为 future scope，未分配执行包编号。

## Final Assessment

M11.1 task-to-path MVP 测试与证据收口完成。

- 1104 API tests passed，65 skipped（外部依赖）。
- 25 E2E tests passed，无 environment-blocked 失败。
- ruff clean。
- `git diff --check` clean。
- 无 11.1.9 目录。
- 静态审查无 P1/P2 发现。
- 所有关键安全边界（replay completed != task succeeded、no recovery、blocked reporting、event order）均有测试覆盖和 E2E 证据。
