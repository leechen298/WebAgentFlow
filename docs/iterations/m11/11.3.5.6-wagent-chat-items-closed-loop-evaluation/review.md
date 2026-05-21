# 复盘 / 评审（Review）

状态：implementation complete（closed-loop pass，result recorded）

## 2026-05-21 设计文档生成

- Author：Codex
- Scope：生成 11.3.5.6 七件套，定义 `/items` `wagent chat` closed-loop evaluation。
- Decision：docs_created
- Notes：
  - 本包只定义测试方案和结果记录规则。
  - 未执行 `wagent chat`。
  - 未启动本地服务。
  - 未运行 `verify-scenario` 或 autonomous run。

## 设计评审（Design Review）

- Reviewer：ChatGPT
- Decision：pass
- Notes：Scope, contract, test matrix, evidence gates, and no-go boundaries are
  aligned. Ready for closed-loop execution.

## 闭环执行记录（Closed-loop Execution）

- Executor：Codex
- Date：2026-05-21
- Commit provenance：live run executed on base commit `0ff305f` with the
  11.3.5.6 fixes still uncommitted; those fixes were later committed as
  `18dcec1` (`fix: complete items chat closed-loop evaluation`)
- API base：`http://127.0.0.1:8001`
- Product URL：`http://127.0.0.1:5176/items`
- Session ID：`503a09ef-e609-4941-a82b-8f6e6be6061d`
- LearnedPath ID：`8c1ea100-9093-4138-9212-b74ce8e4e90b`
- Result file：
  [`docs/testing/results/m11-11.3.5.6-items-closed-loop-2026-05-21.md`](../../../testing/results/m11-11.3.5.6-items-closed-loop-2026-05-21.md)
- evaluation_status：`pass`

## 用户反馈

- Review feedback after first execution report:
  - `review.md` still showed pre-execution `not_run` state.
  - Result artifact commit provenance needed to mention uncommitted fixes.
  - Effective-value evidence needed raw event excerpts.
- Resolution：updated this review, M11 indexes, and the result artifact.

## 最终差异（Final Delta）

### 实际交付

- `wagent chat` `/items` closed loop executed from the product chat entry.
- Product-level static-page learning was fixed to accept LLM Supervisor
  `should_save_path=true` when the rule-side self verdict misses DOM-only
  success.
- Intake `project_name` was mapped to runtime `item_name` so replay receives
  `slot_overrides.item_name`.
- Result artifact recorded transcript, session, LearnedPath, replay, Reporter,
  not-run boundaries, and raw evidence excerpts.

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- Planned default output was evidence-only. During live execution, two blocking
  P0 wiring gaps were found and fixed narrowly:
  - `/items` learning did not persist a LearnedPath because the rule-side
    verdict required URL/title change even though the LLM Supervisor derived
    success from DOM state.
  - replay did not receive `slot_overrides.item_name` when intake emitted
    `semantic_type=project_name`.
- No schema, API, DB migration, CLI command, Console UI, recovery, TaskPathPlanner,
  `pending_choice`, or `active_task` scope was added.

### WebAgentFlow Live Run 边界（Live Run Boundary）

本包不运行 `verify-scenario` 或 autonomous run。闭环验证必须通过 `wagent chat`
产品入口执行，并把 Codex / AI 视为外部测试操作员。

如果执行阶段误触发 `verify-scenario` 或 autonomous run，必须在这里记录为越界，
不得作为本包通过证据。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 实际 `wagent chat` command：see result file `Commands`.
- stdout / stderr：captured in result file `Transcript`.
- session id：`503a09ef-e609-4941-a82b-8f6e6be6061d`.
- user input sequence：
  - `http://127.0.0.1:5176/items`
  - `学习新增项目，名称叫测试项目A-20260521223327`
  - `帮我新增项目，名称叫测试项目B-20260521223327`
- WAgent response：
  - `学习完成：我学会了新增项目操作。之后你可以说“帮我新增项目”。`
  - `执行完成。我在列表中看到了“测试项目B-20260521223327”，所以可以确认新增项目成功。`
- read-only evidence：
  - `chat_execution_started.slot_overrides.item_name=测试项目B-20260521223327`
  - `chat_execution_completed.replay.replay_status=succeeded`
  - `chat_execution_completed.replay.execution_evidence[0].status=verified`
  - `task_result_reported.verification_outcome=verified`
  - LearnedPath action includes `value_slot=item_name`

### Required Gates

| Gate | Expected | Actual | Status | Source |
|---|---|---|---|---|
| Chat session | session id exists | `503a09ef-e609-4941-a82b-8f6e6be6061d` | pass | CLI stdout / history |
| Learn A | LearnedPath generated | `chat_learning_completed`, LearnedPath `8c1ea100-9093-4138-9212-b74ce8e4e90b` | pass | conversation events |
| Parameter binding | `value_slot=item_name` | LearnedPath fill action has `value_slot=item_name` | pass | LearnedPath detail |
| Execute B | replay invoked with B | `slot_overrides.item_name=测试项目B-20260521223327` | pass | `chat_execution_started` |
| Effective value | fill value is B, not A | replay used B slot override and verified B in item list | pass | event raw excerpts in result file |
| DOM evidence | `dom_text_present verified target=B` | target `测试项目B-20260521223327`, status `verified`, confidence `0.95` | pass | `chat_execution_completed` |
| Reporter | outcome `verified` | `verification_outcome=verified`, `task_verified=true` | pass | `task_result_reported` |
| Final response | evidence-based success response | WAgent said it saw `测试项目B-20260521223327` in the list | pass | history messages |

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `git status --short --branch` | record baseline | branch `v0.1`; 11.3.5.6 code/tests/result docs were uncommitted during the run and later committed as `18dcec1` | 0 | Pass | terminal output | base commit `0ff305f` |
| product-test-site build | build passed | Vite build passed, 34 modules transformed | 0 | Pass | terminal output | `/items` target build |
| targeted API tests | passed | `143 passed` | 0 | Pass | pytest output | includes chat runtime, replay hook, reporter, learned replay, learning service |
| learned-path replay API slice | passed | `6 passed, 36 deselected` | 0 | Pass | pytest output | `tests/test_exploration_learned_paths_api.py -k replay` |
| scoped Ruff | clean | `All checks passed!` | 0 | Pass | terminal output | changed Python files |
| `wagent chat` closed loop | pass / fail / blocked / unverified | `pass` | 0 for resumed run | Pass | session `503a09ef-e609-4941-a82b-8f6e6be6061d` | first process timed out on first LLM turn; same session resumed with `--timeout 300` |
| read-only events / history queries | evidence captured | events, history, LearnedPath detail captured | 0 | Pass | result file raw excerpts | no direct replay substitution |
| `git diff --check` | clean | clean | 0 | Pass | terminal output | no whitespace errors |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| `verify-scenario` | 本包明确禁止 | 无 |
| autonomous run | 本包明确禁止 | 无 |
| Console UI smoke | 本包不依赖 Console | 无 |
| Failure Recovery | 属于 11.3.5.8 | 后续验证 |
| TaskPathPlanner multi-candidate | 属于 11.3.5.9 | 后续验证 |

### 后续事项（Follow-ups）

- `.venv/bin/alembic` shebang 指向旧路径
  `/Users/leechen/projects/WebAgentFlow/.venv/bin/python3.11`；本轮迁移使用
  `.venv/bin/python -m alembic`。

## 2026-05-21 空库重跑记录（Empty DB Rerun）

- Executor：Codex
- Data reset：
  - PostgreSQL `conversation_events`, `conversation_messages`,
    `conversation_sessions`, `learned_paths`, `exploration_runs` truncated with
    `RESTART IDENTITY CASCADE`.
  - Redis `FLUSHDB`.
- First empty-DB attempt：`unverified`，session
  `a0cb1c74-99f4-41b4-8cdc-3dcb1cb273ec`.
  - Finding：URL-only page inspection did not persist `pending_target`.
  - Symptom：following learning / execution turns produced
    `chat_no_path.reason=low_confidence_intake`.
- Follow-up fix：
  - `apps/api/app/services/conversation/chat_runtime.py` now saves
    `pending_target` after the inspect-page / understand-page path.
  - `apps/api/tests/test_conversation_chat_runtime.py` asserts the inspect route
    preserves the pending target URL.
- Final empty-DB rerun：`pass`.
  - Session ID：`3e2306d3-8414-4cb6-ba83-b2e19378815e`.
  - Learn item：`测试项目A-20260521232328`.
  - Execute item：`测试项目B-20260521232328`.
  - Learning run ID：`444378d9-e26f-4d6e-a40d-a09631cb5981`.
  - LearnedPath ID：`c4c86c45-3999-4850-ad46-02735f993f80`.
  - LearnedPath action：fill value `测试项目A-20260521232328`,
    `value_slot=item_name`.
  - Replay：`slot_overrides.item_name=测试项目B-20260521232328`,
    `replay_status=succeeded`, `drift_status=none`.
  - Evidence：`dom_text_present`, target
    `测试项目B-20260521232328`, `status=verified`, confidence `0.95`.
  - Reporter：`verification_outcome=verified`, `task_verified=true`.
  - Final response：`执行完成。我在列表中看到了“测试项目B-20260521232328”，所以可以确认新增项目成功。`
