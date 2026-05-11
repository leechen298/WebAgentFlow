# 11.0.7 Conversation Tests and Evidence

## 目标

为 M11.0 conversation runtime loop 建立测试证据闭环：持续运行
conversation domain / repo / API / CLI / orchestrator / replay hook baseline，并新增
conversation runtime deterministic E2E smoke。

## 动机

11.0.6 已经把显式 `/replay <learned_path_id> <url>` 接入 Conversation
Orchestrator 和 M10 replay capability。进入 M11.1 前，需要先证明当前 runtime loop
不是只停留在 unit/API 层，而是能通过确定性 E2E 串起 session、dispatch、replay、
transcript 和 events。

## 边界（本轮不做）

- 不实现 M11.1 Task-to-Path。
- 不做 LearnedPath selection。
- 不做 slot binding。
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不把 verify-scenario live smoke 标成 deterministic E2E。

## 成功标准

- Replay E2E rerun 记录 fresh evidence 或真实 BLOCKED 原因。
- Conversation baseline 记录 API / CLI / orchestrator / replay hook 命令证据。
- Conversation runtime E2E 新增并通过。
- `pnpm run test:e2e` 包含 replay + conversation，且不调用 autonomous run。
- 测试报告写入 `docs/testing/results/`。
