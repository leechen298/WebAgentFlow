# 实施计划

## 触及的文件 / 模块

这是后续实现计划，不是本轮文档初始化要改的代码。

- `apps/api/app/schemas/conversation.py` —— 如有必要，补 API request /
  response schemas；不得改变 11.0.1 已定的核心 enum / command contract。
- `apps/api/app/routers/conversation.py` —— 新增 conversation router。
- `apps/api/app/routers/__init__.py` —— include conversation router。
- `apps/api/app/repos/conversation_repo.py` —— 只复用现有 repo；如确需调整，
  保持最小改动且不改变核心 contract。
- `apps/api/tests/test_conversation_api.py` —— 新增 API tests。
- `docs/iterations/m11/11.0.3-conversation-api/review.md` —— 实现完成后记录
  证据。

## API contract

第一版 endpoint：

```text
POST /conversation/sessions
GET /conversation/sessions/{session_id}
POST /conversation/sessions/{session_id}/messages
GET /conversation/sessions/{session_id}/messages
POST /conversation/sessions/{session_id}/events
GET /conversation/sessions/{session_id}/events
GET /conversation/sessions/{session_id}/transcript
```

本包不提供 session status mutation endpoint。读取 session 即可读取当前
status；状态变更由后续 orchestrator / dispatcher 包明确引入。

## Request / response schema planning

建议新增或复用以下 API schema：

```text
ConversationSessionCreateRequest
- current_mode optional
- metadata optional

Created sessions always start with status = idle.

ConversationSessionResponse
- id
- status
- current_mode
- previous_status
- metadata
- created_at
- updated_at

ConversationMessageCreateRequest
- role: user | system | engine
- content
- metadata optional

ConversationMessageResponse
- id
- session_id
- role
- content
- metadata
- created_at

ConversationEventCreateRequest
- type
- payload optional

ConversationEventResponse
- id
- session_id
- type
- payload
- created_at
```

`ConversationRepository.create_session(initial_status=...)` 仍然可以支持
`initial_status`；这是 store / internal / test 能力。11.0.3 public API
不接受 `initial_status` 字段，避免外部调用方绕过 runtime conversation
lifecycle 直接创建 `replay_running`、`paused`、`completed` 等状态。

`ConversationRole.AGENT` 已存在于 domain contract，但 11.0.3 public API 不接受
`agent` role。Agent messages 保留给未来 internal orchestrator / Agent
integration，避免外部调用方伪造内部 Agent transcript。

列表接口第一版返回简单 list：

```text
ApiResponse[list[ConversationMessageResponse]]
ApiResponse[list[ConversationEventResponse]]
```

`transcript` 第一版延续 11.0.2 决策，只返回 messages，不混入 events。

## Response policy

- 全部 endpoint 返回 `ApiResponse[...]`。
- missing session 返回 HTTP 404。
- invalid enum / body 使用 FastAPI / Pydantic 422。
- 第一版 list endpoints 只支持 `limit`，不暴露 cursor。
- `GET /messages`、`GET /events` 和 `GET /transcript` 必须先 resolve
  session；missing session 返回 HTTP 404，不返回空列表。
- `ConversationRepository` 的 `ValueError("session not found: ...")` 应映射为
  HTTP 404。
- 其他 repo validation error 可以映射为 HTTP 422，优先让 request schema 在
  入口处拦截 enum/body 错误。

## Router behavior

API 只做 store facade：

- 创建 session 调用 `ConversationRepository.create_session()`。
- 读取 session 调用 `ConversationRepository.get_session()`。
- 追加 message 调用 `ConversationRepository.append_message()`。
- 读取 messages 调用 `ConversationRepository.list_messages()`。
- 追加 event 调用 `ConversationRepository.append_event()`。
- 读取 events 调用 `ConversationRepository.list_events()`。
- 读取 transcript 调用 `ConversationRepository.get_transcript()`。

禁止：

- 不执行 replay。
- 不调用 replay API。
- 不调用 autonomous run。
- 不调用 LLM provider。
- 不做 task-to-path planning。
- 不暴露 internal Agent 作为用户直接沟通对象。
- 不把 replay result 包装成 `pass_gate` 或 Supervisor verdict。

## Test plan

后续实现阶段至少覆盖：

- `POST /conversation/sessions` creates session，固定 status 为 `idle`。
- `POST /conversation/sessions` request schema does not define `initial_status`；
  实现阶段不得把该字段暴露为 public API contract。
- `POST /conversation/sessions` accepts metadata。
- `GET /conversation/sessions/{session_id}` reads session。
- unknown session returns HTTP 404。
- `POST /conversation/sessions/{session_id}/messages` appends user message。
- message role supports user / system / engine。
- message role `agent` is rejected by public API。
- invalid message role returns HTTP 422。
- appending message to unknown session returns HTTP 404。
- `GET /conversation/sessions/{session_id}/messages` returns messages ordered by
  `created_at`。
- `GET /conversation/sessions/{session_id}/messages` unknown session returns HTTP
  404, not `[]`。
- `GET /conversation/sessions/{session_id}/transcript` returns messages only。
- `GET /conversation/sessions/{session_id}/transcript` unknown session returns
  HTTP 404, not `[]`。
- `POST /conversation/sessions/{session_id}/events` appends event。
- invalid event type returns HTTP 422。
- appending event to unknown session returns HTTP 404。
- `GET /conversation/sessions/{session_id}/events` returns events ordered by
  `created_at`。
- `GET /conversation/sessions/{session_id}/events` unknown session returns HTTP
  404, not `[]`。
- API implementation does not import replay / autonomous / LLM modules。
- API tests use existing `ApiResponse` envelope assertions。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v
cd apps/api && ../../.venv/bin/ruff check app/routers/conversation.py app/schemas/conversation.py tests/test_conversation_api.py
git diff --check
```

当前文档初始化阶段只需要运行：

```bash
git diff --check
```
