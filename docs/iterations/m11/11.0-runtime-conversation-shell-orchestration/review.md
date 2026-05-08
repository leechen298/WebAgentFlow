# 审核与反思

## 规划初始化

- 本目录用于 M11.0 Runtime Conversation Shell & Agent Orchestration。
- 当前状态：intent / plan 初始化，尚未实现代码。
- M10 已完成，M11.0 是下一步计划交付包。

## 待确认问题

- Conversation session 是否需要落库，还是先内存 / JSON event log。
- CLI 命令格式是否采用 slash commands，还是自然语言 + structured fallback。
- `/replay` 在 M11.0 里是直接命令，还是只作为 orchestrator smoke hook。
- M11.0 是否需要 API endpoint，还是 CLI 直接调用已有 API。
- conversation 测试域何时建立。
- pause / resume / abort 在 M11.0 是状态占位，还是需要最小可执行行为。
