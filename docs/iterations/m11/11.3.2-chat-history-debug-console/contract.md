# 契约（Contract）

状态：implementation complete（implementation review passed, UI smoke pending）

## 概念 / 边界契约

### Conversation History

`Conversation History` 指基于现有 `conversation_sessions`、`conversation_messages`、
`conversation_events` 和 `session.metadata_json` 构造的只读历史视图。

它不是新的执行入口，不改变 conversation runtime，不产生 internal Agent verdict。

### Chat History Debug Console

`Chat History Debug Console` 指 Console 中面向操作员 / 开发者的会话历史页面：

- `/conversation/history` - session list。
- `/conversation/history/:session_id` - session detail。

这个页面是 debug / observability surface。它可以读取和展示已持久化 messages / events /
metadata / replay summaries，但不得通过内部 service 绕过 product runtime。

### Aggregate History Payload

`Aggregate History Payload` 是给 Console、Codex、Kimi Code 和 CLI debug 使用的聚合 read model。
它一次性返回 session、messages、events、learned_actions、learning_runs、replay_summaries 和 raw JSON。

外部 AI 调试员可以读取 payload、复制 session id、通过已有 `wagent conversation send` 或
`wagent chat --resume` 继续会话。外部 AI 调试员不能把自己读到的 payload 改写成内部 Agent 结论。

### Resume Chat Session

`wagent chat --resume <session_id>` 表示继续一个已有 `current_mode=interactive_chat` session。

- `--resume` 不创建新 session。
- `--resume` 不把非 chat session 强行改成 `interactive_chat`。
- `--resume` 使用该 session 已有 metadata，例如 `learned_actions` 和 `browser_visibility`。
- 如果 session 不存在或不是 `interactive_chat`，CLI 必须失败并给出明确错误。

## 状态 / 结果契约

本轮不新增 ConversationStatus。

History list 和 detail 展示现有 session status：

- `idle`
- `task_intake`
- `awaiting_confirmation`
- `plan_confirmed`
- `executing`
- `execution_finished`
- `execution_failed`
- `replay_requested`
- `replay_running`
- `paused`
- `abort_requested`
- `takeover_requested`
- `completed`
- `failed`

Session list summary 不推导 pass / fail。它只展示当前 session status、message / event counts、最后消息摘要和 learned action 数量。

History detail 中的 replay summaries 必须来自已持久化 event payload 或 dispatch/replay summary 数据，不能由前端或 CLI 猜测业务成功。

## Schema / API 契约

### Session list API

新增：

```http
GET /conversation/sessions?current_mode=interactive_chat&status=task_intake&updated_from=2026-05-17T00:00:00Z&updated_to=2026-05-18T00:00:00Z&limit=50
```

Query params：

- `current_mode?: string` - 例如 `interactive_chat`。
- `status?: ConversationStatus` - 可选状态过滤。
- `updated_from?: datetime` - 可选更新时间下界。
- `updated_to?: datetime` - 可选更新时间上界。
- `limit?: int` - 默认 50，范围 `[1, 100]`。

Session list 默认按 `updated_at desc` 排序。`updated_from` / `updated_to` 均作用于
`conversation_sessions.updated_at`，不按 message created time 或 event created time 过滤。

Response envelope 保持 `ApiResponse[T]`。`data` shape：

```json
{
  "items": [
    {
      "id": "session-id",
      "status": "task_intake",
      "current_mode": "interactive_chat",
      "created_at": "2026-05-17T10:00:00Z",
      "updated_at": "2026-05-17T10:05:00Z",
      "message_count": 6,
      "event_count": 12,
      "last_user_message": "帮我登录",
      "last_agent_message": "登录完成。",
      "learned_action_count": 1,
      "learned_actions": [
        {
          "alias": "登录",
          "learned_path_id": "path-id",
          "target_url": "http://localhost:5175/login",
          "page_template": "/login",
          "scenario": "valid_credentials"
        }
      ]
    }
  ]
}
```

首版不要求 cursor pagination；如实现 `has_next` / `next_cursor`，必须保持缺省调用仍可直接读取 `items`。

### Aggregate history API

新增：

```http
GET /conversation/sessions/{session_id}/history
```

Response envelope 保持 `ApiResponse[T]`。`data` shape：

```json
{
  "session": {
    "id": "session-id",
    "status": "task_intake",
    "current_mode": "interactive_chat",
    "previous_status": "idle",
    "metadata": {},
    "created_at": "2026-05-17T10:00:00Z",
    "updated_at": "2026-05-17T10:05:00Z"
  },
  "messages": [],
  "events": [],
  "learned_actions": [],
  "learning_runs": [],
  "replay_summaries": [],
  "raw": {
    "session": {},
    "messages": [],
    "events": []
  }
}
```

`learned_actions` 来源：

- `session.metadata.learned_actions`。

`learning_runs` 来源：

- `chat_learning_completed` event payload 中的 `run_id`、`new_learned_path_id`、`target_url`、`alias` 等字段。

Normalized shape：

```json
{
  "source_event_id": "event-id",
  "source_event_type": "chat_learning_completed",
  "run_id": "run-id",
  "learned_path_id": "path-id",
  "status": "learned",
  "summary": "学习完成：我学会了登录页的登录操作。",
  "raw": {}
}
```

`replay_summaries` 来源：

- `chat_execution_completed` / `chat_execution_failed` event payload 中的 `replay`。
- `plan_execution_completed` / `plan_execution_failed` event payload 中已有 replay summary 字段。
- `replay_completed` / `replay_failed` event payload 中已有 explicit replay summary 字段。

Normalized shape：

```json
{
  "source_event_id": "event-id",
  "source_event_type": "chat_execution_completed",
  "learned_path_id": "path-id",
  "run_id": null,
  "status": "succeeded",
  "summary": "replay succeeded",
  "raw": {}
}
```

如果历史 event payload 缺少这些字段，返回空数组或缺失字段，不得补造。

### CLI contract

新增：

```bash
wagent conversation list --mode interactive_chat --limit 20 --pretty
wagent conversation history <session_id> --pretty
wagent chat --resume <session_id>
```

保留：

```bash
wagent conversation send <session_id> --content "帮我登录" --pretty
wagent conversation messages <session_id> --limit 100
wagent conversation events <session_id> --limit 100
wagent conversation transcript <session_id>
```

`wagent chat` 创建新 session 后必须输出：

```text
WAgent > 本次会话 ID：<session_id>。需要调试时可以在管理后台查看。
```

如果 11.3.1 的 `--headless` 已存在：

- `wagent chat --headless` 创建新 session 时继续写入 `browser_visibility=headless`。
- `wagent chat --resume <session_id>` 使用已有 session metadata。
- `wagent chat --resume <session_id> --headless` 首版必须拒绝并提示 `--headless` only applies when creating a new chat session，避免用户误以为 resume 会修改旧 session runtime policy。

### Console contract

新增路由：

```text
/conversation/history
/conversation/history/:session_id
```

列表页字段：

- 更新时间。
- session id，支持复制。
- mode。
- status。
- 最后一条用户消息。
- 最后一条 agent 回复。
- learned action 数量。
- event 数量。

详情页 tabs：

- Transcript。
- Events。
- Learned Actions。
- Replay / Learning Evidence。
- Raw JSON。

Raw JSON 必须展示 aggregate history payload，并支持复制。

## Evidence / Observation 契约

允许 evidence 来源：

- API unit / integration test 输出。
- CLI unit test 输出。
- Console component / router / API client test 输出。
- 手动 Console smoke 的页面 URL、操作步骤、截图或可复查观察结果。
- `git diff --check`。

本轮不要求 live autonomous run、`verify-scenario` 或 product-driven browser execution。

如果没有真实打开 Console 页面，不得声称 UI smoke 已完成。如果只运行单元测试，必须写成 Console UI smoke not run。

History UI 和 CLI 必须忠实显示 raw persisted data。不得把 raw event 改写成内部 Agent verdict，不得编造 pass / fail，不得省略 `unverified` 语义。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：仍属于 M11 L3 runtime loop 的 operator / developer observability，不新增 internal Agent role。
- Scope boundary 对齐：只增加 WebAgentFlow 自身 conversation 历史读面，不引入账号体系、托管用户数据、闭源产品壳或外部调度接口。
- Roadmap / milestone 对齐：作为 M11.3 interactive chat 的调试可观察性补齐，编号为 11.3.2。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本轮不改变 lifecycle、Agent role 或 milestone boundary。

## 兼容性契约

- 既有 `POST /conversation/sessions`、`GET /conversation/sessions/{session_id}`、messages、transcript、events、dispatch endpoint 保持不变。
- 既有 `wagent conversation start/status/send/messages/transcript/events` 保持不变。
- 既有 `wagent chat` 创建新 session 的行为保持不变，只增加 session id 输出。
- 旧 session 缺少 `learned_actions` 时，summary / history 返回空数组。
- 旧 event 缺少 replay payload 时，`replay_summaries` 返回空数组或只返回可解析部分。
- API response envelope 不变。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：新增 read endpoints，但不改变既有 endpoint response。
- Database schema：不新增 migration，优先复用现有 conversation tables 和 metadata JSON。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不做复杂搜索或全文检索。
- 不做多用户权限、账号体系、云端用户数据、脱敏策略或长期归档。
- 不做 LLM 历史总结。
- 不做失败恢复、重试、中断、接管或 M12 行为。
- 不做 stable external M16 CLI / Skill / Tool interface。
- 不调用 autonomous run。

## 未决问题

- 是否在 session list 首版加入 cursor pagination：默认不做；如果列表性能或 UI 需要，再用后续小包补。
