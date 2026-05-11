# 审核与反思

## 规划初始化

- 本目录用于 11.0.5 Orchestrator Dispatcher。
- 当前状态：已实现并通过验证。
- 前置 11.0.1 Conversation Domain Contract 已完成并通过测试。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 前置 11.0.3 Conversation API 已完成并通过测试。
- 前置 11.0.4 Runtime CLI Shell 已完成并通过测试。
- 本包将为 M11.0 runtime conversation 提供 service-only dispatcher 骨架。

## 已决策

- 11.0.5 不执行 replay side effect；explicit replay hook 属于 11.0.6。
- 11.0.5 不改 11.0.3 public API endpoint contract。
- 11.0.5 不新增 HTTP endpoint；只创建 backend service contract。
- 11.0.5 不新增 `wagent conversation` CLI 命令。
- `dispatch_user_input(session_id, raw_input)` 是本包核心 service contract。
- `dispatch_engine_event(session_id, event_type, payload)` 可以作为占位 contract，
  但 11.0.5 不执行 engine side effect。
- missing session 抛 `ValueError("session not found: ...")`。
- 每次 dispatch 都记录 user message 和 `command_parsed` event。
- transition allowed 时记录 transition event。
- status 发生变化时记录 `state_changed` event。
- invalid transition / allowed=false 不更新 session status，但必须记录 user
  message 和 `command_parsed` event，并记录 rejection / command error 审计信息。
- `/status` 会 append `command_parsed` event，但不更新 session status，不追加
  `state_changed`。
- `/cancel` 遵循 11.0.1 state contract，回到 `idle`，并清空
  `previous_status`。
- `/replay` 在 11.0.5 只 parse / transition 到 `replay_requested`，并记录
  `replay_requested` intent / audit event；不调用 replay API，不执行 replay
  side effect。
- `DispatchResult.engine_command` 可以作为 future hook 占位，但 11.0.5 永远不
  执行 `engine_command`。
- 11.0.5 使用 11.0.1 `ConversationTransitionResult.response_hint` 作为最小
  user-facing response；更丰富自然语言或结构化 response code 留给后续包。

## 实现证据

### 新增文件

- `apps/api/app/services/conversation/orchestrator.py` — Orchestrator / Dispatcher
  service。
- `apps/api/tests/test_conversation_orchestrator.py` — 17 个单元测试。

### 修改文件

- `apps/api/app/services/conversation/__init__.py` — export
  `ConversationOrchestrator` 和 `DispatchResult`。

### Service contract

```python
class ConversationOrchestrator:
    def __init__(self, repo: ConversationRepository) -> None: ...
    def dispatch_user_input(self, session_id: str, raw_input: str) -> DispatchResult: ...
    def dispatch_engine_event(
        self, session_id: str, event_type: ConversationEventType, payload: dict | None = None
    ) -> DispatchResult: ...
```

`DispatchResult` 字段：

- `session_id`
- `previous_status`
- `next_status`
- `command_kind`
- `user_response`
- `events_appended`
- `message_id`
- `allowed`
- `error`
- `engine_command` (占位，11.0.5 始终为 `None`)

### 测试覆盖

17 个测试全部通过：

- free text from idle → user message + `command_parsed` + `message_received` +
  `state_changed` + status `task_intake`
- free text from `task_intake` → stays `task_intake`
- `/status` → audit event only, no status mutation
- `/pause` → `paused`, stores `previous_status`
- `/resume` from `paused` → `task_intake`, clears `previous_status`
- `/abort` → `abort_requested`
- `/takeover` → `takeover_requested`
- `/cancel` → `idle`, clears `previous_status`
- invalid transition (`/resume` from `idle`) → `allowed=false`, no status change
- `/replay <id> <url>` → `replay_requested`, no replay execution
- malformed `/replay` → parse error, no status change
- `dispatch_engine_event` placeholder records event, no status mutation
- missing session for both dispatch methods → `ValueError("session not found: ...")`
- command_parsed event payload inspection
- state_changed event payload inspection
- orchestrator source does not contain replay / autonomous / LLM / CLI imports

### 验证结果

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_orchestrator.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_conversation_api.py -v
# 101 passed

cd apps/api && ../../.venv/bin/ruff check app/services/conversation/orchestrator.py app/services/conversation/__init__.py tests/test_conversation_orchestrator.py
# All checks passed

git diff --check
# clean
```

### 边界遵守

- 未调用 replay API。
- 未实现 `/replay` command side effect。
- 未做 Agent D / E / F / G / H。
- 未做 task-to-path planning。
- 未做 slot binding。
- 未调用 autonomous run。
- 未依赖 LLM provider。
- 未新增 CLI 命令。
- 未新增 HTTP endpoint。
- 未创建 M11.1 详情目录。
- 未加入 user / account / tenant 字段。

## 待确认问题

- 后续是否需要 internal dispatch endpoint。
- 后续是否需要更丰富 structured response code。
- 后续是否需要 `dispatch_engine_event` 的真实实现。
