# 契约（Contract）

状态：ready_for_implementation

## 概念 / 边界契约

### Conversation Entry Gate

Conversation Entry Gate 是 `interactive_chat` 的入口门禁组件。它位于
Conversation Intake Agent 之前，只负责判断当前用户消息是否需要进入网页任务 runtime。

它不是新的 Agent 角色，不进入产品模型主 Agent 列表。

Entry Gate 允许做：

- 判断消息是否为网页任务候选。
- 判断消息是否明显是非网页任务 / 闲聊 / 能力询问 / 普通问候。
- 给 Orchestrator 一个短 `reply_hint`，用于生成统一 WAgent 口径回复。
- 输出低延迟、非 thinking 的结构化 JSON。
- 记录脱敏 trace、latency 和 provider/model metadata。
- 在硬超时内完成；默认目标不超过 1.5 秒，绝对上限不超过 2 秒。

Entry Gate 不允许做：

- 不调用 skill。
- 不调用 Playwright。
- 不触发 learning / replay。
- 不选择 LearnedPath。
- 不理解页面。
- 不选择工作 Agent。
- 不输出 selector、DOM path、browser steps 或 learned_path_id。
- 不把自己的输出写入 LearnedPath / replay / Supervisor evidence。

## 状态 / 结果契约

Entry Gate 第一版输出分类：

- `web_task_candidate`：可能是网页任务，继续进入 Intake + Router。
- `non_web_chat`：非网页任务，由 Orchestrator 快速友好回复，并引导用户回到
  WebAgentFlow 的网页操作能力。
- `capability_question`：用户在问 WAgent 能做什么，由 Orchestrator 用固定产品能力说明回复。
- `needs_clarification`：不确定是否网页任务，Orchestrator 追问；不得触发 learning / replay。
- `unsupported`：明确不属于当前产品范围，Orchestrator 友好拒绝或说明边界。

状态优先级：

1. 显式网页任务信号优先进入 `web_task_candidate`。
2. 明显非网页任务可走 `non_web_chat` / `capability_question`，但最终回复必须收束到
   WebAgentFlow 使用场景，不提供开放式闲聊续聊。
3. 不确定时走 `needs_clarification`，不得猜测执行。
4. provider / parse / schema / low confidence 失败时不得触发 learning / replay。

## Schema / API 契约

建议新增 Entry Gate result schema：

```json
{
  "category": "web_task_candidate",
  "requires_agent_runtime": true,
  "confidence": 0.86,
  "reply_hint": null,
  "reason_summary": "用户输入包含网页任务候选信号。",
  "latency_ms": 120,
  "provider": "provider-name",
  "model": "model-name",
  "fallback": false
}
```

字段契约：

- `category`：只能是允许枚举。
- `requires_agent_runtime`：为 `true` 时进入 11.3.5 runtime。
- `confidence`：低于实现定义阈值时不得进入 learning / replay。
- `reply_hint`：只能作为 Orchestrator 生成最终用户文案的 hint；不得直接作为未过滤回复。
- `reason_summary`：短摘要，不得包含 chain-of-thought。
- `latency_ms`：记录门禁耗时。
- `provider` / `model`：用于 history trace。
- `fallback`：标记是否由 fallback path 产生。
- `error_kind`：可选，记录 timeout / provider_error / parse_error / schema_error / low_confidence。

API response envelope 不改变。Conversation History detail 可在既有 history / trace 字段中展示
Entry Gate trace；不要求新增公开 API 路由。

## Latency / Timeout Contract

Entry Gate 的价值是避免简单输入进入慢速重型 runtime，因此它必须有硬延迟边界：

- 默认 provider timeout 目标：`<= 1500ms`。
- 绝对上限：`<= 2000ms`。
- 超时后必须立即走 friendly fallback / clarification path。
- 超时后不得继续等待 provider 完成后再覆盖回复。
- 超时后不得触发 Intake、Router、learning 或 replay。
- timeout trace 可记录 provider / model / elapsed_ms / error_kind，但不得记录 raw thinking。

如果当前 provider 无法稳定满足该延迟，Entry Gate 必须使用更轻量模型、deterministic fallback
或直接走 friendly fallback；不得把慢模型接在 Entry Gate 上后再依赖 CLI spinner 掩盖等待。

## CLI Working UX 契约

`wagent chat` 等待 `/conversation/.../dispatch` 返回期间必须显示持续 working indicator。

本轮 CLI 体验明确参考 Codex CLI / Claude Code CLI 这类 agentic CLI 的沟通方式。参考的是
交互原则，不是像素级样式：

- 用户提交消息后立即得到“系统正在处理”的反馈。
- 长等待期间持续更新，不进入静默卡住状态。
- 如果系统内部阶段可见，优先展示阶段感；如果阶段不可见，至少保持 spinner / working indicator。
- 临时 progress 与最终 `WAgent >` 回复分离。
- 用户按 Ctrl-C / 中断时，终端状态可恢复，不留下破碎控制字符。
- 非 TTY / 日志环境保持可读，不输出动态控制字符。
- 不用 spinner 掩盖慢模型；Entry Gate 仍必须满足硬超时。

要求：

- 用户输入提交后立即显示工作状态。
- 工作状态是 transient progress，不是正式 agent reply。
- API 返回后清理或完成该工作状态，再打印正式 WAgent 回复。
- 工作状态不得提前断言“学习”“执行”“打开浏览器”。
- 如果终端不支持动态 spinner，必须退化为低噪音的周期性状态文本。
- Ctrl-C 时不留下破碎 spinner 文本。

建议阶段文案：

- `正在理解你的需求`
- `正在判断下一步`
- `正在准备回复`

进入实际学习 / 执行后的阶段性进度仍由已有 progress events / skill events 驱动。

## Non-web Reply Policy

非网页任务、闲聊或无关内容的回复必须满足：

- 快速返回，不进入 Intake / Router / Skill Runtime。
- 保持统一 WAgent 口径。
- 说明当前产品主要用于学习和执行网页操作。
- 给出可执行的下一步引导，例如让用户提供目标 URL、说明要学习的页面操作，或执行已学操作。
- 不扩展成通用聊天、知识问答或长篇闲聊。
- 不泄露内部 category、schema、confidence、provider 或 trace 信息。

## Evidence / Observation 契约

Entry Gate trace 是 conversation evidence。它可以说明：

- 是否运行 Entry Gate。
- category / requires_agent_runtime。
- 是否跳过 Intake / Router。
- latency。
- provider / model / prompt id / prompt version / prompt hash。
- parse / schema / low-confidence failure。
- timeout / provider_error failure。

它不得作为：

- 页面观察 evidence。
- LearnedPath proof。
- replay result。
- Supervisor verdict。
- pass_gate evidence。

Trace / history 必须丢弃或脱敏 provider thinking。以下内容不得长期保存、不得展示在 history
detail，也不得进入 response provenance raw record：

- `<think>...</think>` blocks。
- `thinking` / `reasoning` / `reasoning_content` / `chain_of_thought` 字段。
- provider 返回的长推理文本。

允许保存的只有短 `reason_summary`、category、confidence、latency、provider/model、prompt
metadata 和 redacted error metadata。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：Entry Gate 是 11.3.5 面客入口的运行时组件，不新增 Agent 角色。
- Scope boundary 对齐：仍保持 LLM 不直接操作浏览器；代码负责裁决和执行边界。
- Roadmap / milestone 对齐：作为 11.3.5 patch-level 优化，编号为 11.3.5.1。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 权威文档更新：M11 索引和 M11 计划需要登记本 patch；产品模型主 Agent 表不需要新增角色。

## 兼容性契约

- 非 `interactive_chat` developer workflow 不启用 Entry Gate。
- 既有 11.3.5 Intake / Router / Skill Runtime 保持不变；Entry Gate 只在其前面决定是否进入。
- 旧 history 没有 Entry Gate trace 时，Console 应显示为缺失 / 未记录，而不是错误。
- CLI 非 TTY 环境应使用非动态 progress 文案，避免破坏日志。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API envelope：不变。
- Database schema：默认不变；如实现选择新增字段，必须保持旧数据兼容并写入 migration。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。
- 11.3.5 Skill Registry：不新增主干 skill，除非实现需要内部记录类 helper。

## 非目标

- 不实现完整通用聊天助手。
- 不把 Entry Gate 变成 Router。
- 不让 Entry Gate 做页面理解。
- 不让 Entry Gate 直接产生 LearnedPath 或 Replay 操作。
- 不使用硬编码问候白名单作为主要策略。

## 未决问题

- Entry Gate provider 默认使用哪一个低延迟非 thinking 模型，由实现阶段根据现有
  `llm_provider` 配置能力决定；但无论 provider 如何选择，都必须满足本文件的硬超时。
- CLI spinner 的具体样式由实现阶段按终端兼容性选择；不要求复制 Codex CLI / Claude Code
  CLI 的样式，但必须满足本文件定义的 agentic CLI working interaction。
