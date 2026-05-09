# 审核与反思

## 规划初始化

- 本目录用于 11.0.3 Conversation API。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.0.1 Conversation Domain Contract 已完成。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 本包将把 session / message / event store 暴露为最小 HTTP API。

## 待确认问题

- 是否需要 session status update endpoint，还是留给后续 orchestrator /
  dispatcher 包引入。
- list messages / events 是否长期只支持 `limit`，还是后续需要 cursor query。
- transcript 是否长期只返回 messages，还是未来增加 messages + events 混合视图。
- router tag / name 是否使用 `conversation`，还是对外命名为 runtime conversation。
- API tests 是否需要覆盖 OpenAPI schema。

## 已决策

- 第一版 API 强制创建 `status=idle` 的 session。
- `ConversationSessionCreateRequest` 不接受 `initial_status`；repo / internal /
  test 可以继续保留 `initial_status` 能力。
- public message append API 只允许 `user` / `system` / `engine` role。
- `agent` role 不允许 public append，保留给 future internal orchestrator /
  Agent integration。
- `GET messages`、`GET events`、`GET transcript` 对 missing session 必须返回
  HTTP 404，不能返回空列表。
