# 审核与反思

## 规划初始化

- 本目录用于 11.0.1 Conversation Domain Contract。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 本包是 M11.0 的第一个可执行子包，用于先稳定 conversation 领域 contract。

## 待确认问题

- `ConversationStatus` 是否需要区分 `task_intake` 和 `free_text_received`。
- `/cancel` 与 `/abort` 的语义是否需要区分。
- `/takeover` 在 M11.0 是 placeholder，还是需要明确 transition。
- replay command 的 URL 是否只做字符串格式检查，还是需要 URL parse。
- 是否需要 `error` / `unknown_command` command kind。
