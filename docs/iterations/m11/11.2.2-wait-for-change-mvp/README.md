# 11.2.2 · 等待变化 MVP（Wait-for-change MVP）

状态：文档生成完成，能力未实现

## 目标

11.2.2 定义 Wait-for-change MVP 的文档级设计。它回答：replay action 执行后，
WebAgentFlow 应该如何短窗口等待页面变化，并把等待过程记录成后续 replay
evidence / reporter evidence 可以消费的结构化结果。

本包只定义设计，不实现 runtime observation、wait-for-change 或 page-load
waiting。

## 背景

11.2.0 已经完成 M11.2 scope 和 realistic runtime case catalog。11.2.1 已经定义
Observation Signal Contract，用来描述“观察到了什么”。

11.2.2 在此基础上定义 Wait Result 和 Wait Strategy，用来描述“等待过程如何结束”。

## Wait-for-change MVP 是什么

Wait-for-change MVP 是 replay action 执行后的短窗口观察机制，用于等待并记录页面
是否出现可观察变化。

它用于回答：

- 当前 action 后是否出现可观察变化？
- 出现了哪些 observation signals？
- 等待是命中变化、超时、跳过，还是明确不需要？
- 这些结果能否作为后续 replay evidence / reporter evidence 的输入？

它不是：

- retry policy。
- recovery plan。
- abort decision。
- user takeover。
- 最终 result report。
- 业务成功判断。
- 完整 passive runtime observer。
- WebSocket / SSE 专用监听器。

## MVP 范围

11.2.2 MVP 优先覆盖 `post_action` wait，也就是 replay action 后短窗口等待页面变化。

`passive_runtime` 变化保留在 11.2.1 contract 和后续设计中，不作为 11.2.2 MVP 的
连续后台观察目标。

## 核心设计文档

本包的核心设计在 [`design.md`](./design.md)。

`design.md` 定义：

- Wait-for-change MVP。
- MVP signal coverage。
- Wait Result。
- Wait Strategy。
- Wait Result 与 Observation Signal 的关系。
- Agent / Reporter Boundary。
- conservative reporting 边界。
- 与 realistic runtime case catalog 的对齐关系。

## 后续实现计划

- [Implementation Plan](./implementation-plan.md)：后续代码实现计划，当前能力尚未实现。

## Page Understanding Agent 边界

11.2.2 不调用 Page Understanding Agent。

Page Understanding Agent 属于 L1 / M14 的页面学习语义理解角色；11.2.2 只处理
replay action 后短窗口 observation signals 和 wait results。

如果后续需要基于完整 replay evidence 做解释，应由 11.2.5 的 evidence-aware
Task Result Reporter 承接，而不是把 Page Understanding Agent 放进 wait loop。

## 硬边界

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 public API。
- 不修改 database schema。
- 不创建 Python / TypeScript schema 文件。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不实现 runtime observation。
- 不实现 wait-for-change。
- 不实现 page-load waiting。
- 不实现 mutation observer。
- 不实现 network observer。
- 不实现 WebSocket / SSE / polling observer。
- 不使用 Agent 判断业务成功。
- 不引入每一步 wait 后的 Agent 业务判断。
- 不实现 evidence-aware Task Result Reporter。
- 不实现 Page Understanding Agent。
- 不实现 Page Context Bridge。
- 不做 recovery / retry / abort / interruption / user takeover。
- 不读取或保存 raw HTML。
- 不创建 M12 / 12.x 目录。
- 不创建 M14 / 14.x 目录。
- 不创建 11.3 目录。
- 不创建 v0.2 分支。
