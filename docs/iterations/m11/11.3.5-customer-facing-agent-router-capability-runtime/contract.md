# Contract

状态：proposed（docs generated, implementation not started）

## 核心不变量

1. Customer-Facing Agent Router 不是 Conversation Orchestrator。
2. Router 只输出结构化路由建议，不直接调用 capability。
3. Orchestrator 是代码侧裁决者，负责状态、scope、risk、授权、调用和事件。
4. Capability Runtime 是执行者，只执行已注册、可审计的应用能力。
5. Learning Agent / Web Operation Agent / Page Understanding Agent 可以组织工作，
   但必须通过 Orchestrator / Capability Runtime 请求能力。
6. LLM 不得直接控制浏览器，不得输出 selector、Playwright step 或 learned_path_id
   作为执行授权。
7. LearnedPath / replay / Supervisor evidence 只能来自真实浏览器执行和代码侧证据，
   不能来自 LLM 猜测。

## 角色契约

| Role | 中文名 | 本质 | 输出 | 能否直接调用 capability | 边界 |
|---|---|---|---|---|---|
| Conversation Intake Agent | 对话理解 Agent | 语言理解层 | intent、target、slots、missing_fields | 否 | 不操作浏览器，不选择路径 |
| Customer-Facing Agent Router | 面客 Agent Router | 路由建议者 | route_decision、next_agent、recommended_capability | 否 | 只建议，不执行 |
| Conversation Orchestrator | 会话编排器 / 调度器 | 代码控制层 | 调用、追问、拒绝、记录、用户回复 | 是 | 最终裁决者 |
| Page Understanding Agent | 页面理解 Agent | 页面语义理解 | page_type、supported_goals、required_slots、risk_hints | 否 | 不输出 selector 或步骤 |
| Learning Agent | 学习 Agent | 学习流程组织者 | learning request / learning result summary | 通过 Orchestrator 请求 | 不把猜测写成路径证据 |
| Web Operation Agent | 网页操作 Agent | 操作执行组织者 | replay / learn_then_execute request | 通过 Orchestrator 请求 | 不跨站点，不发明步骤 |
| Task Result Reporter | 结果反馈 Agent | 结果解释层 | 用户可读结果 | 否 | 不创造事实 |

## Route Decision Schema

Router 输出必须是 schema-constrained JSON。第一版字段：

- `route_decision`
- `next_agent`
- `recommended_capability`
- `target.url`
- `target.site_origin`
- `target.source`
- `user_goal`
- `known_context.has_learned_action`
- `known_context.has_required_user_inputs`
- `known_context.page_context_available`
- `missing_fields[]`
- `risk_level`
- `confidence`
- `reason_summary`

这些字段是通用契约，不绑定任何测试页面、业务页面、固定输入、固定按钮或固定话术。

允许的第一版 `route_decision`：

- `ask_user`
- `inspect_page`
- `understand_page`
- `delegate_to_learning_agent`
- `delegate_to_web_operation_agent`
- `report_unknown`
- `decline_unsupported`

允许的第一版 `next_agent`：

- `conversation_orchestrator`
- `page_understanding_agent`
- `learning_agent`
- `web_operation_agent`
- `task_result_reporter`

允许的第一版 `recommended_capability`：

- `collect_conversation_context`
- `inspect_target_page`
- `understand_page`
- `lookup_learned_actions`
- `ask_user_for_missing_info`
- `start_learning`
- `start_replay`
- `learn_then_execute`
- `record_progress_event`
- `record_agent_trace`

## Capability Registry

Capability Registry 是应用能力目录。它不是 Agent 列表。

| Capability | 中文说明 | 主要用途 | 请求方 | 真正执行方 | 浏览器 | 改变页面 | 沉淀 LearnedPath |
|---|---|---|---|---|---|---|---|
| `collect_conversation_context` | 收集会话上下文 | 最近消息、pending 状态、已学 actions、最后目标、no-path 原因 | Orchestrator | 代码 | 否 | 否 | 否 |
| `inspect_target_page` | 检查目标页面 | 给定 URL，获取 title、URL、可见文本、控件摘要、Full/Simplified AST、PageAnalysis | Router 建议 / Worker 请求 | Runtime + 代码 | 可以 | 否 | 否 |
| `understand_page` | 理解页面语义 | 判断页面类型、主要目标、必需输入、风险 | Router 建议 / Learning Agent 请求 | Page Understanding Agent | 否 | 否 | 否 |
| `lookup_learned_actions` | 查询已学操作 | 查询 current session / target scope 下已学操作 | Router / Web Operation Agent | 代码 / Repository | 否 | 否 | 否 |
| `ask_user_for_missing_info` | 追问缺失信息 | 询问缺少的目标、URL、参数、输入或确认 | Router 建议 | Orchestrator / Reporter | 否 | 否 | 否 |
| `start_learning` | 启动学习 | 调用 LearningRunService / autonomous exploration 学习操作 | Learning Agent | Learning Service | 是 | 可能 | 是 |
| `start_replay` | 执行已学路径 | 调用 replay 执行 LearnedPath | Web Operation Agent | Replay Service | 是 | 可能 | 否 |
| `learn_then_execute` | 先学再执行 | 对未学过但信息完整、风险允许的任务，先学习再 replay | Web Operation Agent / Learning Agent | Capability Runtime 编排 | 是 | 可能 | 是 |
| `record_progress_event` | 记录进度 | 让 CLI / Console 知道正在理解、检查、学习、执行 | Orchestrator / Runtime | 代码 | 否 | 否 | 否 |
| `record_agent_trace` | 记录 Agent 轨迹 | 记录 Intake、Router、Page Understanding 等结构化输出 | Agent Runtime | 代码 | 否 | 否 | 否 |

## Target Resolution

目标页面来源优先级：

1. 用户当前消息中的显式 URL。
2. `pending_target`。
3. 最近提到的 URL / last no-path context。
4. 当前 session 唯一已学 action 的 target。
5. 未来能力：active browser tab。M11.3.5 不实现，不得假设已存在。
6. 仍不确定时追问用户。

## Page Context Contract

`inspect_target_page` 应尽量组合已有基础设施输出：

- current URL / title。
- visible text summary。
- interactive element summary from PageAnalysis。
- labels and semantic roles from form label extraction / page analyzer。
- HTML -> Full AST。
- Full AST -> Simplified AST。
- optional screenshot reference。
- page signature / path_template / query_signature / dom_fingerprint。
- current-session learned action summary for the same target scope。

Page Understanding Agent 只读取 page context bundle，输出页面语义。第一版字段：

- `page_type`
- `supported_goals[]`
- `supported_goals[].goal`
- `supported_goals[].canonical_goal`
- `supported_goals[].aliases[]`
- `supported_goals[].required_slots[]`
- `supported_goals[].risk_level`
- `confidence`
- `reason_summary`

这些字段描述页面可支持的用户目标和所需输入，不得把某个测试页面、字段名、按钮名或
业务动作写成契约。

它不得输出 selector、DOM path、Playwright step 或 LearnedPath action。

## Risk Policy

M11.3.5 只定义轻量风险策略，不引入完整权限系统。

| Risk | 判定口径 | 策略 |
|---|---|---|
| `low` | 只读或可安全重复、不会修改目标系统关键状态的操作 | 信息完整时可 `learn_then_execute` |
| `medium` | 会改变页面状态但通常可恢复、可重新执行或影响范围有限的操作 | 可学习；执行时复用现有 confirmation / chat policy |
| `high` | 不可逆、外部可见、涉及资产/权限/大范围数据变更或高影响提交的操作 | M11.3.5 不自动执行，必须追问 / 拒绝 / 交给后续 consent 设计 |

本轮不新增复杂用户同意 UI。高风险自动执行是 acceptance blocker。

## Thinking Policy

- Router：no-thinking / low-latency，结构化 JSON，短 `reason_summary`。
- Page Understanding Agent：no-thinking / low-latency，结构化 JSON，短 `reason_summary`。
- Learning / Replay execution：代码执行，不让 LLM step-by-step 控制。
- Failure Recovery：复杂恢复和长思考留到 M12。
- History 只保存脱敏 trace metadata 和简短 reason，不展示 chain-of-thought。

## Prompt Asset Contract

Agent prompt 是产品资产，不是业务 service 里的长字符串。11.3.5 开始，新增或调整
LLM-backed Agent 时必须把 prompt 放到固定 prompt asset 目录，由代码按 prompt id /
version 加载。

推荐目录：

```text
apps/api/app/prompts/
  README.md
  registry.toml
  shared/
    webagentflow_boundaries.md
    evidence_and_scope.md
    redaction_rules.md
    structured_output_rules.md
  agents/
    conversation_intake_agent/
      prompt.md
      metadata.toml
    customer_facing_agent_router/
      prompt.md
      metadata.toml
    page_understanding_agent/
      prompt.md
      metadata.toml
    learning_agent/
      prompt.md
      metadata.toml
    web_operation_agent/
      prompt.md
      metadata.toml
    task_result_reporter/
      prompt.md
      metadata.toml
```

约束：

- service 代码只能引用 prompt id / version / loader，不得内嵌大段 system prompt。
- shared prompt fragments 只能放通用边界、证据、脱敏和结构化输出规则，不得放页面或测试站特例。
- 每个 Agent prompt 独立存放，避免把 Router、Page Understanding、Learning、Web Operation
  的职责混在一个 prompt 里。
- `metadata.toml` 必须声明 prompt id、version、agent role、schema name、runtime policy、
  allowed inputs、forbidden outputs 和 sensitive context policy。
- prompt asset 不复制 Pydantic schema；它只引用 schema 名称 / 版本。schema truth 仍在
  `apps/api/app/schemas/`。
- History / trace 必须记录 prompt id、prompt version、prompt content hash、schema name、
  provider、model 和 redaction 状态。
- 如果 prompt 文件缺失、version 不匹配或 hash 校验失败，Orchestrator 不得触发 learning /
  replay。

## 用户可见行为

### 裸 URL

用户只提供目标 URL 时，系统不得直接 execute。系统应保存 `pending_target`，
并询问用户要学习或执行的操作目标。

### URL 后短句学习

如果 session 已存在 `pending_target`，用户下一轮给出短学习意图时，系统应结合
pending target 进入学习路线判断。如果缺少 action goal 或 slots，Orchestrator 应追问。

### 未学过但信息完整

用户要求执行一个当前 session 未学过的目标，但 URL、目标和必要输入都完整时，是否进入
`learn_then_execute` 取决于 risk policy 和 Orchestrator 校验。

### 缺信息

缺少必要信息时，系统必须追问，不得猜测，不得从 validation spec / assertions 或其他
测试 oracle 取值。

## Evidence Boundary

- Router decision、page understanding 和 intake trace 是 conversation evidence。
- 它们不得写入 LearnedPath 作为页面观察事实、步骤证据或执行证明。
- LearnedPath actions 只能来自 Learning Service / Replay / user demonstration 等真实执行证据。
- Supervisor verdict 仍只由 autonomous exploration 的 Supervisor 链路产生。
