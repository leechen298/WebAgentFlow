# 11.3.5.1 · Conversation Entry Gate & Chat Latency UX

状态：ready_for_implementation
里程碑：M11
类型：code
父迭代：11.3.5 · Customer-Facing Agent Router & Skill Runtime

## 迭代定位

11.3.5 已经把 `wagent chat` 的面客入口升级为：

```text
Context Collector
-> Conversation Intake Agent
-> Customer-Facing Agent Router
-> Orchestrator
-> Worker Agent / Skill Runtime
```

人工试用继续暴露出入口体验问题：非网页任务消息仍可能进入 Intake + Router
两层 LLM，导致简单输入也等待较久；CLI 目前只打印一次 `正在理解你的需求。`，
这不是持续 working 状态，用户会感觉整个 CLI 卡住。

本 patch-level 迭代不改 11.3.5 的 Router / Skill Runtime 主架构，而是在入口前
增加轻量 **Conversation Entry Gate / 对话入口门禁**，并把 CLI 等待体验升级为
参考 Codex CLI / Claude Code CLI 的持续 working 反馈。

## 核心原则

```text
Entry Gate 不是 Router。
Entry Gate 不是新的工作 Agent。
Entry Gate 不调用 skill。
Entry Gate 不触发 learning / replay。
Entry Gate 只判断是否需要进入网页任务 runtime。
```

无关内容、普通问候、能力询问、闲聊和非网页任务应快速得到友好回复，并把用户引导回
WebAgentFlow 可以处理的网页操作任务，不进入 Intake + Router + Skill Runtime。可能是
网页任务的输入继续进入 11.3.5 runtime。

CLI 必须在等待 API 返回期间呈现持续 working 状态，而不是只输出一行进度文本后静默等待。
这里的参考目标不是复制 Codex CLI / Claude Code CLI 的视觉样式，而是采用同类交互原则：
用户提交后立即看到系统在工作，等待期间持续有反馈，阶段变化可感知，取消时终端保持干净，
最终回复和临时进度严格分离。

## 本轮目标

- 新增 Entry Gate 概念和 schema contract。
- 在 Intake / Router 前建立轻量、低延迟、非 thinking 的相关性判断。
- 非网页任务直接生成统一 WAgent 口径的友好回复。
- 闲聊 / 无关内容快速响应，并引导用户回到 WebAgentFlow 的网页学习、执行和调试能力。
- 网页任务候选继续进入 11.3.5 的 Intake / Router / Skill Runtime。
- Entry Gate 失败、低置信、malformed output 时不得触发 learning / replay。
- Entry Gate 必须有硬超时；超时后快速走友好 fallback，不继续等待慢模型。
- `wagent chat` 等待 API 响应时显示持续 working indicator，并避免把 progress 当作最终回复。
- Conversation History detail 能看到 Entry Gate trace、latency、是否跳过重型 runtime。
- Conversation History 不得保存 provider thinking / chain-of-thought。

## 明确不做

- 不做完整闲聊系统。
- 不让 Entry Gate 替代 Conversation Intake Agent。
- 不让 Entry Gate 替代 Customer-Facing Agent Router。
- 不让 Entry Gate 理解页面、选择工作 Agent、调用 skill 或触发浏览器动作。
- 不硬编码问候白名单作为产品策略。
- 不做 active browser tab。
- 不做 M12 recovery / retry / abort。
- 不改变 11.3.5 Skill Registry。
- 不改变非 `interactive_chat` developer workflow。

## 迭代文档

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`

## 当前状态

设计评审通过，进入实现阶段；当前 `wagent chat` 的一次性 `正在理解你的需求。`
不能视为本迭代要求的持续 loading / working UX。
