# 审核与反思

## 规划初始化

- 本目录用于 11.1.1 Task Planning Domain Contract。
- 当前状态：intent / plan 初始化，尚未实现代码。
- 本包是 M11.1 的第一个执行包，用于定义 task-to-path 领域 contract。

## 待确认问题

- `TaskIntent.normalized_goal` 是否由 Agent D 填写，还是 deterministic
  normalizer 先填。
- `RiskHint` 和 `ConsentRequirement` 是否合并为一个 schema。
- `TaskExecutionResult.status` 是否需要区分 replay failure 和 verification
  failure。
- AgentD / AgentE schema 是否在 11.1.1 定义完整，还是只定义 stub。
- artifact fields 是否只留占位，具体 lifecycle 后移到 M15。
