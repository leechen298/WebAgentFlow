# 审核与反思

## 规划初始化

- 本目录用于 M11.1 Task-to-Path Planning & Execution MVP。
- 当前状态：总纲初始化，尚未实现代码。
- 前置 M11.0 runtime loop 已完成到 11.0.7。
- 本阶段将开始 L3 Actual Work MVP。

## 待确认问题

- Task Path Planner / 任务路径规划器（legacy: Agent D） 是否在 11.1.4 才开始接 LLM，前置包是否全部保持 deterministic。
- 11.1.1 domain contract 是否应该定义 Task Path Planner / 任务路径规划器和 Task Result Reporter / 任务结果汇报器（legacy: Agent D/E） schema，还是只定义
  task / path / route / result schema。
- task result verification 是否作为 11.1.7，还是拆成更细。
- basic artifact capture 是否放入 11.1.7，还是推到 M15。
