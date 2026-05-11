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

### 测试覆盖

API 共 179 passed：

- `test_conversation_replay_hook.py` — 16 passed：
  - replay command calls handler and completes (succeeded)
  - replay observed also completes
  - replay drifted fails session
  - replay unsupported / failed / runtime_error / candidate_not_found fail session
  - replay handler exception maps to failed
  - free text does not call handler
  - malformed replay does not call handler
  - replay without handler stops at replay_requested
  - replay lifecycle events in correct order
  - replay event payload contains summary
  - replay status goes idle -> replay_running -> completed
  - replay uses exact path id (no selection)
  - orchestrator does not import autonomous / LLM / CLI

- `test_conversation_api.py` — 29 passed：
  - dispatch free text
  - dispatch missing session -> 404
  - dispatch malformed replay -> allowed=false, no replay
  - dispatch replay with missing path -> candidate_not_found, failed
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
# 179 passed

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
