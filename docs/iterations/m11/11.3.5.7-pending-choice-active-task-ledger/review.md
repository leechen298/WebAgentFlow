# 复盘 / 评审（Review）

状态：implementation complete（code review passed，targeted tests passed）

## 2026-05-21 文档生成

- Author：Codex
- Scope：生成 11.3.5.7 七件套，定义 `pending_choice`、私有映射、最小
  `active_task` ledger、cancel cleanup 和 targeted test plan。
- Decision：docs_created
- Notes：
  - 本包属于 P1 runtime robustness，不改变 11.3.5.3 - 11.3.5.6 P0 working loop。
  - 未实现代码。
  - 未运行 pytest / ruff / build。
  - 未运行 `verify-scenario` 或 autonomous run。

## 设计评审（Design Review）

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - Scope, `pending_choice` contract, private map boundary, minimal
    `active_task` ledger, cancel cleanup, and no-go boundaries are aligned.
  - Ready for implementation.

## 代码评审（Code Review）

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - 代码方向通过；`pending_choice` / private map / minimal `active_task`
    能力已经进入 runtime，并被 11.3.5.8 / 11.3.5.9 后续包复用。
  - private map 和 `learned_path_id` 用户可见层脱敏边界已补齐。
  - choice selection 保留 runtime `slot_overrides`，不会把参数化 replay 退回固定录制值。
  - 仍建议补独立 closeout 记录；本文件即为本轮收口记录。

## 用户反馈

- 用户确认最新整体状态可以继续，但要求把 11.3.5.7 的独立 closeout 记录补齐。

## 2026-05-22 实现收口

- Author：Codex
- Code commit：`0e9ee97 fix: secure pending choice replay slots`
- Decision：implementation_complete
- Notes：
  - 实现 `pending_choice` / private map / deterministic choice parser。
  - 实现 minimal `active_task` metadata，让 learning / execution / clarify
    具备 code-owned live task state。
  - Entry Gate 在 pending choice / active task 存在时进入 heavy runtime，
    避免 `A` / `1` / `第一个` / `继续` 等短输入被普通 Router 误判。
  - choice visible payload 不包含 `learned_path_id`、selector、browser action、
    `slot_overrides` 或 private map。
  - session public payload 递归清理 private map 和 `learned_path_id`。
  - 用户选择 pending choice 后，Runtime 从 private map 内部解析真实 learned action，
    并保留安全 runtime slots。

## 最终差异（Final Delta）

### 实际交付

- `apps/api/app/services/conversation/context.py`
  - 增加 `pending_choice` / `active_task` context parsing。
- `apps/api/app/services/conversation/entry_gate.py`
  - pending choice / active task 存在时强制进入 heavy runtime。
- `apps/api/app/services/conversation/chat_runtime.py`
  - 实现 pending choice 创建、选择解析、修正输入重入 intake、过期清理、
    cancel cleanup 和 minimal active task updates。
  - pending choice private map 保存内部 learned action payload；
    visible choice 只暴露 public choice id / label / description / intent。
  - 选择执行时保留 `slot_overrides`，避免参数化 replay 丢失 `record_name`。
- `apps/api/app/services/conversation/history.py`
  - 对 session public payload 做递归脱敏，避免 private map / `learned_path_id`
    外泄到普通 session response。
- `apps/api/app/routers/conversation.py`
  - session response 复用 public sanitizer。
- `apps/api/app/services/conversation/intake.py`、
  `apps/api/app/services/conversation/router_agent.py`、
  `apps/api/app/services/conversation/orchestrator.py`
  - 配合 choice / active task 语义和 LLM-facing payload safety。
- Tests：
  - 覆盖 choice parser、pending choice 创建 / 选择 / 过期 / 修正 / cancel、
    active task learning / execution、session API 脱敏和 single-path regression。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- 无阻断偏差。
- 后续 11.3.5.8 / 11.3.5.9 继续复用并扩展该状态底座；本包自身仍不接
  TaskPathPlanner，不做 Failure Recovery 菜单。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本包不运行 `verify-scenario` 或 autonomous run。

如果后续用户显式要求 live smoke，只能作为外部测试操作员通过 `wagent chat` 记录真实输出；
不得调用 autonomous-run endpoint，不得编造内部 Agent verdict。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 本包没有 E2E / UI smoke。
- 本包没有 CLI live run。
- 本包验收基于 mocked runtime / API targeted tests。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| conversation targeted suite | pending choice / active task / API sanitizer / router / entry gate pass | 151 passed | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_api.py tests/test_conversation_entry_gate.py tests/test_conversation_router_agent.py` | Re-run during closeout |
| focused runtime slice | planner / pending choice / recovery / items regressions pass | 19 passed, 46 deselected | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -k "planner or pending_choice or recovery or items"` | Includes later packages that reuse 11.3.5.7 |
| scoped Ruff | changed Python / test files clean | All checks passed | 0 | Pass | `uv run ruff check apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/context.py apps/api/app/services/conversation/history.py apps/api/app/routers/conversation.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_api.py apps/api/tests/test_conversation_entry_gate.py apps/api/tests/test_conversation_router_agent.py` | Closeout check |
| `git diff --check` | clean | clean | 0 | Pass | `git diff --check` | Closeout check |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| `wagent chat` live smoke | 本包默认 targeted tests，不要求 live run | 如后续需要手工验证再记录 |
| `verify-scenario` | 本包明确禁止 | 无 |
| autonomous run | 本包明确禁止 | 无 |
| TaskPathPlanner multi-candidate | 属于 11.3.5.9 | 已在后续包接入 |
| Failure Recovery menu | 属于 11.3.5.8 | 已在后续包接入 |

### 后续事项（Follow-ups）

- 如后续把 history/debug payload 暴露给普通用户或 LLM prompt，需要单独定义
  `learned_path_id` 在 debug event 中的可见性策略。
