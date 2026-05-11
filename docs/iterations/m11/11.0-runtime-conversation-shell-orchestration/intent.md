# M11.0 Runtime Conversation Shell & Agent Orchestration

## 目标

建立 CLI-first 的运行时沟通入口和 Conversation Orchestrator 骨架，让用户
始终和 WebAgentFlow 沟通，并为 M11.1 / M12 / M13 的 Agent 路由和执行边界
打底。

## 动机

M10 已经完成 LearnedPath 路径资产底座：persistence、catalog、replay、
drift detection，以及 replay E2E / Codex exploratory evidence。系统现在
能消费已有路径资产并解释漂移，但还没有统一的 runtime conversation
surface。

不能直接跳到复杂 task planner。用户和系统之间需要先有统一入口、会话状态、
消息记录、基础命令和 orchestrator 边界，否则后续 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）
会被暴露成用户直接感知的内部实现。用户认知里只有 WebAgentFlow，而不是
一组独立子 Agent。

M11.0 先提供会话状态、消息入口、事件记录、基础命令和 Conversation
Orchestrator / Dispatcher 边界。它是 M11.1 Task-to-Path、M12 Recovery /
Abort、M13 Guided Teaching 的共同入口层。

CLI-first 是最小可行入口。后续 Web UI 或 M16 external CLI 都不能替代
这个 runtime loop 基础：M11.0 的重点是运行时产品入口和 session controller，
不是对外工具分发。

## 边界（本轮不做）

- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H） 的具体实现。
- 不做自然语言 task-to-path planning。
- 不做 slot binding。
- 不做 L3 task execution MVP。
- 不做 task result verification。
- 不做 recovery / abort dialogue 的完整 Agent。
- 不做 teaching mode。
- 不做 artifact lifecycle。
- 不做 action risk / consent gate。
- 不做 multi-page workflow。
- 不做 M16 external interfaces。
- 不引入路线图外的产品外壳、身份管理、托管数据或外部通道规划。
- 不调用 autonomous run，不做隐藏重新学习。
- 不让 LLM 逐步控制浏览器。
- 不修改 M10 replay contract。

## 成功标准

- 明确 runtime conversation CLI 与当前 `wagent verify` / 未来 M16 external
  CLI 的区别。
- 明确 Conversation Orchestrator / Dispatcher 的 session state 模型。
- 明确 message / event / session 的最小数据结构。
- 明确基础命令或消息流。
- 明确如何以显式 `learned_path_id + url` 调用 M10 replay 能力作为最小
  smoke hook。
- 明确哪些只是 placeholder，哪些必须在 M11.0 实现。
- 明确 M11.0 完成后 M11.1 可以在此基础上接 Task Path Planner / 任务路径规划器和 Task Result Reporter / 任务结果汇报器（legacy: Agent D/E）。
