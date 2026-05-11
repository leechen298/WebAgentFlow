# 11.0.5 Orchestrator Dispatcher

## 目标

为 M11.0 runtime conversation 建立 Conversation Orchestrator / Dispatcher 的
最小纯调度骨架：接收用户消息、slash command 或 engine event，解析命令，
执行状态转移，记录 message / event，并返回 WebAgentFlow 视角的
user-facing response，为 11.0.6 replay hook 和后续 Agent routing 打底。

## 动机

11.0.1 已经提供 command parser 和 state transition 纯函数。11.0.2 已经
提供 DB-backed session / message / event store。11.0.3 已经提供
Conversation API。11.0.4 已经提供非交互式 `wagent conversation` CLI。

当前 CLI 可以创建 session、发送 message、查看 transcript，但用户输入进入
系统后还没有统一的 orchestrator：没有统一的 command parse audit、state
transition audit、session status mutation 和 WebAgentFlow user-facing
response 生成点。

11.0.5 要先把“消息进入系统后发生什么”这件事固定下来。它必须先建立无
replay side effect、无 Agent side effect 的 dispatcher 骨架，再由 11.0.6
接入显式 replay hook。这样可以避免一上来把 orchestrator、replay、Task
Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、
Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、
Teaching Guide Agent / 教学引导器（legacy: Agents D-H）和 task planning
混在一起。

## 边界（本轮不做）

- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 Agent routing implementation。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 artifact lifecycle。
- 不做 risk gate。
- 不做 multi-page workflow。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不新增 CLI 命令。
- 不做 E2E。
- 不创建 M11.1 详情目录。
- 不加入 user / account / tenant 字段。

## 成功标准

- 有 Orchestrator / Dispatcher service contract。
- 能接收 `session_id + raw user input`。
- 能为 engine event 预留 service contract，但不执行 engine side effect。
- 能用 11.0.1 parser 解析 slash command / free text。
- 能用 11.0.1 state transition 计算 next state。
- 能通过 11.0.2 repo append user message。
- 能 append `command_parsed` / `state_changed` 等 event。
- 能 update session status。
- 能返回 user-facing response hint。
- 能处理 status / pause / resume / abort / takeover / cancel / free_text。
- `/replay` 只能 parse 和 transition 到 `replay_requested`，不能执行 replay。
- 不调用 replay / autonomous / LLM。
- 有单元测试。
