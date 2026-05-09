# 审核与反思

## 规划初始化

- 本目录用于 11.0.2 Conversation Session Store。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.0.1 Conversation Domain Contract 已完成并通过测试。
- 本包将为 M11.0 后续 API、CLI、orchestrator 提供 session / message /
  event 数据层。

## 待确认问题

- `previous_status` 是核心列，还是放入 `metadata_json`。
- transcript 是否只返回 messages，还是 messages + events 混合视图。
- session delete 是否 cascade messages / events。
- `metadata_json` / `payload_json` 是否需要 schema version。
- `list_messages` / `list_events` 是否第一版需要 cursor，还是先 limit-only。
- 是否需要 conversation cleanup helper for tests。
