# 审核与反思

## 规划初始化

- 本目录用于 11.0.2 Conversation Session Store。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.0.1 Conversation Domain Contract 已完成并通过测试。
- 本包将为 M11.0 后续 API、CLI、orchestrator 提供 session / message /
  event 数据层。

## 实现证据

### 新增文件

- `apps/api/app/models/conversation.py` — ORM 模型（3 张表）。
- `apps/api/app/repos/conversation_repo.py` — repository contract。
- `apps/api/alembic/versions/a93d26f33594_add_conversation_tables.py` — migration。
- `apps/api/tests/test_conversation_repo.py` — 32 个 repo 测试全部通过。

### 修改文件

- `apps/api/app/models/__init__.py` — 导出 `ConversationSession` /
  `ConversationMessage` / `ConversationEvent`。

### 数据模型

#### conversation_sessions

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | String(36) PK | UUID |
| `status` | String(32) | 默认 `idle` |
| `current_mode` | String(32) nullable | 当前模式 |
| `previous_status` | String(32) nullable | pause / resume 语义 |
| `metadata_json` | JSON | 扩展字段 |
| `created_at` | DateTime(tz) | server_default now() |
| `updated_at` | DateTime(tz) | server_default now() |

索引：`ix_conversation_sessions_updated_at`

#### conversation_messages

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | String(36) PK | UUID |
| `session_id` | String(36) FK → sessions.id ON DELETE CASCADE | |
| `role` | String(16) | user / system / agent / engine |
| `content` | Text | |
| `metadata_json` | JSON | |
| `created_at` | DateTime(tz) | |

索引：`ix_conversation_messages_session_id_created_at`

#### conversation_events

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | String(36) PK | UUID |
| `session_id` | String(36) FK → sessions.id ON DELETE CASCADE | |
| `type` | String(32) | 事件类型 |
| `payload_json` | JSON | 审计数据 |
| `created_at` | DateTime(tz) | |

索引：`ix_conversation_events_session_id_created_at`

### Repository contract

```python
ConversationRepository(session: Session)
  create_session(initial_status="idle", current_mode=None, metadata=None)
  get_session(session_id) -> ConversationSession | None
  update_session_status(session_id, status, previous_status=UNSET, current_mode=UNSET, metadata_patch=None)
  append_message(session_id, role, content, metadata=None)
  append_event(session_id, type, payload=None)
  list_messages(session_id, limit=100, cursor=None)
  list_events(session_id, limit=100, cursor=None)
  get_transcript(session_id) -> list[ConversationMessage]
```

- `previous_status` 使用 sentinel `_UNSET` 区分"不传"与"传 None 以清除"。
- `get_transcript` 仅返回 messages，events 通过 `list_events` 单独读取。
- `create_session` / `update_session_status` 验证 `ConversationStatus`。
- `append_message` 验证 `ConversationRole`，并在写入前检查 session 存在。
- `append_event` 验证 `ConversationEventType`，并在写入前检查 session 存在。
- `list_messages` / `list_events` 暂不实现 cursor pagination；传入 cursor 时显式
  抛 `ValueError("cursor pagination is not implemented yet")`。

### 测试覆盖

32 个 repo 测试全部通过：

- create session defaults to `idle`
- create session stores metadata
- create session rejects invalid status
- get session by id / unknown returns None
- update session status
- update session `previous_status` for pause / resume
- update session metadata patch merges
- update session unknown id raises
- update session rejects invalid status
- append user / system / engine message
- append message accepts `ConversationRole`
- append message rejects invalid role
- append message unknown session raises `ValueError`
- list messages ordered by `created_at` + limit
- list messages with cursor raises
- get_transcript returns messages only (no events)
- append event
- append event accepts `ConversationEventType`
- append event rejects invalid type
- append event unknown session raises `ValueError`
- list events ordered by `created_at` + limit
- list events with cursor raises
- session delete cascades messages and events
- no user / account / tenant fields in models
- repo does not import replay / autonomous / LLM modules
- model collected in Base.metadata sanity

### Alembic head check

已运行：

```bash
cd apps/api && ../../.venv/bin/alembic -c alembic.ini heads
# a93d26f33594 (head)

cd apps/api && ../../.venv/bin/alembic -c alembic.ini history --verbose
# Rev: a93d26f33594 (head)
# Parent: 20260502_0001
# Path: .../a93d26f33594_add_conversation_tables.py
```

结论：`a93d26f33594_add_conversation_tables.py` 的 `down_revision =
"20260502_0001"` 与当前 migration 链匹配。

### 验证命令

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v
# 61 passed
cd apps/api && ../../.venv/bin/ruff check app/models/conversation.py app/repos/conversation_repo.py app/models/__init__.py tests/test_conversation_repo.py alembic/versions/a93d26f33594_add_conversation_tables.py
# All checks passed!
cd apps/api && ../../.venv/bin/alembic -c alembic.ini heads
# a93d26f33594 (head)
git diff --check
# clean
```

## 设计决策确认

| 问题 | 决策 |
|---|---|
| `previous_status` 是核心列还是放入 metadata_json | **核心列** — 直接放在 `conversation_sessions` 上，便于 pause/resume 查询。 |
| transcript 是否只返回 messages | **只返回 messages** — `get_transcript` 仅返回 messages；events 通过 `list_events` 单独读取，避免审计事件混入用户 transcript。 |
| session delete 是否 cascade messages/events | **是** — `relationship` 配置 `cascade="all, delete-orphan"`，FK 也带 `ON DELETE CASCADE`。 |
| `metadata_json` / `payload_json` 是否需要 schema version | **第一版不需要** — 保持简单，后续如有需要可在 JSON 中嵌入 `v` 字段。 |
| `list_messages` / `list_events` 是否需要 cursor | **第一版 limit-only** — cursor 参数保留在接口中，暂不实现分页逻辑。 |
| 是否需要 conversation cleanup helper for tests | **不需要单独 helper** — cascade delete + `reset_database` fixture 已满足测试清理需求。 |

## 边界遵守

本轮未触及：

- API endpoint
- CLI
- orchestrator dispatcher
- replay API
- Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）
- task-to-path planning
- slot binding
- recovery / abort dialogue
- teaching mode
- artifact lifecycle
- risk gate
- multi-page workflow
- autonomous run
- LLM provider
- E2E
- user / account / tenant 字段
