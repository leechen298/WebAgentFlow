# 审核与反思

## 实际交付

- 新增 `apps/api/app/schemas/conversation.py`。
- 新增 `apps/api/app/services/conversation/__init__.py`。
- 新增 `apps/api/app/services/conversation/commands.py`。
- 新增 `apps/api/app/services/conversation/state.py`。
- 新增 `apps/api/tests/test_conversation_commands.py`。
- 新增 `apps/api/tests/test_conversation_state.py`。

## Contract 实现

已实现的 status：

- `idle`
- `task_intake`
- `awaiting_confirmation`
- `replay_requested`
- `replay_running`
- `paused`
- `abort_requested`
- `takeover_requested`
- `completed`
- `failed`

已实现的 role：

- `user`
- `system`
- `agent`
- `engine`

已实现的 event type：

- `session_created`
- `message_received`
- `command_parsed`
- `state_changed`
- `replay_requested`
- `replay_completed`
- `replay_failed`
- `pause_requested`
- `resume_requested`
- `abort_requested`
- `takeover_requested`
- `session_completed`
- `session_failed`

已实现的 command kind：

- `status`
- `cancel`
- `pause`
- `resume`
- `abort`
- `takeover`
- `replay`
- `free_text`
- `error`

`parse_command(raw)` 是纯函数，只做字符串解析。`/replay <learned_path_id>
<url>` 只检查参数是否存在，不校验 path 是否存在，不做 URL parse。

`next_state(current_status, command)` 是纯函数，只返回
`ConversationTransitionResult`。11.0.1 不记录 previous status，因此 `/resume`
从 `paused` 固定回到 `task_intake`；`/cancel` 从非终态回到 `idle`。

## 验证结果

已运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_commands.py tests/test_conversation_state.py
```

结果：

```text
29 passed in 0.03s
```

## 范围边界确认

- 未做 DB / persistence。
- 未做 API endpoint。
- 未做 CLI command。
- 未调用 replay API。
- 未实现 orchestrator side effects。
- 未实现 Agent D / E / F / G / H。
- 未做 task-to-path planning。
- 未做 slot binding。
- 未调用 autonomous run。
- 未依赖 LLM provider。
- 未做 E2E。
- 未创建 M11.1 详情目录。

## 待确认问题

- `ConversationStatus` 是否需要区分 `task_intake` 和 `free_text_received`。
- `/cancel` 与 `/abort` 的语义是否需要区分。
- `/takeover` 在 M11.0 是 placeholder，还是需要明确 transition。
- replay command 的 URL 是否只做字符串格式检查，还是需要 URL parse。
- 是否需要 `error` / `unknown_command` command kind。

## Follow-up

- 11.0.2 Conversation session store：决定并实现 session / message / event
  存储。
- 11.0.3 Conversation API：暴露 session create / append message / status 等
  endpoint。
- 11.0.4 Runtime CLI shell：在 `wagent` 中增加 runtime conversation 入口。
- 11.0.5 Orchestrator dispatcher：接入状态转移和 user-facing response。
- 11.0.6 Explicit replay command hook：通过 orchestrator 显式调用 M10 replay。
