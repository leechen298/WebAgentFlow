# 意图（Intent）

状态：ready_for_implementation

## 目标

让 `wagent chat` 在进入 11.3.5 重型 Agent runtime 前，先用轻量 Entry Gate 判断
是否属于网页任务；同时把 CLI 等待体验从一次性进度文案升级为持续可感知的 working
状态。

## 动机

当前 `wagent chat` 已接入 Conversation Intake Agent 和 Customer-Facing Agent Router。
这让网页任务的语言理解和路由能力更强，但也带来入口延迟：简单的非网页消息可能仍串行
调用 Intake LLM 和 Router LLM。用户看到的只有一次性 `正在理解你的需求。`，后续等待
没有 spinner、阶段状态或耗时反馈，观感像 CLI 卡住。

这个问题不应通过硬编码问候绕过，也不应削弱 11.3.5 Router 架构。正确做法是在入口处
加入窄职责的 Entry Gate：

```text
用户消息
-> Entry Gate 判断是否需要网页任务 runtime
-> 非网页任务：快速友好回复
-> 网页任务候选：进入 Intake + Router + Skill Runtime
```

## 边界 / 非目标

- 不新增产品 Agent 角色；Entry Gate 是入口组件，不是 Router、Worker Agent 或 Skill。
- 不实现完整闲聊、知识问答或通用助手能力。
- 不硬编码问候白名单作为长期产品行为。
- 不让 LLM 直接操作浏览器。
- 不让 Entry Gate 调用 skill、选择 LearnedPath、输出 selector 或浏览器步骤。
- 不改变 11.3.5 的 Skill Registry 主体。
- 不运行 live autonomous run 或 `verify-scenario`。

## 成功标准

- 非网页任务输入能快速返回友好回复，并跳过 Intake / Router。
- 闲聊和无关内容的回复应引导用户回到 WebAgentFlow 的使用场景，例如学习页面操作、
  执行已学操作或查看调试历史；不得扩展成开放式通用聊天。
- 网页任务候选输入继续进入 11.3.5 runtime，不被 Entry Gate 误拦。
- Entry Gate provider 失败、malformed JSON、schema 校验失败或低置信时不得触发
  learning / replay。
- Entry Gate provider 慢响应必须被硬超时截断，默认目标不超过 1.5 秒，绝对上限不超过
  2 秒；超时后走友好 fallback。
- CLI 等待 API 返回期间持续显示 working 状态，用户能知道系统仍在工作。
- progress / working 状态不被记录成正式 WAgent agent reply。
- History detail 可审计 Entry Gate 决策、latency、是否跳过 Intake / Router，以及最终回复来源。
- History detail 不得保存或展示 provider thinking / chain-of-thought。
