# 技术设计（Technical Design）

状态：ready_for_implementation（docs review passed, implementation not started）

## 当前状态

当前 `wagent chat` 的 interactive chat runtime 主要通过 deterministic parser 和 regex 处理用户输入：

- 学习意图：URL + 学习关键词。
- 输入抽取：固定 label regex。
- 执行命中：当前 session learned action 的 utterance / alias 匹配。

这足以完成 M11.3.3 product-level smoke，但不足以支持普通用户的自然表达。

## 目标结构

```text
User message
-> ConversationIntakeService
-> ConversationIntakeResult schema validation
-> Conversation Orchestrator state / scope / policy validation
-> LearningRunService or replay handler
```

## 新增服务边界

建议新增：

```text
apps/api/app/services/conversation/intake.py
apps/api/app/schemas/conversation_intake.py
apps/api/tests/test_conversation_intake.py
```

`ConversationIntakeService` 职责：

- 读取 raw user message。
- 读取当前 session metadata 摘要。
- 读取 pending intake。
- 读取当前 session learned actions 摘要。
- 调用 LLM-backed provider 或 fake / deterministic fallback。
- 校验并返回 `ConversationIntakeResult`。

M11.3.4 的 contract 定义角色和 schema，不绑定具体 LLM provider。
实现测试可以使用 fake / stub Intake provider。真实 LLM smoke 才能标记
LLM-intake acceptance passed。

## Schema

建议 schema：

```text
ConversationIntakeIntent = learn_operation | execute_operation | provide_missing_info | unknown
ConversationIntakeTarget = url, site_origin, page_hint
ConversationIntakeAction = goal, canonical_goal, aliases
ConversationIntakeSlot = name, semantic_type, label_seen, value, sensitive, source
ConversationMissingField = semantic_type, display_name
ConversationIntakeResult = intent, target, action, slots, missing_fields, confidence, should_ask_user, ask_user_message_hint
```

Schema 校验失败时，chat runtime 不得调用 learning 或 replay。

## Pending Intake

`pending_intake` 存在 session metadata 中。

Orchestrator 合并规则：

- 只有当前 session 存在 pending intake 时，`provide_missing_info` 才能生效。
- 补充信息的 target URL 缺失时继承 pending target。
- 补充信息包含不同 target URL 时不得自动合并，应要求用户重新说明。
- 合并后缺失字段清空，才能进入 learning。
- learning 成功、用户取消、用户退出、新学习目标覆盖、turns 用尽时清除。
- schema 校验失败时保留 pending intake。

## Chat Runtime 集成

`interactive_chat` session 优先进入 Conversation Intake flow。

推荐行为：

- `learn_operation` 且信息完整：调用 product-level learning。
- `learn_operation` 且缺信息：保存 pending intake，回复 Orchestrator 生成的追问。
- `provide_missing_info` 且 pending intake 存在：合并后继续学习或继续追问。
- `provide_missing_info` 但 pending intake 不存在：提示先说明要学习或执行什么。
- `execute_operation`：按 current session learned actions + target URL / site origin scope 匹配。
- `unknown`：给出普通用户可理解的提示，不触发浏览器动作。

非 `interactive_chat` session 不走 M11.3.4 intake flow，继续走现有 preview /
confirmation / developer workflow。

## LLM Prompt 和 Redaction

Prompt 只允许包含完成 intake 所需的最小上下文：

- 当前用户消息。
- pending intake 摘要。
- 当前 session learned action 的脱敏摘要。
- 输出 schema 和边界说明。

不得长期保存明文 sensitive slot 到：

- LLM request log。
- provider trace。
- conversation history。
- debug console raw JSON。

如果运行时必须临时传入敏感值，必须作为 runtime-only 数据处理。

## Orchestrator Guardrails

Orchestrator 必须二次校验：

- URL 合法性和 site origin。
- current session learned action scope。
- `canonical_goal` 只作为辅助，不作为授权。
- LLM 不得输出 `learned_path_id`。
- LLM 不得输出 selector 或 browser actions。
- 低 confidence 必须追问。

## Contract Alignment

- 对齐 product model：新增受控自然语言入口 Agent，但不让 LLM 操作浏览器。
- 对齐 M11.3.3：继续只学习和操作用户输入的 target site，不读取 validation oracle。
- 对齐 M11.3.2：history/debug console 展示时必须 redacted sensitive slots。
- 对齐 M11.1/M12：不改变 confirmation gate、recovery、abort 或 developer workflow。

## 非目标

- 不实现完整 dialogue manager。
- 不实现高风险操作 consent policy。
- 不实现多页面 workflow。
- 不实现 global LearnedPath 自动召回。
- 不实现 UI 看板改造。
