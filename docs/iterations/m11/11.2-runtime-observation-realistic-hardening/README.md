# 11.2 · 运行时观察与真实网页稳健性增强（Runtime Observation & Realistic Web Hardening）

状态：11.2.0 文档初始化完成

## 目标

M11.2 在已完成的 M11.1 task-to-path MVP 之后，补上运行时观察边界。M11.1
已经证明 WebAgentFlow 可以从用户任务输入走到 LearnedPath 检索、规划预览、
确认、replay 执行和基于证据的结果汇报。M11.2 继续回答的是：replay 执行
期间和执行之后，页面到底发生了什么。

M11.2 回答：

- 页面发生了什么变化？
- 预期变化是否等到了？
- 观察到了哪些结构化信号？
- 这些信号能否作为 result evidence？

M11.2 不回答：

- 失败之后怎么办？
- WebAgentFlow 是否应该 retry？
- 是否应该询问用户做 recovery 选择？
- 是否应该 interrupt、abort 或 replan？
- 是否应该创建或修复路径？

这些决策属于 v0.2 / M12。

## 与 M11.1 的关系

M11.1 是第一个可工作的 task-to-path loop：

```text
TaskInput -> LearnedPath retrieval / ranking -> Task Path Planner
-> planning preview -> confirmation -> replay execution
-> Task Result Reporter
```

M11.2 保持这条链路不变。11.2.0 不修改 Task Path Planner、replay execution、
confirmation 或 Task Result Reporter 行为。11.2.x 只定义后续包可以使用的
observation layer，用来增强 wait-for-change 行为和 result evidence。

## 与 M12 的关系

M11.2 是感知层。M12 是应急反应层。

M11.2 可以观察 modal 是否出现、按钮是否一直 disabled、列表是否刷新、toast
是否很快消失，或者 passive server push 是否改变页面。它应该把这些观察记录为
evidence。

M12 决定失败、不确定、用户中断、retry、abort、takeover 或 recovery dialogue
应该怎么处理。M11.2 不应把这些决策夹带进 observation 文档或实现计划。

## 核心观察概念

### Post-action Observation

Post-action Observation 指用户动作或 replay 动作之后短时间内发生的页面变化。

示例：

- 点击 Submit -> 等 loading 消失。
- 点击 Submit -> 等 toast 出现。
- 点击行操作 -> 等 modal 打开。
- 输入搜索词 -> 等结果列表刷新。
- 填完必填字段 -> 等按钮变为 enabled。
- 提交表单 -> 等 URL、title、text、element 或 result state 变化。

它存在的原因是：WebAgentFlow 不能在 click 完成后立刻判断页面已经完成响应。
click 结束不等于页面反应结束。

### Passive Runtime Observation

Passive Runtime Observation 指不是由当前用户动作直接触发的页面变化。

示例：

- WebSocket 推送新消息。
- SSE 更新任务状态。
- polling 刷新列表。
- 后台任务完成后页面自己更新。
- 客服消息在没有新点击的情况下出现。
- 订单状态被服务端更新，SPA 在当前页面内刷新。

它存在的原因是：真实页面在 replay 运行时仍可能自己变化。WebAgentFlow 需要
记录这种变化，并在后续判断它是否影响 execution 或 result reporting。

## 11.2.0 范围

11.2.0 只初始化文档范围和 realistic runtime case catalog。

本轮创建：

- M11.2 总览文档。
- intent 文档。
- plan 文档。
- review 占位文档。
- realistic web runtime scenario catalog。

本轮不创建代码、测试、fixture、schema、API contract、wait helper 或 result
reporter integration。

## 后续 11.2.x 拆包

- 11.2.0 · 运行时观察范围与真实场景目录（Runtime Observation Scope & Realistic Case Catalog）。
- 11.2.1 · [观察信号契约（Observation Signal Contract）](../11.2.1-observation-signal-contract/)。
- 11.2.2 · [等待变化 MVP（Wait-for-change MVP）](../11.2.2-wait-for-change-mvp/)。
- 11.2.3 · replay 与观察集成（Replay Integration with Observation）。
- 11.2.4 · 真实场景 fixture 页面（Realistic Fixture Pages）。
- 11.2.5 · 观察证据接入 Task Result Reporter（Observation Evidence into Task Result Reporter）。
- 11.2.6 · Codex 真实网页 QA（Codex Realistic Web QA）。
- 11.2.7 · 运行时观察测试与证据（Runtime Observation Tests and Evidence）。

11.2.1 的核心 contract 文档是
[`contract.md`](../11.2.1-observation-signal-contract/contract.md)。它只定义
文档级 signal contract，不代表 runtime observation、wait-for-change 或 reporter
integration 已实现。

11.2.2 的核心契约文档是
[`contract.md`](../11.2.2-wait-for-change-mvp/contract.md)。它只定义文档级
Wait Result 和 Wait Strategy，不代表 wait-for-change、page-load waiting、Agent
判断或 reporter integration 已实现。

## 硬边界

- 11.2.0 不修改 runtime code。
- 11.2.0 不修改 test code。
- 11.2.0 不运行 E2E。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不处理 recovery、retry、abort 或 interruption。
- 不做 teaching mode。
- 不触发 autonomous run。
- 不引入 LLM provider 依赖。
- 不做 raw HTML planner。
- 不创建 M12 目录。
- 不创建 v0.2 分支。
