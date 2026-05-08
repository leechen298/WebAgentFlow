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

- [11.0-runtime-conversation-shell-orchestration](./11.0-runtime-conversation-shell-orchestration/) —— Runtime Conversation Shell 与 Conversation Orchestrator 规划。状态：规划中。
- 11.1-task-to-path-planning-execution —— Task-to-Path Planning & Execution MVP。状态：future，尚未创建详情目录。
