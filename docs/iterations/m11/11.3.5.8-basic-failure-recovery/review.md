# 复盘 / 评审（Review）

状态：implementation complete（code review passed，targeted tests passed）

## 2026-05-22 文档生成

- Author：Codex
- Scope：生成 11.3.5.8 七件套，定义基础失败恢复、replay retry、relearn、cancel
  和 targeted test plan。
- Decision：docs_created
- Notes：
  - 本包属于 P2 runtime robustness。
  - 本包不改变 11.3.5.3 - 11.3.5.6 P0 working loop。
  - 本包复用 11.3.5.7 `pending_choice` / `active_task`。
  - 未实现代码。
  - 未运行 pytest / ruff / build。
  - 未运行 `verify-scenario` 或 autonomous run。

## 设计评审（Design Review）

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - 11.3.5.7 preflight dependency 已写清楚。
  - retry 副作用风险已写入 contract / wording / test plan。
  - recovery event private payload 禁止清单已补齐。
  - scope 保持 basic failure recovery，不做复杂自治恢复。

## 2026-05-22 设计反馈修订

- Reviewer：ChatGPT
- Decision：revisions_applied
- Notes：
  - 明确 11.3.5.7 `pending_choice` / private map / `active_task` 是实现前置，
    11.3.5.8 实现前必须 preflight 确认。
  - 明确 retry 是再次执行，不是重新检查；在 evidence missing / uncertain / needs_review
    下可能重复副作用，用户可见文案必须提示。
  - 明确 recovery events 不得记录 private retry / relearn payload、`slot_overrides`、
    `learned_path_id`、`evidence_targets`、selector 或 ReplayAction。

## 2026-05-22 设计评审通过

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - 11.3.5.7 `pending_choice` / private map / `active_task` preflight dependency
    已写清楚。
  - retry 是再次执行、可能重复副作用的风险已写入 contract / wording / test plan。
  - recovery event private payload 禁止清单已补齐。
  - scope 保持 basic failure recovery，不做复杂自治恢复。

## 代码评审（Code Review）

- Reviewer：User
- Decision：pass
- Notes：
  - 未发现阻断问题，可以进入收口。
  - 重点复核了 `chat_runtime.py` 的 failure classification、pending choice 分支、
    retry / relearn / cancel 处理，以及 recovery event payload。
  - 实现基本对齐 11.3.5.8：失败后提供 A/B/C；retry 走 direct replay；
    relearn 进入 learning branch 且不自动 replay；cancel 清理 runtime context；
    recovery events 没有写入 `learned_path_id` / `slot_overrides` /
    `evidence_targets` / private map。
  - Reviewer 本地补跑 focused 测试：
    `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -k "recovery or does_not_claim_success_without_evidence"`，
    结果 `7 passed, 51 deselected`；`git diff --check` 通过。
  - 非阻断观察：retry private map 保存了 `evidence_targets`，但当前 retry
    实际通过 `_execute_matched_action()` 重新构造 `/items` evidence target。
    对当前 `/items + item_name` 路径等价，不影响本包验收；如果后续支持更多
    evidence target 类型，再考虑把 evidence target override 显式传进 retry。

## 用户反馈

- 用户确认代码评审未发现阻断问题，可以进入下一步收口。

## 2026-05-22 实现收口

- Author：Codex
- Code commit：`f7771b8 feat: add basic chat failure recovery`
- Decision：implementation_complete
- Notes：
  - 实现 Basic Failure Recovery 的 conservative A/B/C recovery menu。
  - replay failed / blocked / evidence missing / `needs_review` / `uncertain`
    后由 runtime 提供恢复选项，不编造成果。
  - 用户选择 A 时 direct replay 同一个 learned action，保留原
    `slot_overrides`；retry 失败后只重新展示 recovery menu，不自动循环。
  - 用户选择 B 时进入 learning branch，不自动 replay 旧失败任务。
  - 用户选择 C 或中文取消语义时清理 pending runtime context。
  - recovery progress events 只记录 public diagnostics，不记录
    `learned_path_id` / `slot_overrides` / `evidence_targets` / private map。

## 最终差异（Final Delta）

### 实际交付

- `apps/api/app/services/conversation/chat_runtime.py`
  - 新增 failure classification：`replay_failed`、`blocked`、
    `evidence_missing`、`needs_review`、`uncertain`。
  - 新增 recovery pending choice builder，visible payload 只展示：
    `A. 重试执行该操作` / `B. 重新学习` / `C. 取消`。
  - 扩展 pending choice selection，支持 `retry_replay`、
    `relearn_operation`、`cancel`，并保持 11.3.5.7 `learned_action`
    普通 choice 行为不变。
  - 新增 retry / relearn / cancel recovery progress events，payload
    不包含 private execution payload。
- `apps/api/tests/test_conversation_chat_runtime.py`
  - 覆盖 replay failed、blocked drift、evidence missing、retry payload
    preservation、retry no auto-loop、relearn no replay、cancel cleanup
    和 recovery event redaction。
- 同步状态索引：
  - `docs/iterations/m11/11.3.5.8-basic-failure-recovery/README.md`
  - `docs/iterations/m11/README.md`
  - `docs/iterations/m11/m11-plan.md`

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- 无阻断偏差。
- 非阻断观察：retry private map 保存 `evidence_targets`，但当前 retry
  仍通过 `_execute_matched_action()` 根据 action + slot 重新构造 `/items`
  evidence target。对当前 `/items + item_name` 验收等价；后续支持更多
  evidence target 类型时，可显式把 evidence target override 接入 retry。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本包不运行 `verify-scenario` 或 autonomous run。

如果后续用户显式要求 live smoke，只能作为外部测试操作员通过 `wagent chat`
记录真实输出；不得调用 autonomous-run endpoint，不得编造内部 Agent verdict。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 本包没有 E2E / UI smoke。
- 本包没有 CLI live run。
- 本包验收基于 mocked replay / learning 的 runtime targeted tests。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| 11.3.5.7 preflight targeted tests | pending choice / active task / slot override / sanitizer base works | 8 passed, 106 deselected | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_api.py -k "pending_choice or active_task or slot_overrides or public_payload or hides_pending_choice_private_map"` | Preflight only |
| Recovery focused tests | recovery behavior and non-success wording pass | 7 passed, 51 deselected | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -k "recovery or does_not_claim_success_without_evidence"` | Re-run after review |
| First test-plan targeted suite | chat runtime / API sanitizer / entry gate / router agent pass | 144 passed | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_api.py tests/test_conversation_entry_gate.py tests/test_conversation_router_agent.py` | Required targeted suite |
| Second test-plan targeted suite | replay hook / reporter / learned-path replay / learning service pass | 156 passed | 0 | Pass | `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py tests/test_conversation_replay_hook.py tests/test_task_planning_result_reporter.py tests/test_learned_path_replay.py tests/test_learning_run_service.py` | Required targeted suite |
| scoped Ruff | changed Python files clean | All checks passed | 0 | Pass | `uv run ruff check apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/context.py apps/api/app/services/conversation/history.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_api.py` | Test-plan command |
| `git diff --check` | clean | clean | 0 | Pass | `git diff --check` | Whitespace check |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| `wagent chat` live smoke | 本包默认 targeted tests，不要求 live run | 如后续需要手工验证再记录 |
| `verify-scenario` | 本包明确禁止 | 无 |
| autonomous run | 本包明确禁止 | 无 |
| TaskPathPlanner | 属于 11.3.5.9 | 后续接入 |
| Complex Failure Recovery | 超出本包基础恢复范围 | M12 或后续恢复包 |

### 后续事项（Follow-ups）

- 后续支持更多 evidence target 类型时，考虑把 recovery private map 中的
  `evidence_targets` 显式作为 retry override 传入 replay path。
- 11.3.5.9 可继续处理 TaskPathPlanner multi-candidate chat integration。
