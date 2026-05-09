# 11.0.2 Conversation Session Store

## 目标

实现 M11.0 runtime conversation 的 session / message / event 持久化 store，为
后续 API、CLI、orchestrator 和审计证据提供稳定数据层。

## 动机

11.0.1 已经完成 domain contract，但目前只有纯 schema、parser 和 state
transition，没有持久化。M11.0 后续需要 API、CLI 和 orchestrator；这些都
需要能创建 session、追加 message、追加 event、读取 status 和 transcript。

如果没有 store，CLI 和 API 会各自临时保存状态，后续会话恢复、审计和测试
证据会变得混乱。

11.0.2 第一版推荐选择 DB-backed store，而不是 JSON / event log。理由：

- 仓库已有 PostgreSQL / SQLAlchemy / Alembic 基础。
- 便于 API 查询、CLI session lifecycle、audit trail 和 future E2E。
- 便于后续和 conversation history、recovery、teaching session audit 对齐。

这不是账号体系，不加入 user / account / tenant 字段。

## 边界（本轮不做）

- 不做 API endpoint。
- 不做 CLI。
- 不做 orchestrator dispatcher。
- 不调用 replay API。
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

## 成功标准

- 有 conversation session / message / event 的 ORM model 或等价持久化模型规划。
- 有 migration 规划。
- 有 repo contract 规划：
  - `create_session`
  - `get_session`
  - `update_session_status`
  - `append_message`
  - `append_event`
  - `list_messages`
  - `list_events`
- 有审计字段和 JSON metadata / payload 规划。
- 不加入 user / account / tenant 字段。
- 不改变 11.0.1 command parser 和 state transition contract。
- 有 repo tests 计划。
- 明确如何支持 `/resume` 的 `paused_from` 或 previous status 记录。
