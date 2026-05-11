# 审核与反思

## 规划初始化

- 本目录用于 11.0.6 Explicit Replay Command Hook。
- 当前状态：已实现并通过验证。
- 前置 M10.2 replay execution + drift detection 已完成。
- 前置 11.0.5 Orchestrator Dispatcher 已完成。
- 本包已将显式 `/replay <learned_path_id> <url>` command 接入 M10 replay capability。

## 已决策

- 11.0.6 可以调用 M10 replay service，但必须使用显式 `learned_path_id + url`。
- 不做 path selection。
- 不做 task-to-path planning。
- 新增 dispatch endpoint：`POST /conversation/sessions/{session_id}/dispatch`。
- `wagent conversation send` 改为调用 dispatch endpoint。
- 不新增 `wagent conversation replay` command。
- M10 replay result 不包装成 `pass_gate` 或 Supervisor verdict。
- Replay success / observed -> conversation completed。
- Replay drifted / unsupported / failed / runtime_error / candidate_not_found -> conversation failed。
- Conversation events 记录 replay lifecycle。
- 11.0.7 才做 conversation E2E / broader evidence。
- Replay hook 通过 handler / dependency injection 接入 Orchestrator；具体 handler 在 `replay_hook.py` 中调用 M10 replay service。
- `ConversationDispatchResponse.replay_result` 第一版使用 summary，不嵌入完整 replay step details。
- `replay_failed` 第一版不拆子事件类型；通过 summary 中的 `replay_status` / `drift_status` / `error` 区分 drift / unsupported / runtime_error 等。
- dispatch endpoint 第一版只接受 user input，不支持 non-user role。
- Internal `DispatchResult` 可保留 `engine_command`，但 public dispatch response 不暴露 `engine_command`。
- 11.0.6 不写 session metadata `last_replay_result`；replay lifecycle 只写 conversation events。
- malformed `/replay` 返回 HTTP 200 + `allowed=false` + error，不调用 replay。
- missing session 返回 HTTP 404。
- replay resource / runtime failures 返回 HTTP 200 + `replay_failed` event + replay result / error summary。
- Deprecated LearnedPath 不能通过 conversation replay hook 执行；必须返回
  `replay_status=deprecated` 的失败 summary，并记录为 replay failure。
- Dispatch request metadata 必须写入 user message metadata，并进入
  `command_parsed` audit payload，不允许静默丢弃。
- `DispatchResult.events_appended` 顺序必须和实际持久化 event 顺序一致。

## 实现证据

### 新增文件

- `apps/api/app/services/conversation/replay_hook.py` — ReplayHandler protocol + `run_explicit_replay()` bridge to M10 replay service。
- `apps/api/tests/test_conversation_replay_hook.py` — 16 个单元测试覆盖 replay hook + orchestrator 集成。

### 修改文件

- `apps/api/app/schemas/conversation.py` — 新增 `ConversationDispatchRequest`、`ConversationDispatchResponse`、`ConversationReplaySummary`。
- `apps/api/app/services/conversation/orchestrator.py` — 注入 `replay_handler`；REPLAY command 执行 hook 并更新状态 lifecycle（replay_requested -> replay_running -> completed/failed）。
- `apps/api/app/routers/conversation.py` — 新增 `POST /conversation/sessions/{session_id}/dispatch` endpoint；创建 Orchestrator 并注入 `run_explicit_replay` handler。
- `apps/cli/wagent/conversation.py` — `send` 从 `/messages` 改为 `/dispatch`。
- `apps/cli/tests/test_conversation.py` — 更新 `send` 测试为 dispatch endpoint。
- `apps/api/tests/test_conversation_api.py` — 新增 6 个 dispatch endpoint 测试。

### Hardening 补丁（2026-05-11）

- `apps/api/app/services/conversation/replay_hook.py`：
  - deprecated LearnedPath 直接返回 `ConversationReplaySummary(replay_status="deprecated")`。
  - 不调用 M10 `run_replay()`，避免绕过 M10 trust gate。
- `apps/api/app/services/conversation/orchestrator.py`：
  - `dispatch_user_input(..., metadata=None)` 接收 dispatch metadata。
  - user message metadata 持久化。
  - `command_parsed` payload 记录 `dispatch_metadata`。
  - replay lifecycle event 顺序调整为 running -> replay_completed / replay_failed -> final state_changed。
  - `events_appended` 与实际持久化 event 顺序保持一致。
- `apps/api/app/routers/conversation.py`：
  - dispatch endpoint 将 `ConversationDispatchRequest.metadata` 传入 orchestrator。
- `apps/api/tests/test_conversation_replay_hook.py`：
  - 覆盖 deprecated path 不调用 `run_replay()`。
  - 覆盖 dispatch metadata 持久化。
  - 覆盖 `events_appended` 顺序等于 persisted event type 顺序。
- `apps/api/tests/test_conversation_api.py`：
  - 覆盖 dispatch metadata 通过 API 写入 message / event。
  - 覆盖 mocked replay success 和 drifted dispatch response。
- `apps/cli/wagent/conversation.py` / `apps/cli/tests/test_conversation.py`：
  - 更新文件头注释，不再只描述为 11.0.3 store-level API client。

### 测试覆盖

API 共 184 passed：

- `test_conversation_replay_hook.py` — 18 passed：
  - replay command calls handler and completes (succeeded)
  - replay observed also completes
  - replay drifted fails session
  - replay unsupported / failed / runtime_error / candidate_not_found fail session
  - deprecated LearnedPath does not call M10 `run_replay`
  - replay handler exception maps to failed
  - free text does not call handler
  - malformed replay does not call handler
  - replay without handler stops at replay_requested
  - replay lifecycle events and returned `events_appended` stay in the same order
  - replay event payload contains summary
  - replay status goes idle -> replay_running -> completed
  - replay uses exact path id (no selection)
  - orchestrator does not import autonomous / LLM / CLI
  - dispatch metadata persists on user message and `command_parsed` event

- `test_conversation_api.py` — 32 passed：
  - dispatch free text
  - dispatch metadata persists on user message and audit event
  - dispatch missing session -> 404
  - dispatch malformed replay -> allowed=false, no replay
  - dispatch replay with missing path -> candidate_not_found, failed
  - dispatch replay success returns replay summary
  - dispatch replay drift returns failed summary
  - dispatch response does not expose engine_command
  - dispatch does not expose identity/tenant fields

- CLI — 67 passed：
  - send calls dispatch endpoint with input

### 验证结果

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_conversation_replay_hook.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py \
  tests/test_conversation_repo.py \
  tests/test_conversation_commands.py \
  tests/test_conversation_state.py \
  tests/test_learned_path_replay.py \
  tests/test_exploration_learned_paths_api.py -v
# 184 passed

cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v
# 67 passed

cd apps/api && ../../.venv/bin/ruff check \
  app/services/conversation/orchestrator.py \
  app/services/conversation/replay_hook.py \
  app/routers/conversation.py \
  app/schemas/conversation.py \
  tests/test_conversation_replay_hook.py \
  tests/test_conversation_api.py
# All checks passed!

git diff --check
# clean
```

### 边界遵守

- 未做 LearnedPath selection。
- 未做 natural-language task planning。
- 未做 slot binding。
- 未实现 Agent D / E / F / G / H。
- 未做 recovery / abort dialogue。
- 未做 teaching mode。
- 未做 artifact lifecycle。
- 未做 risk gate。
- 未做 multi-page workflow。
- 未调用 autonomous run。
- 未依赖 LLM provider。
- 未创建 M11.1 详情目录。
- 未新增 full external CLI / Skill / Tool。
- 未改变 M10 replay contract。
- 未把 replay result 包装成 `pass_gate` 或 Supervisor verdict。

## 待确认问题

- 后续是否需要完整 `ReplayResult` detail endpoint。
- 后续是否需要把 replay summary 写入 session metadata。
- 后续是否需要 public dispatch 支持 system / engine role。
