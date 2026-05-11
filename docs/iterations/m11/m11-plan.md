# M11 全量计划

## 目标

M11 是 Runtime Loop Foundation。它从 M10 已完成的 LearnedPath 路径资产、
catalog、显式 replay 和 drift detection 出发，建立用户与 WebAgentFlow
沟通的运行时闭环。

M11.0 建立 Runtime Conversation Shell 和 Conversation Orchestrator /
Dispatcher 骨架。M11.1 才进入 Task-to-Path Planning & Execution MVP。

M11 不是 L1 autonomous learning，也不允许 LLM 逐步控制浏览器。用户始终
和 WebAgentFlow 沟通；内部 Agent、engine event 和 replay execution 都由
代码侧 session controller / agent router 管理边界。

## 权威输入

- `AGENTS.md`
- `docs/product-model.md`
- `docs/roadmap.md`
- `docs/scope-boundaries.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/intent.md`
- `docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/plan.md`

## M11.0 拆分原则

- `11.0-runtime-conversation-shell-orchestration/` 是 M11.0 总纲目录，不是
  一次性施工包。
- M11.0 的具体实现必须拆成 `11.0.x-*` 执行包。
- 每个 `11.0.x` 都必须有 `intent.md`、`plan.md`、`review.md`。
- 每次只实现当前执行包，完成后更新当前包的 `review.md`。
- 不顺手实现 M11.1、M12、M13 或更后续能力。
- 不调用 autonomous run，不依赖 LLM provider，不让 LLM 逐步控制浏览器。

## M11.0 执行包拆分

### 11.0.1 · Conversation domain contract

状态：完成。

目标：

- 定义 conversation session、message、event、command、state transition
  的领域 contract。
- 定义 slash command parser 的输入输出 contract。
- 先稳定纯 schema、parser、state transition 语义。

预期触及：

- `apps/api/app/schemas/conversation.py` planned。
- `apps/api/app/services/conversation/commands.py` planned。
- `apps/api/app/services/conversation/state.py` planned。
- `apps/api/tests/test_conversation_commands.py` planned。
- `apps/api/tests/test_conversation_state.py` planned。

边界：

- 不做 persistence。
- 不做 API。
- 不做 CLI。
- 不做 orchestrator side effects。
- 不做 replay hook。
- 不做 Agent D / E / F / G / H。

交付：

- `apps/api/app/schemas/conversation.py`
- `apps/api/app/services/conversation/commands.py`
- `apps/api/app/services/conversation/state.py`
- `apps/api/tests/test_conversation_commands.py`
- `apps/api/tests/test_conversation_state.py`

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_commands.py tests/test_conversation_state.py`
- 结果：`29 passed`

### 11.0.2 · Conversation session store

状态：完成。

目标：

- 实现 conversation session / message / event 的持久化存储。
- 以 11.0.1 的 schema contract 为基础，不改变 command parser 和 state
  transition contract。
- 为后续 11.0.3 API、11.0.4 CLI、11.0.5 orchestrator 提供可审计会话数据。
- 推荐方向：DB-backed store，而不是 JSON / event log。原因是后续 API 查询、
  CLI session lifecycle、audit、history 和 E2E 都需要稳定查询能力。

预期触及：

- `apps/api/app/models/conversation.py` 或等价 ORM model 文件。
- `apps/api/app/repos/conversation_repo.py`。
- Alembic migration。
- `apps/api/tests/test_conversation_repo.py`。
- 可能需要轻量调整 `apps/api/app/schemas/conversation.py`，但不能改变 11.0.1
  已定的核心 enum / command contract。

边界：

- 不做 API endpoint。
- 不做 CLI。
- 不做 orchestrator side effects。
- 不调用 replay API。
- 不做 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不加 user / account / tenant 字段。

交付：

- `apps/api/app/models/conversation.py`
- `apps/api/app/repos/conversation_repo.py`
- `apps/api/alembic/versions/a93d26f33594_add_conversation_tables.py`
- `apps/api/tests/test_conversation_repo.py`
- `docs/iterations/m11/11.0.2-conversation-session-store/review.md`

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v`
- 结果：`61 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/models/conversation.py app/repos/conversation_repo.py app/models/__init__.py tests/test_conversation_repo.py alembic/versions/a93d26f33594_add_conversation_tables.py`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/alembic -c alembic.ini heads`
- 结果：`a93d26f33594 (head)`

### 11.0.3 · Conversation API

状态：完成。

目标：

- 把 11.0.2 的 session / message / event store 暴露为最小 HTTP API
  contract。
- 支持 session create / read。
- 支持 append / read messages。
- 支持 append / read events。
- 支持 read transcript。
- API 对外保持 WebAgentFlow 视角，不直接暴露 internal Agent。

边界：

- 不做 CLI。
- 不做 natural-language planning。
- 不做 orchestrator dispatcher。
- 不做 replay hook 或 `/replay` side effect。
- 不做 Agent D / E / F / G / H。
- 不做 task-to-path planning。
- 不做 slot binding。
- 不加入 user / account / tenant 字段。

交付：

- `apps/api/app/routers/conversation.py`
- `apps/api/tests/test_conversation_api.py`
- `apps/api/app/schemas/conversation.py` (API schema 补充)
- `apps/api/app/routers/__init__.py` (router 注册)

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v`
- 结果：`84 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/routers/conversation.py app/schemas/conversation.py app/routers/__init__.py tests/test_conversation_api.py`
- 结果：`All checks passed!`
- `git diff --check`
- 结果：clean

### 11.0.4 · Runtime CLI shell

状态：完成。

目标：

- 在 `apps/cli/` 中实现 `wagent conversation` runtime conversation 入口。
- 让用户可以通过 CLI 创建 conversation session、追加 user message、读取
  session status、查看 messages / transcript / events。
- CLI 必须通过 HTTP 调用 11.0.3 Conversation API，不直接操作 DB。
- CLI 必须区别于当前 `wagent verify` / `verify-scenario`。
- CLI 仍然不做 orchestrator side effects，不调用 replay，不做 task-to-path。
- 首版只实现非交互命令，不把 REPL / interactive loop 列为验收项。

边界：

- 不做 orchestrator dispatcher。
- 不调用 replay API。
- 不实现 `/replay` command side effect。
- 不做 Agent D / E / F / G / H。
- 不做 natural-language planning。
- 不做 slot binding。
- 不调用 autonomous run。
- 不依赖 LLM provider。
- 不做 M16 external CLI stabilization。
- 不加入 user / account / tenant 字段。

交付：

- `apps/cli/wagent/conversation.py`
- `apps/cli/tests/test_conversation.py`
- `apps/cli/wagent/main.py` (router 注册)

验证：

- `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v`
- 结果：`67 passed`
- `cd apps/cli && ../../.venv/bin/ruff check wagent/main.py wagent/conversation.py tests/test_conversation.py`
- 结果：`All checks passed!`

### 11.0.5 · Orchestrator dispatcher

状态：当前规划 / 下一步执行包。

目标：

- 实现 Conversation Orchestrator / Dispatcher 的纯调度骨架。
- 接收 user message / slash command / engine event。
- 复用 11.0.1 的 command parser 和 state transition contract。
- 复用 11.0.2 的 session / message / event store。
- 为每次用户输入生成 parsed command、state transition、user-facing
  response 和 audit event。
- 不执行 replay side effect。
- 不实现 Agent D / E / F / G / H。
- 不新增 CLI 命令。
- 不做 task-to-path planning。

边界：

- 不做 replay hook；explicit replay hook 属于 11.0.6。
- 不调用 replay API。
- 不调用 autonomous run。
- 不做 natural-language planning。
- 不做 slot binding。
- 不做 Agent routing implementation。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 E2E。

预期触及：

- `apps/api/app/services/conversation/orchestrator.py` 或等价 dispatcher module。
- `apps/api/app/services/conversation/__init__.py`。
- `apps/api/tests/test_conversation_orchestrator.py`。
- 可能小幅复用 `apps/api/app/services/conversation/commands.py` 和
  `apps/api/app/services/conversation/state.py`。
- 可能小幅使用 `apps/api/app/repos/conversation_repo.py`。
- 不改 11.0.3 API endpoint contract，除非后续实现阶段明确需要最小 endpoint
  hook；本轮文档不实现。

### 11.0.6 · Explicit replay command hook

状态：future。

目标：

- `/replay <learned_path_id> <url>` 通过 orchestrator 显式调用 M10 replay。
- 作为 M11.0 smoke hook，验证 runtime loop 能触发一个已完成的确定性能力。

边界：

- 不做 path selection。
- 不做 slot binding。
- 不改 M10 replay contract。

### 11.0.7 · Conversation tests and evidence

状态：future。

目标：

- 建立 conversation 测试域。
- 覆盖 API、CLI、orchestrator 和必要的 E2E smoke。
- 形成可审计测试证据。

边界：

- 不依赖 LLM provider。
- 不调用 autonomous run。

## M11.1 placeholder

M11.1 Task-to-Path Planning & Execution MVP 是 future。它会在 M11.0 runtime
loop 基础上接入 Agent D / E、LearnedPath retrieval / ranking、slot binding、
pre-execution confirmation、task result verification MVP 和 basic artifact
capture。

本轮不展开 M11.1 详情目录。等 M11.0 完成后，再创建
`11.1-task-to-path-planning-execution/` 的 intent / plan / review。

## 执行规则

- 开始每个 `11.0.x` 前必须阅读 `AGENTS.md`、`docs/product-model.md`、
  `docs/iterations/m11/m11-plan.md`、M11.0 总纲和当前执行包的
  `intent.md` / `plan.md`。
- 每次只实现当前包。
- 不调用 `/exploration/autonomous-runs` 或
  `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 不依赖 LLM provider。
- 不引入路线图外产品外壳、身份管理、托管数据或外部通道规划。
- 每个包完成后更新自己的 `review.md`，记录实际交付、验证命令、范围偏差和
  后续风险。
