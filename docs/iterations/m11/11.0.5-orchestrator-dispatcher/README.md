# 11.0.5 · Orchestrator Dispatcher

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/scope-boundaries.md`
4. `docs/iterations/m11/m11-plan.md`
5. `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/intent.md`
6. `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/plan.md`
7. `docs/iterations/m11/11.0.1-conversation-domain-contract/review.md`
8. `docs/iterations/m11/11.0.2-conversation-session-store/review.md`
9. `docs/iterations/m11/11.0.3-conversation-api/review.md`
10. `docs/iterations/m11/11.0.4-runtime-cli-shell/review.md`
11. 本目录的 `intent.md`
12. 本目录的 `plan.md`

状态：**已完成**。`17 passed`，ruff clean。

## 当前关系

- 前置：11.0.1 domain contract、11.0.2 store、11.0.3 API、11.0.4 CLI。
- 本包：实现 Orchestrator / Dispatcher 的纯调度骨架。
- 后续：11.0.6 explicit replay command hook。
- 本包只做状态转移、消息记录、事件记录、用户响应提示，不做 replay side
  effect。

## 硬边界

- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不做 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不新增 CLI 命令。
- 不新增 HTTP endpoint。
- 不创建 M11.1 详情目录。

## 目标

为 M11.0 runtime conversation 建立 Conversation Orchestrator / Dispatcher
的最小纯调度骨架：接收用户消息、slash command 或 engine event，解析命令，
执行状态转移，记录 message / event，并返回 WebAgentFlow 视角的
user-facing response。

## 非目标

- 不接 replay execution。
- 不实现 `/replay` command side effect。
- 不实现 Agent routing。
- 不做自然语言 task planning。
- 不新增 API endpoint contract。
- 不新增 CLI 命令。
- 不做 E2E。

## 成功标准

- 有 Orchestrator / Dispatcher service contract。
- 能接收 `session_id + raw user input`。
- 能复用 11.0.1 parser 和 state transition。
- 能复用 11.0.2 repo 记录 message / event 并更新 session status。
- 能返回 user-facing response hint。
- `/replay` 只能 parse 和 transition 到 `replay_requested`，不能执行 replay。
- 不调用 replay / autonomous / LLM。
- 有单元测试计划。
