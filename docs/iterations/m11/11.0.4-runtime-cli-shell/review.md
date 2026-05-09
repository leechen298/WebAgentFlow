# 审核与反思

## 规划初始化

- 本目录用于 11.0.4 Runtime CLI Shell。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.0.1 Conversation Domain Contract 已完成。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 前置 11.0.3 Conversation API 已实现并通过验证。
- 本包将规划 `wagent conversation` CLI-first runtime conversation 入口。

## 已决策

- 主命名使用 `wagent conversation`，不使用 `wagent chat` 作为首版主命名。
- 11.0.4 首版只规划非交互命令，不把 interactive loop / REPL 列为验收项。
- `send` 命令首版只允许追加 `user` message。
- `send` 首版不支持 `--metadata`，metadata 默认 `{}`。
- CLI 调用 11.0.3 Conversation API，不直接操作 DB。
- 第一版默认 JSON 输出，推荐支持通用 `--pretty`。
- API base URL 优先复用现有 CLI 配置；当前按 `wagent verify` 使用
  `WBAF_API_BASE` / `http://localhost:8001` / `--api-base`。
- conversation CLI 使用短请求 timeout，推荐默认 `30s`。
- `messages` / `events` 第一版支持 `--limit`，默认 `100`，不支持 cursor。
- CLI 不调用 replay API，不实现 `/replay` command side effect。
- CLI 不调用 autonomous run，不依赖 LLM provider。
- 当前 `wagent verify` / `verify-scenario` 仍是 development verification skill backend，
  不进入 runtime conversation CLI。

## 待确认问题

- 是否需要 `wagent conversation help` 的额外文档输出，还是依赖 argparse。
- 未来是否引入 interactive REPL。
- 未来是否允许 internal / debug role 写入 `system` 或 `engine` message。
