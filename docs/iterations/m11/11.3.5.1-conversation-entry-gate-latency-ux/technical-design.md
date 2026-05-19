# 技术设计（Technical Design）

状态：ready_for_implementation

## 当前状态（Current State）

当前 `wagent chat` 在用户提交消息后会打印一次中性进度文案，例如
`正在理解你的需求。`，然后等待 `/dispatch` 返回。这个行为不是持续 loading，也不会展示
当前阶段或 spinner。简单非网页输入仍可能进入 Conversation Intake Agent 和
Customer-Facing Agent Router 两层 LLM，造成不必要的延迟和不稳定回复。

11.3.5 已引入 Context Collector、Router、Skill Runtime、Prompt Asset 和 trace 机制。
11.3.5.1 应复用这些基础设施，不改 Router / Skill Runtime 主结构。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Entry Gate 位于 Intake 前 | `ChatRuntime.try_handle()` 在构造 intake 前调用 entry gate service | GATE-1 / CHAT-1 | 只作用于 `interactive_chat` |
| 非网页任务跳过 Intake / Router | Entry Gate result `requires_agent_runtime=false` 时直接生成 Orchestrator reply | CHAT-2 / TRACE-1 | 不触发 learning / replay |
| 网页任务进入 11.3.5 runtime | `requires_agent_runtime=true` 时继续现有 Intake + Router flow | CHAT-3 | 不改变 Router contract |
| provider / schema 失败不得执行 | Entry Gate failure maps to ask / clarify response | NEG-1 / NEG-2 | fail closed |
| Entry Gate 有硬超时 | provider call wrapped by timeout budget, then fallback | NEG-3 | target <=1500ms, hard cap <=2000ms |
| CLI 持续 working 状态 | CLI dispatch wait loop 显示 spinner 或周期性 status | CLI-1 / CLI-2 | progress 不是正式 reply |
| trace 可审计 | conversation event / history read model 增加 entry gate trace | TRACE-1 | redacted only |
| 不保存 provider thinking | trace sanitizer drops thinking / CoT fields and `<think>` blocks | TRACE-2 | history never shows CoT |

## 实现方案（Proposed Implementation）

### 新增 schema

建议新增：

```text
apps/api/app/schemas/conversation_entry_gate.py
```

核心类型：

- `ConversationEntryGateCategory`
- `ConversationEntryGateResult`
- `ConversationEntryGateTrace`

`ConversationEntryGateResult` 至少包含：

- `category`
- `requires_agent_runtime`
- `confidence`
- `reply_hint`
- `reason_summary`
- `latency_ms`
- `provider`
- `model`
- `fallback`

### 新增 service

建议新增：

```text
apps/api/app/services/conversation/entry_gate.py
```

职责：

- 构造轻量 prompt input。
- 调用低延迟非 thinking provider。
- 校验 schema。
- 处理 malformed JSON / provider error / timeout / low confidence。
- 输出 `ConversationEntryGateResult`。
- 返回 redacted trace metadata。

provider 调用必须包在明确 timeout budget 中：

- 默认目标 `<= 1500ms`。
- 绝对上限 `<= 2000ms`。
- 超时即返回 friendly fallback / clarification，不再等待慢调用补结果。
- timeout path 记录 `error_kind=timeout` 和 elapsed time，但不触发 Intake / Router / learning / replay。

Entry Gate prompt 应作为 prompt asset 存放：

```text
apps/api/app/prompts/agents/conversation_entry_gate/
  prompt.md
  metadata.toml
```

并登记到：

```text
apps/api/app/prompts/registry.toml
```

prompt 约束：

- 只判断是否进入网页任务 runtime。
- 不输出 intent parsing 细节。
- 不输出 selector / step / skill call。
- 不输出 chain-of-thought。
- 不包含页面或测试站特例。

trace sanitizer 必须在 history 持久化前丢弃 provider thinking / CoT：

- 删除 `<think>...</think>`。
- 删除 `thinking`、`reasoning`、`reasoning_content`、`chain_of_thought` 等字段。
- 只保留短 `reason_summary` 和结构化 metadata。

### Chat runtime 集成

在 interactive chat flow 中：

```text
用户消息
-> collect minimal context for gate
-> Entry Gate
-> if requires_agent_runtime=false: Orchestrator reply + trace
-> if requires_agent_runtime=true: existing 11.3.5 Intake + Router flow
```

Entry Gate 不应替代 Context Collector。它只需要最小上下文：

- current user message
- session mode
- pending target exists?
- pending intake exists?
- last no-path reason exists?

如果实现发现需要完整 context bundle，应记录为后续优化，不在 11.3.5.1 首版扩大。

非网页任务的用户可见回复由 Orchestrator 生成，不直接信任 provider 的原文。
回复应短、快、友好，并把用户引导回 WebAgentFlow 的核心用法：提供 URL、学习页面操作、
执行已学操作或查看调试历史。

### CLI working indicator

修改：

```text
apps/cli/wagent/chat.py
```

交互参考：

- 参考 Codex CLI / Claude Code CLI 的 agentic CLI 等待体验。
- 不复制具体视觉样式；实现应选择适合当前终端和测试环境的最小 spinner / status loop。
- 工作状态应让用户明确知道请求仍在处理，而不是 CLI 卡住。

建议行为：

- 用户输入后，CLI 启动 dispatch request。
- 请求等待期间，显示 spinner：
  - `WAgent · 正在理解你的需求 ...`
  - 或同等低噪音动态状态。
- API 返回后停止 spinner，清理当前行，再输出正式 `WAgent > ...` 回复。
- 如果 stdout 不是 TTY，使用单行或周期性文本，不输出控制字符。
- Ctrl-C 时恢复光标 / 清理行。
- 如果 API / event 能提供阶段，允许把 spinner label 从“正在理解”切到“正在判断下一步”、
  “正在准备回复”等；没有阶段事件时不编造内部阶段。

CLI 不需要知道每个内部 Agent 阶段；真实阶段信息仍来自 API progress / event。
11.3.5.1 的最低要求是“等待期间可感知”，不是完整 streaming。

### History / trace 集成

在 conversation event / history read model 中加入：

- `entry_gate_recorded`
- `entry_gate.category`
- `entry_gate.requires_agent_runtime`
- `entry_gate.skipped_intake_router`
- `entry_gate.latency_ms`
- `entry_gate.provider`
- `entry_gate.model`
- `entry_gate.fallback`
- `entry_gate.error_kind`
- `entry_gate.timeout_ms`

History raw record 也必须经过同样 redaction，不得在 raw trace 中保留 provider thinking。

如果 `requires_agent_runtime=false`，最终回复 provenance 应能标识为：

```text
entry_gate + orchestrator_code
```

或等价的混合来源。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 不新增路由 | `/dispatch` 内部行为变化 |
| API response schema | Maybe | History detail 可增加 trace 字段 | 旧记录缺字段应兼容 |
| Database schema / migration | Maybe | 优先使用现有 event metadata | 如新增字段需 migration |
| CLI | Yes | 新增持续 working indicator | 非 TTY fallback |
| Console UI | Maybe | History detail 展示 Entry Gate trace | 旧数据显示未记录 |
| Conversation events | Yes | 新增 entry gate trace event | conversation evidence only |
| Replay execution | No | 不改 replay | Entry Gate 不触发 replay |
| Reporter | No | 不改 Task Result Reporter | 非网页回复由 Orchestrator 统一生成 |
| Worker / async jobs | No | 不涉及 worker |  |
| Tests / fixtures | Yes | 新增 API/CLI/history tests | 不跑 live run |
| Docs | Yes | 本迭代文档 |  |

## 失败 / 边界情况

- provider timeout：返回 clarify / friendly fallback，不触发 learning / replay。
- provider sleep 超过 timeout budget：测试必须证明不会等待到慢调用完成。
- malformed JSON：记录 parse failure，不触发 learning / replay。
- schema validation failure：记录 schema failure，不触发 learning / replay。
- low confidence：追问或友好说明，不触发 learning / replay。
- non-web chat：快速引导回 WebAgentFlow 使用场景，不进入开放式闲聊。
- false negative：如果用户输入包含明确 URL、学习、执行、页面操作信号却被 gate 拦住，测试应失败。
- false positive：普通非网页消息进入重型 runtime 是性能回归，但不应触发 learning / replay。
- CLI interrupted：spinner 必须清理。

## 非目标（Non-goals）

- 不做 streaming API。
- 不做完整终端 TUI。
- 不做 active browser tab。
- 不做完整闲聊系统。
- 不做正式 risk / consent policy。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Entry Gate unit | schema、category、failure handling | `test-plan.md` GATE |
| Chat runtime integration | non-web skips heavy runtime, web task enters runtime | `test-plan.md` CHAT |
| CLI UX | spinner / non-TTY fallback / interrupt cleanup | `test-plan.md` CLI |
| History trace | entry gate trace + provenance | `test-plan.md` TRACE |
| Regression | 11.3.5 web task still works | `test-plan.md` REG |

## 验证命令入口（Validation Commands）

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_entry_gate.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_chat.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation app/schemas tests/test_conversation_entry_gate.py tests/test_conversation_chat_runtime.py tests/test_conversation_api.py
git diff --check
```
