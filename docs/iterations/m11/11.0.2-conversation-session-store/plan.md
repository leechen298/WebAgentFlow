# 实施计划

## 触及的文件 / 模块

> 本文件是 11.0.2 的实现规划，不表示这些文件当前已经存在。本包只做
> session / message / event store，不做 API endpoint、CLI 或 orchestrator
> side effects。

- `apps/api/app/models/conversation.py` —— ORM models for conversation
  sessions / messages / events。
- `apps/api/app/repos/conversation_repo.py` —— repository contract。
- `apps/api/alembic/versions/<revision>_add_conversation_tables.py` ——
  migration。
- `apps/api/tests/test_conversation_repo.py` —— repository tests。
- `apps/api/app/schemas/conversation.py` —— only if small schema alignment is
  needed; do not change core command / state contract。
- `docs/iterations/m11/11.0.2-conversation-session-store/review.md` ——
  implementation evidence after code work。

## 推荐数据模型

建议规划 3 张表。

### conversation_sessions

字段：

- `id`
- `status`
- `current_mode`
- `previous_status`
- `metadata_json`
- `created_at`
- `updated_at`

说明：

- `previous_status` 用于 pause / resume 语义，例如从 `replay_running` pause
  后可恢复。
- 不加 `user_id` / `account_id` / `tenant_id`。
- `metadata_json` 用于非核心字段，不作为账号体系。

### conversation_messages

字段：

- `id`
- `session_id`
- `role`
- `content`
- `metadata_json`
- `created_at`

说明：

- `session_id` 外键到 `conversation_sessions`。
- `role` 使用 11.0.1 的 `ConversationRole` 值。
- 不直接存 Agent 内部私有链路，只记录用户可审计 transcript。

### conversation_events

字段：

- `id`
- `session_id`
- `type`
- `payload_json`
- `created_at`

说明：

- `type` 使用 11.0.1 的 `ConversationEventType` 值。
- `payload_json` 记录状态变化、命令解析、engine event、replay event 等审计
  数据。
- 不包装 replay 为 `pass_gate` / Supervisor verdict。

## Repository contract

规划 repo 方法：

```text
create_session(initial_status=idle, current_mode=None, metadata=None)
get_session(session_id)
update_session_status(session_id, status, previous_status=None, current_mode=None, metadata_patch=None)
append_message(session_id, role, content, metadata=None)
append_event(session_id, type, payload=None)
list_messages(session_id, limit=100, cursor=None)
list_events(session_id, limit=100, cursor=None)
get_transcript(session_id)
```

要求：

- repo 方法不调用 LLM。
- repo 方法不调用 replay。
- repo 方法不调用 autonomous run。
- repo 方法不做 task planning。
- repo 方法只做 data access 和轻量 validation。

## Migration plan

- 新增三张 conversation 表。
- 推荐第一版 session delete 时 cascade delete messages / events。当前没有账号体系
  或长期托管存储语义，cascade delete 也方便测试清理。
- 索引：
  - `conversation_messages.session_id, created_at`
  - `conversation_events.session_id, created_at`
  - `conversation_sessions.updated_at`
- 不添加 user / account / tenant indexes。

## Test plan

至少规划以下 tests：

- create session defaults to `idle`。
- create session stores metadata。
- get session by id。
- update session status。
- update session `previous_status` for pause / resume。
- append user message。
- append system / engine message。
- append event。
- list messages ordered by `created_at`。
- list events ordered by `created_at`。
- `get_transcript` 第一版只返回 messages ordered by `created_at`；events 通过
  `list_events` 单独读取，避免把审计 event 混入用户 transcript。
- cascade delete / cleanup behavior。
- no user / account / tenant fields in models。
- repo does not import replay / autonomous / LLM modules。

## Implementation steps

1. Add ORM models。
2. Add Alembic migration。
3. Add repo。
4. Add repo tests。
5. Update `review.md` with evidence。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py
git diff --check
```

当前文档阶段只需要运行：

```bash
git diff --check
```
