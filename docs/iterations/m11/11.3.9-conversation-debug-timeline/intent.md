# 意图（Intent）

状态：docs_generated_pending_design_review

## 目标

把现有 Conversation History detail 升级为 `wagent chat` 的可解释调试时间线，让用户和开发者能看懂“我现在具体在做什么、为什么这么回复、下一步等什么”，而不是只看到后端终端 HTTP 日志或 raw JSON。

## 动机

用户反馈当前本地后端终端日志不可读：

- 只能看到服务重启、HTTP request、LLM provider request 等基础信息。
- 看不到当前会话正在理解哪个输入、路由到哪个 runtime 分支、生成了什么选项、为什么等待用户选择。
- 如果直接把请求返回参数打印到终端，容易刷屏、暴露敏感信息，也不适合作为产品调试入口。

项目已有更合适的基础：Conversation sessions、messages、events、response provenance、
LLM traces 和 Console history detail。当前缺口不是“没有日志”，而是缺少一个把这些
结构化事件翻译成人能理解的运行轨迹视图。

本包承接 11.3.2 Chat History & Debug Console，但范围更窄：只增强
`/conversation/history/:session_id` 的可解释性和 CLI 的调试入口提示。

## 边界 / 非目标

- 本轮不新增 runtime learning、execution、replay、recovery、abort 或 task planning 能力。
- 不新增数据库表；优先从既有 `conversation_events`、messages、session metadata 和 trace read model 派生。
- 不把完整 LLM request / response、页面 DOM、用户敏感输入或 private maps 输出到终端或普通页面。
- 不做通用日志平台、全文搜索、日志聚合、长期归档、权限系统或多租户审计。
- 不触发 `verify-scenario`、autonomous run 或 product-driven browser execution。
- 不改变产品对外统一口径；用户-facing 文案仍从“我”的视角表达，内部 trace 只在后台调试页展示。

## 成功标准

- `GET /conversation/sessions/{session_id}/history` 返回一个脱敏的 `debug_timeline` read model，能按时间顺序解释本会话关键步骤。
- Timeline item 至少覆盖用户输入、WAgent 回复、intake / entry gate / router trace、pending choice / action options、learning / replay start / completion、failure / recovery、cancel 等常见 chat runtime 节点。
- Console detail 默认展示“运行轨迹 / Debug Timeline”视图；每个节点有面向人类的标题、摘要、状态、来源、时间、关联 message/event/trace id，并支持展开脱敏 payload。
- Events / Raw JSON 仍保留，作为开发者深挖入口；Timeline 不替代 raw evidence。
- CLI 创建 session 后给出更明确的后台调试路径提示，至少包含 session id 和 Console history path。
- 后端终端日志保持简洁，不新增 raw payload dump；如调整终端日志，只允许增加 session_id / message_id / trace_id / latency / error summary 等低噪声关联信息。
- 所有新增 read surfaces 不发明内部 Agent 结论，不把 `unverified`、缺失 evidence 或静态推理写成 pass。
