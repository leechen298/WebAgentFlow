# Plan

状态：proposed（docs generated, implementation not started）

## 阶段 0：文档收口

- 重命名 11.3.5：从 Chat Context Recovery UX 扩展为 Customer-Facing Agent Router
  & Capability Runtime。
- 更新 M11 index / m11-plan。
- 更新 product-model 中英文镜像。
- 更新 roadmap 中英文镜像。
- 更新 `docs/user-guide/wagent-chat.md`，把 11.3.5 写成计划能力，不写成当前可用。

验证：

```bash
git diff --check
```

## 阶段 1：Schema 和 Registry

- 新增 Router decision schema。
- 新增 Page Understanding result schema。
- 新增 Capability Registry 定义。
- 为每个 capability 定义：
  - name
  - input contract
  - output contract
  - preconditions
  - risk hints
  - executor owner

## 阶段 1.5：Prompt Asset Registry

- 新增 `apps/api/app/prompts/` 目录。
- 新增 prompt registry 和 prompt metadata 格式。
- 为 Conversation Intake Agent、Customer-Facing Agent Router、Page Understanding Agent、
  Learning Agent、Web Operation Agent、Task Result Reporter 建立独立 prompt asset 目录。
- 新增 shared prompt fragments：产品边界、证据边界、脱敏规则、结构化输出规则。
- 新增 prompt loader，只允许代码按 prompt id / version 加载 prompt。
- LLM trace 记录 prompt id、version、hash、schema 和 redaction 状态。
- 禁止在 service 函数里硬编码大段 Agent prompt。

## 阶段 2：Context Collector

- 收集 recent messages。
- 收集 `pending_intake`、`pending_target`、`last_no_path_reason`。
- 收集 learned_actions summary，并按 target scope 分组。
- 收集最近 URL / last no-path target。
- 输出 redacted context bundle。

## 阶段 3：Router Agent

- 新增 `CustomerFacingAgentRouterService`。
- 支持 LLM-backed provider、fake provider、deterministic fallback。
- 输出 schema-constrained route decision。
- provider / schema / confidence 失败时只允许 ask / unknown，不触发 learning / replay。

## 阶段 4：Page Context and Page Understanding

- 新增 PageContextBuilder。
- 复用 HTML AST、Simplified AST、PageAnalysis、page signature。
- 新增 PageUnderstandingService。
- 第一版可用 fake / deterministic provider；真实 LLM smoke 单独记录。

## 阶段 5：Capability Runtime

- 实现 registry lookup 和 precondition check。
- 接入：
  - collect_conversation_context
  - inspect_target_page
  - understand_page
  - lookup_learned_actions
  - ask_user_for_missing_info
  - start_learning
  - start_replay
  - learn_then_execute
  - record_progress_event
  - record_agent_trace

## 阶段 6：Worker Agent Runtime

- Learning Agent 组织 `start_learning`。
- Web Operation Agent 组织 `lookup_learned_actions` / `start_replay` /
  `learn_then_execute`。
- Result Reporter 统一生成用户可读结果。

第一版可将 runtime 逻辑放在 conversation service 包内，不强制拆成独立进程或复杂
Agent framework。

## 阶段 7：Chat Runtime Integration

- FREE_TEXT 先 collect context。
- Intake result + context 进入 Router。
- Orchestrator 校验 route decision。
- 通过 Capability Runtime 调用能力。
- 记录 progress、trace、provenance。
- 非 `interactive_chat` 保持原 workflow。

## 阶段 8：Console / CLI UX

- CLI 增加中性 loading。
- 明确 learning / execution 后才输出具体“打开浏览器学习 / 执行”。
- History detail 展示 Router / Worker / capability trace。
- History list 时间显示当前系统时区 `YYYY-MM-DD HH:mm:ss`。

## 阶段 9：验证

建议最小验证：

```bash
cd apps/api
../../.venv/bin/python -m pytest tests/test_conversation_intake.py tests/test_conversation_chat_runtime.py -q
../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py tests/test_conversation_capabilities.py -q
../../.venv/bin/python -m ruff check app/services/conversation app/schemas tests/test_conversation_router_agent.py tests/test_conversation_capabilities.py

cd ../cli
../../.venv/bin/python -m pytest tests/test_chat.py -q

cd ../..
git diff --check
```

Console 变更后补：

```bash
pnpm --filter @web-agent-flow/console test -- ConversationHistoryDetailPage
```

真实 manual smoke 需单独记录 session_id、learned_path_id、trace evidence。
