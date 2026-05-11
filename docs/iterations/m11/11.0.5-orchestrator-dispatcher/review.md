# 审核与反思

## 规划初始化

- 本目录用于 11.0.5 Orchestrator Dispatcher。
- 当前状态：intent / plan 初始化，尚未实现代码。
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

## 待确认问题

- 后续是否需要 internal dispatch endpoint。
- 后续是否需要更丰富 structured response code。
- 后续是否需要 `dispatch_engine_event` 的真实实现。
