# 审核与反思

## 规划初始化

- 本目录用于 11.0.4 Runtime CLI Shell。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 前置 11.0.1 Conversation Domain Contract 已完成。
- 前置 11.0.2 Conversation Session Store 已完成并通过 hardening。
- 前置 11.0.3 Conversation API 已实现并通过验证。
- 本包将规划 `wagent conversation` CLI-first runtime conversation 入口。

## 已决策

- 11.0.4 首版只规划非交互命令，不把 interactive loop / REPL 列为验收项。
- `send` 命令首版只允许追加 `user` message。
- CLI 调用 11.0.3 Conversation API，不直接操作 DB。
- CLI 不调用 replay API，不实现 `/replay` command side effect。
- CLI 不调用 autonomous run，不依赖 LLM provider。
- 当前 `wagent verify` / `verify-scenario` 仍是 development verification skill backend，
  不进入 runtime conversation CLI。

## 待确认问题

- `--pretty` 是否作为所有 conversation 子命令的通用参数实现。
- Conversation CLI 默认 timeout 应该是短请求 timeout，还是复用 `wagent verify`
  的长 timeout。
- `messages` 和 `events` 是否第一版暴露 `--limit`。
- `send` 是否需要支持 `--metadata` JSON 参数，还是第一版固定 `{}`。
- 是否需要 `wagent conversation help` 的额外文档输出，还是依赖 argparse。
