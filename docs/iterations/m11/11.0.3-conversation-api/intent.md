# 11.0.3 Conversation API

## 目标

为 M11.0 runtime conversation 提供最小 HTTP API，让后续 CLI 和 operator
surface 能创建会话、读取会话、追加消息、读取状态、读取 transcript 和读取
events。

本包把 11.0.2 已完成的 DB-backed session / message / event store 暴露成
稳定的 WebAgentFlow API facade。后续 11.0.4 runtime CLI shell 应该调用
这个 API，而不是直接操作 DB。

## 动机

- 11.0.1 已经定义 conversation domain contract：status、role、event type、
  command parser 和 state transition 纯逻辑。
- 11.0.2 已经实现 DB-backed session / message / event store，并补了 enum
  validation、session existence check、cursor 行为显式报错和 Alembic head
  验证。
- 11.0.3 需要把 store 暴露成稳定 API contract，作为后续 CLI、operator
  surface 和 orchestrator dispatcher 的共同入口。
- 后续 11.0.4 runtime CLI shell 应调用 HTTP API；否则 CLI 和 API 会形成两套
  conversation lifecycle。
- API 必须保持 WebAgentFlow 视角：用户和 WebAgentFlow 沟通，不直接面对
  Agent D / E / F / G / H。

## 边界（本轮不做）

- 不做 CLI。
- 不做 orchestrator dispatcher。
- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不实现 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 artifact lifecycle。
- 不做 risk gate。
- 不做 multi-page workflow。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 E2E。
- 不创建 M11.1 详情目录。
- 不加入 user / account / tenant 字段。
- API request 不接受 `initial_status`；session creation 第一版一律从
  `idle` 开始。
- public API 不允许直接追加 `agent` role message；`agent` role 保留给未来
  internal orchestrator / Agent integration。

## 成功标准

- 有清晰的 conversation API endpoint contract。
- 能创建 `status=idle` 的 session，且 request body 不暴露 `initial_status`。
- 能读取 session。
- 能追加 user / system / engine message。
- 能追加 event。
- 能读取 messages / transcript。
- 能读取 events。
- 读取 session、messages、events、transcript 时，missing session 返回 HTTP
  404，不返回空列表。
- API response 使用现有 `ApiResponse` envelope。
- 有 API tests 计划，并在实现阶段补充 `tests/test_conversation_api.py`。
- API 不调用 autonomous run。
- API 不依赖 LLM provider。
- API 不改变 11.0.1 domain contract。
- API 不改变 11.0.2 repository contract。
- API 不加入 user / account / tenant 字段。
