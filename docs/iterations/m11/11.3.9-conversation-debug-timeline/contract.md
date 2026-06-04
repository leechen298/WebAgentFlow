# 契约（Contract）

状态：docs_generated_pending_design_review

## 概念 / 边界契约

### Conversation Debug Timeline

`Conversation Debug Timeline` 是从已有 conversation history 派生的只读调试 read model。

它用于解释一次 `wagent chat` / Conversation API 会话发生了什么：

- 用户输入了什么类型的信息；
- runtime 识别到什么意图或缺口；
- 代码侧路由到了哪个应用能力或等待状态；
- 是否生成了 action options / pending choice；
- 是否进入 learning / replay / recovery / cancel；
- WAgent 回复由代码、内部 Agent 或 hybrid path 产生；
- 可展开查看哪些脱敏 payload、message id、event id、trace id。

它不是新的日志存储，不是执行入口，不是 pass / fail 裁判，也不是 internal Agent verdict。

### Human-readable Step

Timeline item 必须先给出人能读懂的 `title` 和 `summary`，再提供可展开的技术细节。

示例：

```text
用户输入页面地址
识别到这是一个页面 URL，但还不知道要学习或执行哪个操作。
```

不得把 raw JSON 作为默认阅读顺序。

### Debug Detail Payload

每个 timeline item 可以携带脱敏 `details`。`details` 只能来自现有 public-safe payload：

- conversation message public content；
- `conversation_event_public_payload()` 输出；
- public LLM trace payload；
- response provenance；
- session public metadata。

不得暴露：

- `pending_choice_private_map`；
- raw provider secrets / credentials；
- 未脱敏用户敏感字段；
- target page DOM 原文大段 dump；
- internal private retry payload；
- 未经过现有 sanitizer 的 LLM raw response。

### Terminal Log Boundary

后端终端日志不是本轮主要调试入口。它只能承载低噪声运行健康和关联信息，例如：

- method / path / status / latency；
- session_id / message_id / trace_id；
- provider / model / request_id / latency；
- error kind / short summary。

不得把完整 LLM request / response、完整 conversation history、完整 event payload 或用户敏感输入打印到终端。

## 状态 / 结果契约

本轮不新增 ConversationStatus、replay status 或 pass_gate status。

Timeline item 使用独立显示状态，不参与 runtime state machine：

- `info` - 普通过程节点；
- `waiting` - 等待用户输入或选择；
- `running` - learning / replay / provider call 等进行中记录；
- `success` - 已完成的学习、执行或确认节点；
- `warning` - fallback、低置信、需要复核或不完整证据；
- `error` - runtime error、provider error、API error 或明确失败；
- `cancelled` - 用户或 runtime 取消。

这些状态只用于 Console 显示，不得被下游当成 product verification result。

## Schema / API 契约

### History response extension

扩展现有：

```http
GET /conversation/sessions/{session_id}/history
```

在 `ConversationHistoryResponse` 中新增向后兼容字段：

```json
{
  "debug_timeline": [
    {
      "id": "timeline-item-id",
      "kind": "user_message",
      "title": "用户输入页面地址",
      "summary": "识别到这是页面 URL，正在确认下一步。",
      "status": "waiting",
      "created_at": "2026-06-04T19:25:35Z",
      "source": "message",
      "message_id": "message-id",
      "event_id": null,
      "trace_id": null,
      "related_event_ids": [],
      "related_trace_ids": [],
      "details": {},
      "raw_ref": {
        "tab": "events",
        "id": "event-id"
      }
    }
  ]
}
```

字段语义：

- `id`: timeline item id，稳定于一次 response 内即可，不要求跨重算永久稳定。
- `kind`: 显示分类，如 `user_message`、`agent_response`、`entry_gate`、`intake`、
  `router_decision`、`pending_choice`、`action_options`、`learning`、`replay`、
  `recovery`、`cancel`、`llm_trace`、`error`。
- `title`: 简短人类标题。
- `summary`: 面向操作员 / 开发者的解释。
- `status`: 使用本文件定义的 display status。
- `created_at`: 来源 message / event / trace 的时间；没有时可为 `null` 并排在相关对象附近。
- `source`: `message` / `event` / `trace` / `derived`。
- `message_id` / `event_id` / `trace_id`: 主来源引用。
- `related_event_ids` / `related_trace_ids`: 展开或跳转辅助。
- `details`: 脱敏 payload 摘要，不放 private map。
- `raw_ref`: 指向 Raw / Events / Transcript tab 的 UI hint，可选。

### Backward compatibility

`debug_timeline` 必须有默认空数组。旧调用方忽略该字段仍可工作。

### CLI handoff text

`wagent chat` 创建新 session 后的调试提示可以增强为：

```text
WAgent > 本次会话 ID：<session_id>。调试详情：/conversation/history/<session_id>
```

如果 CLI 不知道 Console base URL，不得编造完整 URL；只输出相对 path 和 session id。

## Evidence / Observation 契约

允许作为 timeline evidence 的来源：

- `conversation_messages`；
- `conversation_events`；
- `ConversationHistoryService` 已暴露的 `llm_traces` / `entry_gate_traces`；
- `learning_runs` / `replay_summaries` read model；
- public session metadata。

不允许作为 timeline evidence 的来源：

- 新增直接调用 autonomous-run endpoint；
- 一次性脚本导入 internal services 伪造结果；
- Codex / AI 的主观推理；
- 未持久化、不可复查的终端观察；
- 未脱敏 provider raw payload。

Timeline 可以解释“为什么系统进入等待用户选择”，但不能把未执行的学习 / replay 说成已完成。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：本包属于 operator workflow / debug glass，不新增 internal Agent role，不让 LLM 进入 step-by-step browser execution loop。
- Scope boundary 对齐：本包只增强 read-only observability，不改变 learning / replay / recovery 行为。
- Roadmap / milestone 对齐：承接 M11.3 interactive chat productization 和 11.3.2 debug console 基础，作为 M11.3 post-closeout UX / observability follow-up。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- 不新增 DB migration。
- `GET /conversation/sessions/{session_id}/history` 只新增字段，不删除或重命名现有字段。
- Console raw / events / transcript tabs 保留。
- Existing CLI commands 保持可用。
- History service 遇到未知 event type 时仍返回通用 timeline item 或跳过，不得导致整个 history endpoint 失败。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：只做 backward-compatible response extension。
- Database schema：不变，无 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不实现全站日志平台。
- 不做权限 / 多租户审计。
- 不做 raw LLM payload 下载。
- 不做 autonomous run 或 verify-scenario 验收。
- 不用 Timeline 替代 `review.md` 或 eval artifact。

## 未决问题

- Console detail 是否需要默认切到 Timeline tab：建议 Yes；设计评审确认。
- CLI 是否需要读取环境变量输出完整 Console URL：建议本轮 No，只输出相对 path；设计评审确认。
