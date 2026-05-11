# 审核与反思

## 规划初始化

- 本目录用于 11.0.3 Conversation API。
- 当前状态：已实现并通过验证。
- 前置 11.0.1 Conversation Domain Contract 已完成。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 本包将把 session / message / event store 暴露为最小 HTTP API。

## 实现证据

### 新增文件

- `apps/api/app/routers/conversation.py` — conversation HTTP API router。
- `apps/api/tests/test_conversation_api.py` — 23 个 API 测试全部通过。

### 修改文件

- `apps/api/app/schemas/conversation.py` — 新增 API request/response schema：
  - `ConversationSessionCreateRequest`
  - `ConversationSessionResponse`
  - `PublicConversationMessageRole`
  - `ConversationMessageCreateRequest`
  - `ConversationMessageResponse`
  - `ConversationEventCreateRequest`
  - `ConversationEventResponse`
- `apps/api/app/routers/__init__.py` — include `conversation_router`。

### Endpoint 列表

```text
POST   /conversation/sessions
GET    /conversation/sessions/{session_id}
POST   /conversation/sessions/{session_id}/messages
GET    /conversation/sessions/{session_id}/messages
POST   /conversation/sessions/{session_id}/events
GET    /conversation/sessions/{session_id}/events
GET    /conversation/sessions/{session_id}/transcript
```

### 关键策略决策

| 问题 | 决策 |
|---|---|
| Session create 是否 idle-only | **是** — `POST /conversation/sessions` 不接受 `initial_status`，一律创建 `status=idle` 的 session。Request schema 使用 `ConfigDict(extra="forbid")`，传入 `initial_status` 返回 HTTP 422。 |
| Public message role 策略 | **只接受 user / system / engine** — `PublicConversationMessageRole = Literal["user", "system", "engine"]`，`agent` role 在 Pydantic 层直接返回 HTTP 422，不进入 repo。 |
| Missing session 的 read/list 行为 | **HTTP 404** — `GET /messages`、`GET /events`、`GET /transcript` 均先 resolve session，missing session 返回 404，不返回空列表。 |
| Response envelope | 全部 endpoint 返回 `ApiResponse[...]`。 |
| List endpoints 分页 | 第一版只支持 `limit` query param（1–1000），不支持 cursor。 |
| Transcript 内容 | 第一版只返回 messages，不混入 events。 |

### 测试覆盖

23 个 API 测试全部通过：

- `POST /conversation/sessions` creates session with `status=idle`
- `POST /conversation/sessions` accepts metadata
- `POST /conversation/sessions` rejects `initial_status` (HTTP 422)
- `GET /conversation/sessions/{id}` reads session
- Unknown session returns HTTP 404
- `POST .../messages` appends user / system / engine message
- `POST .../messages` rejects `agent` role (HTTP 422)
- `POST .../messages` rejects invalid role (HTTP 422)
- `POST .../messages` unknown session returns HTTP 404
- `GET .../messages` returns ordered messages
- `GET .../messages` unknown session returns 404, not `[]`
- `GET .../transcript` returns messages only (no events)
- `GET .../transcript` unknown session returns 404, not `[]`
- `POST .../events` appends event
- `POST .../events` invalid type returns HTTP 422
- `POST .../events` unknown session returns HTTP 404
- `GET .../events` returns ordered events
- `GET .../events` unknown session returns 404, not `[]`
- API response uses `ApiResponse` envelope
- Response does not expose user/account/tenant fields
- Router does not import replay / autonomous / LLM modules

### 验证命令

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v
# 84 passed
cd apps/api && ../../.venv/bin/ruff check app/routers/conversation.py app/schemas/conversation.py app/routers/__init__.py tests/test_conversation_api.py
# clean
git diff --check
# clean
```

## 边界遵守

本轮未触及：

- CLI
- orchestrator dispatcher
- replay API / `/replay` command side effect
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
- 11.0.4 或 M11.1 详情目录

## Follow-up

- 11.0.4 runtime CLI shell 应调用本 API，而不是直接操作 DB。
- 后续 orchestrator / dispatcher 包负责 session status mutation 和 replay side effect。
