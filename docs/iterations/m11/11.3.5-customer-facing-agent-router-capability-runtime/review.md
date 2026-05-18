# Review

状态：proposed
docs_review：pending
implementation：not_started

## 当前发现

人工 `wagent chat` smoke 暴露出：

```text
用户只发 URL -> 系统误判为 execute
用户再说“学习” -> 系统没有结合上一轮 URL
```

初始 11.3.5 只把问题定义成 Chat Context Recovery UX。后续讨论确认这个范围太窄：
真正的问题是面客 Agent 路由、Orchestrator 裁决、Worker Agent 和 Capability Runtime
边界没有完整建模。

## 设计决策

- 接受：`Customer-Facing Agent Router != Conversation Orchestrator`。
- 接受：Router 只输出路由建议，不直接调用 capability。
- 接受：Orchestrator 是代码侧裁决者，负责 scope、risk、state、事件和真正调用。
- 接受：Capability Registry 是应用能力目录，不是 Agent 列表。
- 接受：Learning Agent 和 Web Operation Agent 是工作 Agent，可以通过 Orchestrator /
  Capability Runtime 请求 capability。
- 接受：Page Understanding Agent 可以提前作为页面语义理解层使用，但不得输出 selector
  或 browser steps。
- 接受：M11.3.5 不实现 active browser tab。
- 接受：Risk policy 必须进入本轮，但只做轻量分类和 high-risk 自动执行阻断。
- 接受：Thinking policy 必须写死，Router / Page Understanding 默认低延迟结构化输出。

## 现有基础设施评估

项目已经具备支撑 11.3.5 的底层能力：

- AST 双轨：HTML -> Full AST -> Simplified AST。
- PageAnalysis：可操作元素、标签、semantic roles。
- 操作路径证据：ExplorationRun steps、LearnedPath actions、Replay observation。
- LearnedPath catalog / retrieval。
- Task planning schemas / result reporter。
- Conversation intake / provenance / redacted LLM trace。

因此本轮不应重造“Agent 直接看网页乱点”的系统，而应把这些能力整理为受控
Capability Runtime。

## Acceptance blockers

不得 accepted 的情况：

- Router 直接调用 start_learning / start_replay。
- LLM 输出 selector / Playwright step / learned_path_id 并被当作执行授权。
- Orchestrator 跳过 target scope / risk 校验。
- 未学过页面跨站点命中历史 LearnedPath。
- 高风险动作自动执行。
- Page Understanding output 写入 LearnedPath proof。
- History 或 trace 明文展示 password / token / access_secret。
- 文档或代码假设 active browser tab 已可用。
- 把旧用户操作录制 / Chrome extension 栈写成当前能力。
- 非 `interactive_chat` developer workflow 被改坏。

## 当前状态

本提交只生成 / 更新文档。实现、测试和 manual smoke 均未开始。
