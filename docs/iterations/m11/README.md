# M11 · Runtime Loop Foundation

M11 的目标是让 WebAgentFlow 从“路径资产可以持久化、查看、显式 replay”
进入“用户可以通过运行时入口和 WebAgentFlow 沟通”的阶段。M10 已经完成
LearnedPath persistence、catalog、replay execution + drift detection；
M11 在这个确定性底座上建立 runtime loop。

M11 不是重新做 L1 autonomous learning，也不允许 LLM 逐步控制浏览器。
用户始终和 WebAgentFlow 这个应用沟通，内部 Agent 边界由
Conversation Orchestrator / Dispatcher 管理。

M11.0 先做 Runtime Conversation Shell & Agent Orchestration。它建立
CLI-first 的最小运行时沟通入口、session state、消息 / 事件边界和
orchestrator 骨架。M11.1 才进入 Task-to-Path Planning & Execution MVP。

M11.0 也是 M11.1 Task-to-Path、M12 Recovery / Abort、M13 Guided Teaching
的共同入口层。当前最小可行 runtime surface 是 CLI-first：先跑通完整功能
闭环，再扩展更丰富的操作员界面或稳定对外接口。

## 迭代索引

- [m11-plan](./m11-plan.md) —— M11 全量计划与 M11.0 / M11.1 执行包拆分。状态：持续更新。
- [11.0-runtime-conversation-shell-orchestration](./11.0-runtime-conversation-shell-orchestration/) —— M11.0 总纲：Runtime Conversation Shell 与 Conversation Orchestrator 规划。状态：完成。
- [11.0.1-conversation-domain-contract](./11.0.1-conversation-domain-contract/) —— conversation session / message / event / command / state contract。状态：完成。
- [11.0.2-conversation-session-store](./11.0.2-conversation-session-store/) —— session / message / event persistence。状态：完成。
- [11.0.3-conversation-api](./11.0.3-conversation-api/) —— conversation API endpoints。状态：完成。
- [11.0.4-runtime-cli-shell](./11.0.4-runtime-cli-shell/) —— CLI-first runtime conversation shell。状态：完成。
- [11.0.5-orchestrator-dispatcher](./11.0.5-orchestrator-dispatcher/) —— Orchestrator / Dispatcher state routing。状态：完成。
- [11.0.6-explicit-replay-command-hook](./11.0.6-explicit-replay-command-hook/) —— 显式 `/replay <learned_path_id> <url>` hook。状态：完成。
- [11.0.7-conversation-tests-and-evidence](./11.0.7-conversation-tests-and-evidence/) —— conversation 测试域与证据。状态：完成。
- [11.1-task-to-path-planning-execution](./11.1-task-to-path-planning-execution/) —— M11.1 总纲：Task-to-Path Planning & Execution MVP。状态：总纲初始化中。
- [11.1.1-task-planning-domain-contract](./11.1.1-task-planning-domain-contract/) —— task / candidate / route / binding / verification domain contract。状态：完成（17 schema，33 passed）。
- [11.1.2-learned-path-retrieval-ranking](./11.1.2-learned-path-retrieval-ranking/) —— LearnedPath retrieval and deterministic ranking。状态：完成（38 retrieval tests，71 combined passed）。
- [11.1.3-task-path-planner-mvp](./11.1.3-task-path-planner-mvp/) —— Task Path Planner MVP。状态：完成（21 planner tests passed）。
- [11.1.4-task-planning-dispatch-preview](./11.1.4-task-planning-dispatch-preview/) —— Task Planning Dispatch Preview。状态：完成（64 targeted tests passed，962 full API tests passed）。
- [11.1.5-plan-confirmation-consent-gate](./11.1.5-plan-confirmation-consent-gate/) —— Plan Confirmation and Consent Gate。状态：完成（confirmation gate + slash decision commands，review passed）。
- Slot Binding contract and deterministic binding MVP —— 状态：future，尚未分配执行包编号。
- [11.1.6-execution-via-replay](./11.1.6-execution-via-replay/) —— Execution via Replay。状态：完成（execution service + orchestrator/API coverage，full API tests passed，ruff clean）。
- [11.1.7-result-verification-task-result-reporter](./11.1.7-result-verification-task-result-reporter/) —— Result Verification and Task Result Reporter。状态：documentation initialized。
- Task-to-path tests and evidence —— 状态：future，尚未分配执行包编号。

`11.0-runtime-conversation-shell-orchestration/` 是 M11.0 总纲目录，不是
一次性施工包。具体实现拆到 `11.0.x-*` 执行包；每个执行包都必须独立维护
`intent.md`、`plan.md`、`review.md`，并且每次只施工当前包。
