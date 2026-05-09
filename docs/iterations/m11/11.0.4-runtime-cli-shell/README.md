# 11.0.4 · Runtime CLI Shell

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/m11/m11-plan.md`
4. `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/intent.md`
5. `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/plan.md`
6. `docs/iterations/m11/11.0.3-conversation-api/review.md`
7. 本目录的 `intent.md`
8. 本目录的 `plan.md`

状态：**当前规划中**。

## 硬边界

- 不做 orchestrator dispatcher。
- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不做 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不创建 M11.1 详情目录。

## 当前关系

- 前置：11.0.1 domain contract、11.0.2 store、11.0.3 Conversation API。
- 本包：规划 runtime conversation CLI shell。
- 后续：11.0.5 Orchestrator Dispatcher。

## 目标

为 M11.0 runtime conversation 提供 CLI-first 的最小用户入口，让用户可以
通过 CLI 创建 conversation session、发送 user message、查看 session status、
查看 messages / transcript / events，并为后续 Orchestrator / Dispatcher 接入做准备。

## 非目标

- 不实现 interactive loop / REPL。
- 不直接操作 DB。
- 不调用 replay。
- 不做 task-to-path planning。
- 不实现任何 Agent 逻辑。
- 不稳定化 M16 external CLI。

## 成功标准

- 明确 runtime CLI command shape。
- 明确 CLI 和 `wagent verify` 的区别。
- 明确 CLI 和 M16 external CLI 的区别。
- CLI 通过 HTTP 调用 11.0.3 Conversation API。
- 支持 create session、send user message、get session status、
  list messages、view transcript、list events 的规划。
- 有 CLI tests 计划。
- 不调用 autonomous run。
- 不依赖 LLM provider。
