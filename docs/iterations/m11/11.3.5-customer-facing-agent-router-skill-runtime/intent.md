# Intent

## 背景

M11.3.3 证明了 product-test-site 与 validation-site 可以拆开，`wagent chat`
可以在产品级测试站上学习并执行当前 session 中学过的操作。M11.3.4 引入
Conversation Intake Agent，让 LLM / fallback 负责把用户话语理解成结构化 intent。

但小白用户真实操作暴露出问题：系统虽然调用了 Intake Agent，但仍可能把裸 URL、
短句补充和未学过目标处理成彼此割裂的单轮命令。

这不是“用户没按格式说话”。小白用户输入 URL，本质是在告诉系统目标页面；下一句
“学习”，本质是在补充意图。产品应该能主动收集上下文、检查自己是否学过、必要时
理解页面、再决定追问、学习或执行。

## 产品意图

11.3.5 的目标是把 `wagent chat` 从：

```text
代码初筛 -> Intake intent -> 直接 learn / execute / unknown
```

升级为：

```text
Context Collector
-> Conversation Intake Agent
-> Customer-Facing Agent Router
-> Conversation Orchestrator
-> Worker Agent
-> Skill Runtime
-> Result Reporter
```

用户仍然只看到统一的 WAgent 回复，不看到内部 Agent 名称、schema、trace 或 route
decision。

## 角色意图

### Customer-Facing Agent Router

面客 Router 是 LLM-backed / schema-constrained 的路由建议者。它回答：

```text
下一步建议交给谁？
```

它不调用 skill，不执行浏览器动作，不做最终授权。

### Conversation Orchestrator

Orchestrator 是代码侧编排器 / 调度器。这个词是软件和 Agent 系统里常用的说法，
意思是“负责协调多个组件按规则工作的人 / 控制层”。在 WebAgentFlow 中它不是 LLM
Agent，而是代码侧裁决者。它回答：

```text
这个建议能不能执行？由谁执行？如何记录？
```

### Application Skill Registry

Application Skill Registry（也可称 Skill Registry）是应用能力目录。它列出系统能做的
受控能力，包括收集上下文、检查页面、理解页面、查询已学操作、追问用户、启动学习、
执行已学路径、先学再执行、记录进度事件和记录 Agent trace。

Skill 是“应用能力”，不是 Agent。Agent 可以建议或请求使用 skill；
真正调用由 Orchestrator / Skill Runtime 执行。

### Worker Agents

11.3.5 MVP 中定义三个工作 Agent 边界：

- Page Understanding Agent：理解页面能支持哪些用户目标。
- Learning Agent：组织学习流程。
- Web Operation Agent：组织执行用户要求的网页操作。

它们可以通过 Orchestrator / Skill Runtime 请求 skill，但不能绕过代码侧
scope / state / MVP 边界校验。

## 现有基础设施意图

本轮必须复用现有基础设施，而不是另起一套“Agent 看网页”系统：

- HTML AST 和 Simplified AST 为页面理解提供结构化输入。
- PageAnalysis / form label extraction 为字段、按钮、控件语义提供输入。
- ExplorationRun steps 和 LearnedPath actions 记录真实操作路径，辅助 Router 判断
  系统是否学过类似操作。
- Task planning schemas 已经提供 route、postcondition、artifact 等结构化概念，
  11.3.5 应尽量复用这些词汇。

## 成功标准

本轮文档通过后，后续实现应能达到：

- 裸 URL 不再被当作执行请求。
- 系统能保存 pending target 并追问用户想学习或执行什么。
- 短句、指代和自然表达可以结合上下文解释。
- 未学过但信息完整、且处于 M11.3.5 MVP 支持范围内的任务可以进入
  learn-then-execute 策略。
- 缺信息时追问，不猜测执行。
- Router、Orchestrator、Worker Agent、Skill Runtime 的责任可审计。
- History detail 能解释 Agent 路由、代码裁决、skill 调用和最终回复来源。
