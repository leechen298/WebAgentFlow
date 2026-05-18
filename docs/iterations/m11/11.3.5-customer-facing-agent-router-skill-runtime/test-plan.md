# Test Plan

状态：ready_for_implementation（docs review passed, implementation not started）

## 文档阶段

本轮文档阶段只要求：

```bash
git diff --check
```

不得声称实现、LLM smoke、UI smoke、autonomous run 或 E2E 已通过。

## 后续实现测试矩阵

| ID | Surface | 目标 |
|---|---|---|
| CTX-1 | Context Collector | 收集 recent messages、pending_target、pending_intake、last_no_path_reason、learned_actions |
| CTX-2 | Redaction | context bundle 不持久化 sensitive slot 明文 |
| ROUTER-1 | Router schema | route decision JSON 通过 Pydantic / JSON schema 校验 |
| ROUTER-2 | Router guardrail | malformed JSON / low confidence 不触发 learning / replay |
| ROUTER-3 | Router boundary | Router 不直接调用 skill |
| SKILL-1 | Application Skill Registry | 每个 skill 有 preconditions / executor / trace contract |
| PROMPT-1 | Prompt assets | Agent prompt 文件存在于固定目录，service 不内嵌长 prompt |
| PROMPT-2 | Prompt metadata | prompt registry / metadata 包含 id、version、schema、hash、runtime policy |
| PROMPT-3 | Prompt trace | LLM trace 记录 prompt id / version / hash / schema / redaction 状态 |
| PAGE-1 | Page context | 组合 HTML AST、Simplified AST、PageAnalysis、page signature |
| PAGE-2 | Page Understanding | 输出 observed_page_summary、visible_controls、supported_goals、required_slots，不输出 selector / steps |
| TARGET-1 | Target resolution | URL > pending_target > recent URL > unique learned target > ask user |
| UX-1 | Bare URL | 裸 URL 保存 pending_target，不 execute |
| UX-2 | Short learn | “学习”能引用 pending_target 并追问目标/slots |
| UX-3 | No-path | 未学过 target 转学习引导，不冷拒绝 |
| UX-4 | Loading | CLI 先显示中性 loading，不提前说“执行：学习” |
| TRACE-1 | History | 记录 Intake / Router / Orchestrator / skill / final provenance |
| REG-1 | Non chat | 非 `interactive_chat` 保持 preview / confirmation / developer workflow |

## 必测用户行为类别

### 1. 裸 URL

期望：

- 不调用 `start_replay`。
- 不调用 `start_learning`。
- 保存 `pending_target`。
- 回复用户想学习或执行哪个操作。

### 2. URL 后短句学习

前置：session 存在一个 `pending_target`。

期望：

- Router 结合 pending target 输出学习路线建议。
- 如果缺 action goal 或 slots，Orchestrator 追问。
- 不把短学习意图当成 execute task。

### 3. 学习意图自然语言变体

同一类目标应至少覆盖多种自然表达，但测试文档不得固定到某个页面、账号、按钮或字段。

期望：

- intent / route 指向 learning。
- target 由用户消息、pending target 或 target resolution 规则给出。
- slots 能表达用户提供的必要输入。
- sensitive-like slot 标记 sensitive。

### 4. 执行意图泛化

当前 session 已学习同 target 后，用户对同一目标的不同自然表达应能命中同一 action。

期望：

- 只在当前 session、同 target scope 命中。
- 不跨站点召回历史 LearnedPath。

### 5. 未学过但信息完整

用户要求执行未学过的目标，但 target、user goal 和 required slots 均已完整。

期望：

- lookup learned actions 发现未学过。
- 通过 Orchestrator 的 target、goal、slots、current-session scope 和 MVP 边界校验后，
  进入 learn-then-execute 或清晰询问用户是否先学习。
- 不从 validation-site specs / assertions 取输入。

### 6. 组合目标

用户目标由多个页面动作组成时，Router 应输出组合目标，而不是退化为单个按钮动作。

期望：

- Router 输出组合目标。
- Page Understanding 识别页面可支持的相关能力。
- 如果未学过且信息完整，并且处于 M11.3.5 MVP 支持范围内，可以进入 learn-then-execute。
- 执行结果预留 artifact 字段。

## 负例

- LLM provider 未配置：可 fallback deterministic parser，但不得标记 LLM route acceptance passed。
- prompt 文件缺失、metadata 缺字段或 hash 校验失败：不得触发 learning / replay。
- service 函数内硬编码大段 Agent system prompt：不得 accepted。
- LLM 返回 malformed JSON：不得触发 learning / replay。
- schema 校验失败：不得触发 learning / replay。
- confidence 低于阈值：必须追问。
- Router 输出 selector / Playwright step：拒绝并记录 guardrail event。
- Router 输出 learned_path_id 作为授权：拒绝。
- Page Understanding 输出页面事实但无浏览器 evidence：不得写入 LearnedPath proof。
- 明显高影响或不可逆任务不得进入 learn_then_execute；本轮应返回不支持或交给后续
  risk / consent 设计处理。
- active browser tab 未实现时，不得用它作为目标来源。

## Manual smoke（实现后）

启动：

```bash
pnpm run dev
.venv/bin/wagent chat
```

执行时应选择一个非 validation oracle 的产品级测试页面或人工指定页面。测试记录只写目标类别、
route decision、skill 调用和脱敏证据，不把某个固定页面或固定输入写成通用验收契约。

验收：

- 第一轮 URL 不执行。
- 第二轮“学习”引用 pending target。
- 第三轮补齐必要信息后学习成功并沉淀 LearnedPath。
- 第四轮执行同 target 已学 action。
- 浏览器可见进度符合 M11.3.1。
- History detail 显示 Intake / Router / Orchestrator / skill trace，敏感信息脱敏。

未真实跑 manual smoke 前，review 必须写 `manual smoke not run`。
