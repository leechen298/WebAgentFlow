# 契约（Contract）

状态：ready_for_implementation（docs review passed, implementation not started）

## 角色契约

### Conversation Intake Agent / 对话理解 Agent

Conversation Intake Agent 是 `wagent chat` 的自然语言入口层。

它负责：

- 理解用户当前消息。
- 判断用户是要学习操作、执行操作、补充缺失信息，还是未知。
- 抽取目标 URL / 页面指代。
- 抽取用户想达成的 action goal。
- 抽取用户提供的输入槽位。
- 标记缺失信息。
- 归一化相近说法，例如 `登录`、`进入工作台`、`打开工作台`。
- 输出结构化 JSON 给 Conversation Orchestrator。

它不负责：

- 不直接操作浏览器。
- 不调用 Playwright。
- 不看浏览器逐步决定点击哪里。
- 不选择最终 LearnedPath。
- 不绕过 current session learned action scope。
- 不替代 Task Path Planner。
- 不做 L3 step-by-step browser execution。
- 不决定危险操作是否可以执行。
- 不把自己名字暴露给最终用户。

### Conversation Orchestrator / Dispatcher

Conversation Orchestrator 继续是代码侧 session controller 和 internal Agent router。

它负责：

- session 状态。
- pending intake 合并和清理。
- target URL / site origin scope 校验。
- current session learned action 匹配。
- 是否允许 learning / replay。
- 最终用户可见回复拼装。
- 非 `interactive_chat` 路径保持不变。

## Intent 契约

第一阶段只定义：

```text
learn_operation
execute_operation
provide_missing_info
unknown
```

`provide_missing_info` 只能在当前 session 存在 `pending_intake` 时生效。
如果没有 pending intake，用户只输入 `用户名 demo，密码 123456` 不得触发 learning / replay；
系统应提示用户先说明要学习或执行什么操作。

## 结构化输出契约

Conversation Intake Agent 输出必须通过 JSON / Pydantic schema 校验。

最小字段：

```json
{
  "intent": "learn_operation",
  "target": {
    "url": "http://localhost:5176/workspace-login",
    "site_origin": "http://localhost:5176",
    "page_hint": "工作台登录页"
  },
  "action": {
    "goal": "登录",
    "canonical_goal": "进入工作台",
    "aliases": ["登录", "进入工作台", "打开工作台"]
  },
  "slots": [
    {
      "name": "operator_account",
      "semantic_type": "username",
      "label_seen": "操作员账号",
      "value": "demo",
      "sensitive": false,
      "source": "user_message"
    },
    {
      "name": "access_secret",
      "semantic_type": "password",
      "label_seen": "访问口令",
      "value": "123456",
      "sensitive": true,
      "source": "user_message"
    }
  ],
  "missing_fields": [],
  "confidence": 0.86,
  "should_ask_user": false,
  "ask_user_message_hint": null
}
```

缺少信息时：

```json
{
  "intent": "learn_operation",
  "target": {
    "url": "http://localhost:5176/workspace-login"
  },
  "action": {
    "goal": "登录",
    "canonical_goal": "进入工作台",
    "aliases": ["登录", "进入工作台"]
  },
  "slots": [],
  "missing_fields": [
    {
      "semantic_type": "username",
      "display_name": "用户名或账号"
    },
    {
      "semantic_type": "password",
      "display_name": "密码或口令"
    }
  ],
  "confidence": 0.78,
  "should_ask_user": true,
  "ask_user_message_hint": "我需要登录用的用户名和密码。"
}
```

## Pending Intake 契约

缺少信息时，session metadata 保存：

```json
{
  "pending_intake": {
    "intent": "learn_operation",
    "target": {
      "url": "http://localhost:5176/workspace-login",
      "site_origin": "http://localhost:5176"
    },
    "action": {
      "goal": "登录",
      "canonical_goal": "进入工作台"
    },
    "slots": [],
    "missing_fields": ["username", "password"],
    "created_from_message_id": "...",
    "turns_remaining": 3
  }
}
```

清理规则：

- learning 成功后清除。
- 用户取消、退出或新学习目标覆盖时清除。
- 超过 `turns_remaining` 后清除。
- target URL 变化且用户未确认时不得自动合并。
- schema 校验失败时不清除，允许用户重说。

## 文案归口契约

Intake Agent 可以提供 `ask_user_message_hint`，但最终 `user_response` 必须由
Conversation Orchestrator 统一生成或过滤。

用户可见回复不得暴露：

- `Conversation Intake Agent`
- schema / JSON
- confidence
- slot
- selector / id / className
- LearnedPath / replay id / run id

## 执行授权契约

`canonical_goal` 只用于匹配辅助，不是执行授权。

Orchestrator 必须基于：

- current session learned actions
- `target_url`
- `site_origin`
- alias / utterance / canonical goal 辅助匹配

做最终执行匹配。

LLM 不得仅凭 `canonical_goal` 触发执行，也不得输出 `learned_path_id` 作为执行授权。

## Evidence 契约

Intake output 是 conversation intake evidence，不是页面事实。

它可以记录为用户意图理解证据，但不得写入：

- LearnedPath 页面观察事实。
- replay result。
- Supervisor verdict。
- page observation evidence。
- LearnedPath execution proof。

## Response Provenance / LLM Trace 契约

M11.3.4 引入 Conversation Intake Agent 后，Conversation History 必须能解释每条
WAgent 用户可见回复的来源。这个能力属于本轮提交范围，不另拆后续编号。

### Response Provenance

`Response Provenance` 指一条 WAgent 回复的生成来源说明。

必须区分：

```text
code
agent
hybrid
unknown
```

- `code`：由确定性代码路径 / 模板生成。
- `agent`：由 WebAgentFlow 内部 Agent 生成，通常背后有 LLM call。
- `hybrid`：由代码生成主回复，但包含 Agent 产出的解释片段或 summary。
- `unknown`：旧数据或历史记录缺失来源信息。

### Reply Producer

`Reply Producer` 指产品运行时里实际生成用户可见文字的组件。

示例：

- `conversation_orchestrator_code`
- `interactive_chat_runtime_code`
- `conversation_intake_agent`
- `task_result_reporter`
- `failure_recovery_agent`

Codex CLI 是外部开发 / 测试 Agent，不是 WebAgentFlow runtime 的 Reply Producer。
History 页面可以帮助 Codex CLI 调试产品会话，但不得把 Codex CLI 写成产品内部 Agent。

### Message metadata

每条 `conversation_messages.role == "agent"` 的 message 应写入：

```json
{
  "response_provenance": {
    "source_type": "code",
    "producer": {
      "type": "code",
      "id": "interactive_chat_runtime_code",
      "display_name": "Interactive Chat Runtime",
      "internal_agent_role": null
    },
    "llm_trace_ids": [],
    "generated_from_event_ids": ["event-id"],
    "fallback": false
  }
}
```

LLM-backed 示例：

```json
{
  "response_provenance": {
    "source_type": "agent",
    "producer": {
      "type": "agent",
      "id": "conversation_intake_agent",
      "display_name": "Conversation Intake Agent",
      "internal_agent_role": "conversation_intake_agent"
    },
    "llm_trace_ids": ["trace-id"],
    "generated_from_event_ids": ["event-id"],
    "fallback": false
  }
}
```

### LLM Trace

涉及 LLM 的回复、intake 或失败解释必须留下脱敏 trace。推荐 event：

```text
llm_trace_recorded
```

payload 至少包含：

```json
{
  "trace_id": "trace-id",
  "purpose": "reply_generation",
  "agent_role": "conversation_intake_agent",
  "provider": "openai",
  "model": "gpt-5.4",
  "request_id": "provider-request-id",
  "prompt_template_id": "conversation_intake.v1",
  "prompt_hash": "sha256:...",
  "schema_name": "ConversationIntakeResult",
  "schema_version": "m11.3.4",
  "schema_validation": "passed",
  "latency_ms": 1200,
  "token_usage": {
    "input_tokens": 1000,
    "output_tokens": 200
  },
  "raw_request": {
    "redacted": true
  },
  "raw_response": {
    "redacted": true
  },
  "parsed_output": {},
  "redaction": {
    "applied": true,
    "sensitive_fields": ["password"]
  }
}
```

如果 raw request / response 太大，payload 可以只保存摘要和 artifact pointer；但 history API
必须明确返回 `raw_record_available=false` 或 pointer 信息，不得假装有完整原始记录。

### History API / UI

`GET /conversation/sessions/{session_id}/history` 应向后兼容地扩展：

- `messages[].response_provenance`
- top-level `llm_traces`
- `raw` 中包含 redacted provenance / trace 数据

`/conversation/history/:session_id` transcript 中应显示：

- `代码生成`
- `Agent 生成`
- `混合生成`
- `未知来源`

LLM-backed 回复展开后应能看到 provider、model、schema、request id、latency、token usage
和 redaction 状态。普通 transcript 不直接铺开完整 prompt 或 raw provider body。

### Evidence boundary

- Response Provenance 是 reply generation evidence，不是业务成功判定。
- LLM Trace 是 LLM call evidence，不是 Supervisor verdict。
- LLM Trace 不得写入 LearnedPath 作为页面事实。
- LLM Trace 不得替代 replay result、page verification、pass_gate 或 scorecard。

## 敏感信息契约

- `password` / `token` / `access_secret` 等 slot 必须标记为 `sensitive=true`。
- 敏感值可以传给 learning / replay 的内部执行流程。
- conversation events / history / console debug JSON 默认应 redacted。
- LLM prompt payload / request log / provider trace 不得长期保存明文 sensitive slot。
- 如果为了 runtime 执行必须临时传入，必须限定为 runtime-only，不作为 debug evidence 长期保存。
- 用户可见回复不得重复明文密码。
- product-test-site 的 `demo / 123456` 是 fixture value，但通用设计仍按 sensitive 处理。

## LLM 输出失败契约

- malformed JSON：不得触发 learning / replay。
- schema 校验失败：不得触发 learning / replay。
- confidence 低于阈值：必须追问，不得猜测执行。
- provider 未配置：可以 fallback deterministic parser，但不得标记 LLM-intake acceptance passed。

## 产品模型 / 路线图对齐

- Product model 对齐：新增 Conversation Intake Agent / 对话理解 Agent。
- Scope boundary 对齐：不让 LLM 进入逐步浏览器执行循环。
- Roadmap / milestone 对齐：属于 M11.3 interactive chat 产品入口增强。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：Yes，新增 runtime intake role。
- 必须同步更新：`docs/product-model.md`、`docs/product-model.zh.md`、`docs/roadmap.md`、`docs/roadmap.zh.md`。

## 非目标

- 不实现 LLM step-by-step 浏览器控制。
- 不实现复杂多页面 workflow。
- 不实现 M12 recovery / abort。
- 不实现真实业务系统适配。
- 不改变 `wagent conversation ...` developer workflow。
