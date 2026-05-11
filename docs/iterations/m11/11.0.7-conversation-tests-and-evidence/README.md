# 11.0.7 · Conversation Tests and Evidence

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/testing/README.md`
3. `docs/testing/e2e.md`
4. `docs/testing/features/conversation.md`
5. `docs/iterations/m11/m11-plan.md`
6. `docs/iterations/m11/11.0.6-explicit-replay-command-hook/review.md`
7. 本目录的 `intent.md`
8. 本目录的 `plan.md`

状态：**已完成**。

## 当前关系

- 前置：11.0.6 Explicit Replay Command Hook 已完成。
- 本包：为 conversation runtime loop 建立 deterministic E2E 和证据报告。
- 后续：M11.1 Task-to-Path 仍是 future，不能从本包抢跑。

## 硬边界

- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 task-to-path planning。
- 不做 path selection。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不把 replay result 包装成 `pass_gate` 或 Supervisor verdict。

## 目标

验证 M11.0 runtime conversation 已能通过显式 `/replay <learned_path_id> <url>`
进入 M10 replay engine，并把 replay summary、transcript 和 events 作为可审计证据返回。

## 成功标准

- replay deterministic E2E 有 fresh evidence。
- conversation API / CLI / orchestrator / replay hook baseline 有 fresh evidence。
- conversation runtime E2E 覆盖 session -> dispatch -> replay -> transcript/events。
- 所有报告写入 `docs/testing/results/`。
