# 实施计划

## 触及的文件 / 模块

> 本文件是后续实现计划，不表示这些文件当前已经存在。本包只定义领域
> contract 和纯逻辑，不接 DB、API、CLI 或 replay side effects。

- `apps/api/app/schemas/conversation.py`
- `apps/api/app/services/conversation/__init__.py`
- `apps/api/app/services/conversation/commands.py`
- `apps/api/app/services/conversation/state.py`
- `apps/api/tests/test_conversation_commands.py`
- `apps/api/tests/test_conversation_state.py`

## Domain contract

`ConversationStatus`：

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

`ConversationRole`：

- `user`
- `system`
- `agent`
- `engine`

`ConversationEventType`：

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

`ConversationCommand`：

```text
kind:
- status
- cancel
- pause
- resume
- abort
- takeover
- replay
- free_text

fields:
- raw
- args
- learned_path_id optional
- url optional
- text optional
```

`ConversationSession` / `ConversationMessage` / `ConversationEvent` 在本包只定义
schema contract，不新增 persistence 决策，不加入 user / account / tenant 字段。

## Parser contract

- `/status` -> `status` command。
- `/pause` -> `pause` command。
- `/resume` -> `resume` command。
- `/abort` -> `abort` command。
- `/takeover` -> `takeover` command。
- `/cancel` -> `cancel` command。
- `/replay <learned_path_id> <url>` -> `replay` command。
- 其他输入 -> `free_text` command。
- `/replay` 缺少 `learned_path_id` 或 `url` 时返回 parse error，不执行 replay。
- parser 是纯函数，不做 IO，不调用 API，不调用 replay，不调用 LLM。

## State transition contract

规划纯函数：

```text
next_state(current_status, command_or_event) -> transition_result
```

`transition_result` 包含：

- `next_status`
- `response_hint`
- `event_type`
- `allowed`
- `error optional`

状态转移函数只返回决策结果，不执行 side effects：

- 不写 DB。
- 不调用 replay。
- 不调用 LLM。
- 不调用 autonomous run。
- 不触发 browser action。

建议初版规则：

- `status` command 可从任何状态读取当前状态，状态不变。
- free-form task text 从 `idle` 进入 `task_intake`。
- `pause` 只允许从 `task_intake` / `replay_running` 进入 `paused`。
- `resume` 只允许从 `paused` 回到可恢复前态；如果前态不可恢复，返回
  `allowed=false`。
- `abort` 从非终态进入 `abort_requested`。
- `takeover` 从非终态进入 `takeover_requested`。
- `replay` 从 `idle` / `task_intake` 进入 `replay_requested`。
- `completed` / `failed` 是终态，除 `status` 外的命令默认
  `allowed=false`。

## 测试计划

后续实现时至少覆盖：

- parse `/status`。
- parse `/pause`。
- parse `/resume`。
- parse `/abort`。
- parse `/takeover`。
- parse `/cancel`。
- parse `/replay <learned_path_id> <url>`。
- `/replay` 缺参数返回 parse error。
- free text 映射为 `free_text` command。
- `status` command 从任意状态都 allowed。
- `pause` 只从明确允许的状态进入 `paused`。
- `resume` 从 `paused` 返回可恢复状态。
- `abort` 进入 `abort_requested`。
- `takeover` 进入 `takeover_requested`。
- invalid transition 返回 `allowed=false` 和 error。
- schema 中不出现 user / account / tenant 字段。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_commands.py tests/test_conversation_state.py
git diff --check
```

当前文档阶段只需要运行：

```bash
git diff --check
```
