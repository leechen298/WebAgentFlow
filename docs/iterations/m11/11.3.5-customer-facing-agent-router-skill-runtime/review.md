# Review

状态：ready_for_implementation
docs_review：passed
implementation：not_started

## 当前发现

人工 `wagent chat` smoke 暴露出：

```text
用户只发 URL -> 系统误判为 execute
用户再说“学习” -> 系统没有结合上一轮 URL
```

初始 11.3.5 只把问题定义成 Chat Context Recovery UX。后续讨论确认这个范围太窄：
真正的问题是面客 Agent 路由、Orchestrator 裁决、Worker Agent 和 Skill Runtime
边界没有完整建模。

## 设计决策

- 接受：`Customer-Facing Agent Router != Conversation Orchestrator`。
- 接受：Router 只输出路由建议，不直接调用 skill。
- 接受：Orchestrator 是代码侧裁决者，负责 scope、state、MVP 边界、事件和真正调用。
- 接受：Application Skill Registry 是应用能力目录，不是 Agent 列表。
- 接受：Learning Agent 和 Web Operation Agent 是工作 Agent，可以通过 Orchestrator /
  Skill Runtime 请求 skill。
- 接受：Page Understanding Agent 可以提前作为页面语义理解层使用，但不得输出 selector
  或 browser steps。
- 接受：M11.3.5 不实现 active browser tab。
- 接受：M11.3.5 不实现正式 Risk Policy；明显高影响 / 不可逆动作只作为本轮
  `learn_then_execute` 的不支持边界。
- 接受：Thinking policy 必须写死，Router / Page Understanding 默认低延迟结构化输出。

## 文档审核收口（2026-05-19）

结论：docs review passed，可以进入实现阶段。

收口内容：

- 确认 11.3.5 不再是单点 chat recovery bugfix，而是面客 Agent Router
  与应用技能运行时的产品骨架。
- 确认 Router / Orchestrator / Worker Agent / Skill Runtime 边界清楚。
- 确认 Application Skill Registry 已进入 product model 单一权威表，并在本包
  contract 中作为实现期 registry 展开。
- 确认 HTML AST、Simplified AST、PageAnalysis、form label extraction、
  action planning、execution runtime、LearningRunService、LearnedPath model /
  repository、wait-for-change、replay observation、conversation provenance / trace
  和 prompt asset 基础设施均已纳入复用地图。
- 确认 `page_type` / `optional_page_type_hint` 不作为 Page Understanding 契约字段，
  避免把页面理解做成固定场景分类器。
- 确认本轮不实现 active browser tab，不实现正式 Risk Policy / consent gate，
  不重新引入已移除的旧用户操作录制 / Chrome extension 栈。

## 现有基础设施评估

项目已经具备支撑 11.3.5 的底层能力：

- AST 双轨：HTML -> Full AST -> Simplified AST。
- PageAnalysis：可操作元素、标签、semantic roles。
- 操作路径证据：ExplorationRun steps、LearnedPath actions、Replay observation。
- LearnedPath catalog / retrieval。
- Task planning schemas / result reporter。
- Conversation intake / provenance / redacted LLM trace。

因此本轮不应重造“Agent 直接看网页乱点”的系统，而应把这些能力整理为受控
Skill Runtime。

## Acceptance blockers

不得 accepted 的情况：

- Router 直接调用 start_learning / start_replay。
- LLM 输出 selector / Playwright step / learned_path_id 并被当作执行授权。
- Orchestrator 跳过 target scope / MVP 边界校验。
- 未学过页面跨站点命中历史 LearnedPath。
- 明显高影响或不可逆动作进入自动 learn_then_execute。
- Page Understanding output 写入 LearnedPath proof。
- History 或 trace 明文展示 password / token / access_secret。
- 文档或代码假设 active browser tab 已可用。
- 把旧用户操作录制 / Chrome extension 栈写成当前能力。
- 非 `interactive_chat` developer workflow 被改坏。

## 当前状态

文档审核已通过，可进入实现。实现、测试和 manual smoke 均未开始。
