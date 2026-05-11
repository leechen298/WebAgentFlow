# 11.0.4 Runtime CLI Shell

## 目标

为 M11.0 runtime conversation 提供 CLI-first 的最小用户入口，让用户可以通过
CLI 创建 conversation session、发送 user message、查看 session status、查看
messages / transcript / events，并为后续 Orchestrator / Dispatcher 接入做准备。

## 动机

11.0.3 已经提供 Conversation API。M11.0 的产品入口是 runtime conversation
surface，CLI-first 是最小可行入口；本包负责把这个入口规划到现有 Python
`wagent` CLI workspace 中。

CLI 应调用 Conversation API，而不是直接操作 DB。当前 `wagent verify` 是
development verification skill backend，不是 runtime conversation CLI。M16
external CLI 是未来稳定对外工具接口，不属于本包。

本包只做 shell 和 API 调用规划，不做 orchestrator dispatcher，不做 task
planning，不触发 replay side effect。

## 边界（本轮不做）

- 不做 orchestrator dispatcher。
- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不实现 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 artifact lifecycle。
- 不做 risk gate。
- 不做 multi-page workflow。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 M16 external CLI stabilization。
- 不创建 M11.1 详情目录。
- 不加入 user / account / tenant 字段。

## 成功标准

- 明确 runtime CLI command shape。
- 明确 CLI 和 `wagent verify` 的区别。
- 明确 CLI 和 M16 external CLI 的区别。
- CLI 通过 HTTP 调用 11.0.3 Conversation API。
- 支持 create session。
- 支持 append user message。
- 支持 get session status。
- 支持 list messages / transcript / events。
- 支持 basic non-interactive commands。
- interactive loop 只作为 future follow-up，不列为 11.0.4 首版验收项。
- 有 CLI tests 计划。
- 不调用 autonomous run。
- 不依赖 LLM provider。
