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
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。

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
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
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
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
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
- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
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

状态：完成。

目标：

- 实现 Conversation Orchestrator / Dispatcher 的纯调度骨架。
- 接收 user message / slash command / engine event。
- 复用 11.0.1 的 command parser 和 state transition contract。
- 复用 11.0.2 的 session / message / event store。
- 为每次用户输入生成 parsed command、state transition、user-facing
  response 和 audit event。
- 不执行 replay side effect。
- 不实现 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
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

交付：

- `apps/api/app/services/conversation/orchestrator.py`
- `apps/api/app/services/conversation/__init__.py`
- `apps/api/tests/test_conversation_orchestrator.py`

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_orchestrator.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_conversation_api.py -v`
- 结果：`101 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/conversation/orchestrator.py app/services/conversation/__init__.py tests/test_conversation_orchestrator.py`
- 结果：`All checks passed!`
- `git diff --check`
- 结果：clean

### 11.0.6 · Explicit replay command hook

状态：完成。

目标：

- 将显式 `/replay <learned_path_id> <url>` command 接入 M10 replay
  capability。
- 复用 11.0.5 `ConversationOrchestrator` 的 dispatcher flow。
- 只允许使用用户显式给出的 `learned_path_id + url`。
- 不做 LearnedPath selection。
- 不做 slot binding。
- 不做 task-to-path planning。
- 不调用 autonomous run。
- 不包装成 `pass_gate` 或 Supervisor verdict。
- 将 replay result 作为 conversation event / dispatch response 的一部分返回
  和审计。

边界：

- 不做 Task Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、Failure Recovery Agent / 失败恢复助手、User Abort Handler / 用户中断处理器、Teaching Guide Agent / 教学引导器（legacy: Agents D-H）。
- 不做 path selection。
- 不做 natural-language task planning。
- 不做 slot binding。
- 不做 recovery / abort dialogue。
- 不做 teaching mode。
- 不做 multi-page workflow。
- 不做 artifact lifecycle。
- 不做 risk gate。
- 不改 M10 replay contract。
- 不新增 M11.1 目录。
- 不新增 E2E，本包只规划 service / API / CLI-level tests；conversation E2E
  归 11.0.7。

交付：

- `apps/api/app/services/conversation/orchestrator.py`
- `apps/api/app/services/conversation/replay_hook.py`
- `apps/api/app/routers/conversation.py`
- `apps/api/app/schemas/conversation.py`
- `apps/cli/wagent/conversation.py`
- `apps/api/tests/test_conversation_replay_hook.py`
- `apps/api/tests/test_conversation_api.py`
- `apps/cli/tests/test_conversation.py`

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_replay_hook.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_learned_path_replay.py tests/test_exploration_learned_paths_api.py -v`
- 结果：`179 passed`
- `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v`
- 结果：`67 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/conversation/orchestrator.py app/services/conversation/replay_hook.py app/routers/conversation.py app/schemas/conversation.py tests/test_conversation_replay_hook.py tests/test_conversation_api.py`
- 结果：`All checks passed!`
- `git diff --check`
- 结果：clean

### 11.0.7 · Conversation tests and evidence

状态：完成。

目标：

- 建立 conversation 测试域。
- 覆盖 API、CLI、orchestrator 和必要的 E2E smoke。
- 形成可审计测试证据。

边界：

- 不依赖 LLM provider。
- 不调用 autonomous run。

交付：

- `apps/e2e/tests/conversation/runtime.spec.ts`
- `docs/testing/results/2026-05-11-replay-e2e-rerun.md`
- `docs/testing/results/2026-05-11-conversation-baseline.md`
- `docs/testing/results/2026-05-11-conversation-runtime-e2e.md`
- `docs/testing/live-smoke.md`
- `docs/testing/README.md`
- `docs/testing/e2e.md`
- `docs/testing/features/conversation.md`
- `docs/testing/current-testing-backlog.md`
- `docs/testing/full-test-matrix.md`
- `apps/e2e/README.md`

验证：

- `curl -sS -i http://127.0.0.1:8001/health`
- 结果：HTTP 200，database ok
- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_replay_hook.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_learned_path_replay.py tests/test_exploration_learned_paths_api.py -v`
- 结果：`179 passed`
- `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -v`
- 结果：`15 passed`
- `pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/runtime.spec.ts`
- 结果：`1 passed`
- `pnpm run test:e2e`
- 结果：`10 passed`
- `git diff --check`
- 结果：clean

## M11.0 closure

M11.0 Runtime Conversation Shell & Agent Orchestration 已完成到 11.0.7。

已实现：

- conversation domain contract
- DB-backed session / message / event store
- Conversation API
- runtime CLI shell
- Orchestrator Dispatcher
- explicit replay command hook
- conversation runtime tests and evidence

M11.0 建立了 runtime loop 基座，但仍未实现 task-to-path planning、Task
Path Planner / 任务路径规划器、Task Result Reporter / 任务结果汇报器、
slot binding 或 task result verification。M11.0 的最后一个功能
连接点是显式 `/replay <learned_path_id> <url>`：它只使用用户给出的 path id
和 URL，不做 path selection、不做 task planning、不做 slot binding。

## M11.1 · Task-to-Path Planning & Execution MVP

M11.1 是第一个 L3 Actual Work MVP。用户通过 M11.0 conversation surface
提交任务；WebAgentFlow 需要从 LearnedPath catalog 中检索候选路径、选择
路径、绑定参数、请求确认、执行 replay、验证结果、汇报结果。

M11.1 引入 / 具体化 Task Path Planner / 任务路径规划器和 Task Result
Reporter / 任务结果汇报器（legacy: Agent D / E）。

- Task Path Planner 不能读 raw HTML，不能逐步控制浏览器，只能基于 user task、
  LearnedPath catalog、negative / replay evidence、available route
  candidates 输出规划。
- Task Result Reporter 不得脑补成功，只能基于 replay result、postcondition check、
  artifact status、final-state signal、uncertainty flags 汇报。

## M11.1 拆分原则

- M11.1 不能一次性实现。
- 每个 `11.1.x` 都必须有 `README.md`、`intent.md`、`plan.md`、`review.md`。
- 每次只实现当前包。
- 不顺手实现 M12 recovery / M13 teaching / M17 multi-page workflow。
- 不调用 autonomous run。
- 不让 LLM 逐步控制浏览器。
- 不做 hidden relearning。
- 所有 execution 必须通过已有 deterministic replay / later explicit
  execution service。
- 当前阶段不新增 PC App、账号体系、云端数据、消息通道。

## M11.1 执行包拆分

### 11.1.1 · Task planning domain contract

状态：已完成。

交付：

- `apps/api/app/schemas/task_planning.py` — 17 个 schema 定义：
  `TaskInput`, `TaskIntent`, `LearnedPathCandidate`, `RoutePlan`, `RouteStep`,
  `SlotBindingProposal`, `ConfirmationRequirement`, `RiskHint`,
  `ConsentRequirement`, `PostconditionSignal`, `TaskExecutionResult`,
  `ArtifactReference`, `AgentDPlannerInput/Output`, `AgentEReporterInput/Output`。
- `apps/api/tests/test_task_planning_schemas.py` — 33 tests passed，ruff clean。
- `TrustLevel = Literal["provisional", "confirmed", "flaky", "deprecated"]`
  校验 `LearnedPathCandidate.trust`。
- `Severity` / `ArtifactStatus` literals、`raw_text` / `hit_count` /
  `RouteStep.order` 基础约束。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_schemas.py -v`
- 结果：`33 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/schemas/task_planning.py tests/test_task_planning_schemas.py`
- 结果：`All checks passed!`
- `git diff --check`
- 结果：clean

边界（已遵守）：

- 不做 retrieval / ranking 实现。
- 不做 Task Path Planner 实现。
- 不做 Task Result Reporter 实现。
- 不做 slot binding 实现。
- 不做 replay execution。
- 不做 risk gate implementation。
- 不做 artifact lifecycle。
- 不做 E2E。

### 11.1.2 · LearnedPath retrieval and ranking

状态：已完成。

交付：

- `apps/api/app/services/task_planning/retrieval.py` — deterministic retrieval /
  ranking service (`LearnedPathRetrievalService`)。
  - 输入：`TaskIntent`；输出：`list[LearnedPathCandidate]`。
  - 默认排除 `trust=deprecated`；包含 confirmed / provisional / flaky。
  - 评分维度：exact scenario match (+50)、page_template exact/contains match
    (+30/+15)、trust base (confirmed +20 / provisional +10 / flaky 0)、
    hit_count capped at +10、keyword token overlap (+2 per token)。
  - `match_reasons` / `warnings` 可解释；score 为内部实现细节，不暴露为 public
    `LearnedPathCandidate` 字段。
  - `limit` 默认 10，clamp 至 `[1, 50]`。
  - `drift_evidence_summary` 保守地从 `trust_reason` 填充；
    `negative_evidence_summary` 11.1.2 留空。
- `apps/api/app/services/task_planning/__init__.py` — export `LearnedPathRetrievalService`。
- `apps/api/app/repos/learned_paths_repo.py` — 新增只读 `list_candidates()`，
  返回所有 non-deprecated LearnedPaths。
- `apps/api/tests/test_task_planning_retrieval.py` — 38 tests passed，ruff clean。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_retrieval.py tests/test_task_planning_schemas.py -v`
- 结果：`71 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/task_planning/retrieval.py app/services/task_planning/__init__.py tests/test_task_planning_retrieval.py`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/pytest -v` (full suite)
- 结果：`918 passed, 65 skipped`
- `git diff --check`
- 结果：clean

边界（已遵守）：

- 不调用 Task Path Planner。
- 不调用 LLM。
- 不执行 replay。
- 不调用 autonomous run。
- 不做 slot binding。
- 不生成 route plan。
- 不做 confirmation gate。
- 不读取 raw HTML。
- 不做 hidden relearning。
- 不做 E2E。
- 不加入 user / account / tenant 字段。

### 11.1.3 · Task Path Planner MVP

状态：已完成。

目标：

- 设计并实现 Task Path Planner MVP 的服务边界。
- 消费 `TaskInput` / `TaskIntent` 和 ranked `LearnedPathCandidate` 列表，
  输出 `AgentDPlannerOutput`。
- 将选中的 LearnedPath candidate 映射为最小可解释 `RoutePlan`。
- 定义 no candidate / ambiguous candidate / risky candidate / flaky candidate
  的 planning semantics。
- 保留 retrieval `match_reasons` / `warnings` / confirmation requirements，
  供后续 confirmation、execution、reporting 和 recovery 使用。

交付：

- `apps/api/app/services/task_planning/planner.py` — `TaskPathPlanner` 服务。
  - 输入：`TaskIntent` + `list[LearnedPathCandidate]`（已排序）。
  - 输出：`AgentDPlannerOutput`。
  - 防御性过滤 `deprecated` 候选。
  - 无候选时返回 unable-to-plan（`route_plan=None` + `blocking` confirmation requirement）。
  - `confirmed` 候选直接生成最小 RoutePlan。
  - `provisional` 候选生成 RoutePlan 并附加 `warning` 级别 confirmation requirement。
  - `flaky` 候选生成 RoutePlan，附加 `flaky_path` risk hint 和 confirmation requirement。
  - 模糊检测：top 2 候选均为 `confirmed` 且 second 有 strong match signal 时，
    标记 ambiguous 并附加 confirmation requirement。
  - Drift evidence 和 negative evidence 传播到 warnings / risk hints。
  - RoutePlan 包含单个 `RouteStep`，引用 `learned_path_id`，purpose 从 task + candidate 派生。
  - `bound_slots={}`（Slot Binding 为 future scope）。
- `apps/api/app/services/task_planning/__init__.py` — 导出 `TaskPathPlanner`。
- `apps/api/tests/test_task_path_planner.py` — 21 tests passed，ruff clean。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_path_planner.py tests/test_task_planning_retrieval.py tests/test_task_planning_schemas.py -v`
- 结果：`92 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/task_planning/planner.py app/services/task_planning/__init__.py tests/test_task_path_planner.py`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/pytest -v` (full suite)
- 结果：`947 passed, 65 skipped`
- `git diff --check`
- 结果：clean

边界（已遵守）：

- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不做 hidden relearning。
- 不接入 LLM provider。
- 不调用 retrieval service（核心方法直接接收候选列表）。
- 不引入 replay / autonomous / LLM / raw HTML / CLI imports。
- 不新增 CLI command 或 API endpoint。
- 不做真实 slot binding / form filling / result verification / recovery
  dialogue / teaching mode。
- 不创建 11.1.4 详情目录。

### 11.1.4 · Task Planning Dispatch Preview

状态：已完成。

目标：

- 将 ordinary task request 接入 conversation runtime planning preview 路径。
- 区分普通用户任务和显式 `/replay <learned_path_id> <url>` command。
- 用 deterministic / minimal 方式构造 `TaskIntent`（仅 `raw_text`）。
- 串联 11.1.2 retrieval / ranking 和 11.1.3 Task Path Planner，保持职责分层。
- 将 planner output 作为 conversation assistant message / event 预览输出。
- 保留 warnings / risk_hints / match_reasons / confirmation requirements。
- no candidates 时返回 unable-to-plan，不自动学习、不 hidden relearning。

交付：

- `apps/api/app/schemas/conversation.py` — 新增 `PLAN_PREVIEW_PROPOSED`、
  `PLAN_PREVIEW_UNABLE` event types。
- `apps/api/app/services/task_planning/preview.py` — `PlanningPreviewResult` +
  `PlanningPreviewService`。封装 `TaskIntent` 构造、retrieval、planner 调用、
  用户消息格式化、event payload 构建。
- `apps/api/app/services/conversation/orchestrator.py` — 新增可选
  `planning_handler` 参数。FREE_TEXT dispatch 时若 handler 存在：
  - 调用 handler 生成 preview
  - 追加 agent assistant message
  - 追加 preview event
  - confirmation_required 时状态过渡到 `awaiting_confirmation`
  - 覆盖 `user_response`
  - backward compatible（handler=None 时行为不变）
- `apps/api/app/services/task_planning/__init__.py` — 导出 preview 类型。
- `apps/api/tests/test_task_planning_preview.py` — 9 tests。
- `apps/api/tests/test_conversation_orchestrator.py` — 新增 5 个 planning preview
  集成测试。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_preview.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py -v`
- 结果：`64 passed`
- `cd apps/api && ../../.venv/bin/ruff check app/services/task_planning/preview.py app/services/task_planning/__init__.py app/services/conversation/orchestrator.py app/schemas/conversation.py app/routers/conversation.py tests/test_task_planning_preview.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/pytest -q`
- 结果：`962 passed, 65 skipped`
- `git diff --check`
- 结果：clean

边界（已遵守）：

- 不新增 API endpoint（复用现有 `/conversation/sessions/{id}/dispatch`）。
- 不新增 CLI command。
- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不做 slot binding / form filling。
- 不做 result verification / recovery / teaching。
- 11.1.4 实现阶段未创建 11.1.5 详情目录。

### 11.1.5 · Plan Confirmation and Consent Gate

状态：已完成。

目标：

- 实现 `awaiting_confirmation` 下用户输入如何转成 explicit decision。
- 处理 confirm / cancel / reject / clarification / new task intent。
- 支持 slash decision commands：`/confirm`、`/cancel`、`/abort`、`/stop`、
  `/reject`。
- 只记录 consent / cancellation / rejection / clarification intent。
- 不执行 replay，不调用 autonomous run，不做 result verification。
- 确保 ambiguous input 不会被当成 consent。
- 明确 high-risk / flaky / provisional plan 即使被确认，也只是记录 consent
  或 ready-for-execution 语义。

交付：

- `apps/api/app/schemas/conversation.py`
  - 新增 `ConversationStatus.PLAN_CONFIRMED`。
  - 新增 `PLAN_CONFIRMED`、`PLAN_CANCELLED`、`PLAN_REJECTED`、
    `CONFIRMATION_CLARIFICATION_REQUESTED`、
    `EXPLICIT_REPLAY_BLOCKED_BY_PENDING_CONFIRMATION` event types。
- `apps/api/app/services/conversation/confirmation.py`
  - 新增 `PlanConfirmationService` deterministic keyword classifier。
  - 支持 confirm / cancel / reject / ambiguous，以及 slash decision commands。
- `apps/api/app/services/conversation/orchestrator.py`
  - 在 `awaiting_confirmation` 下优先进入 confirmation gate。
  - FREE_TEXT 和 slash decision commands 由 gate 处理。
  - `/replay` 在 pending preview 时被阻断，不调用 replay handler。
  - 其他 slash commands 继续走现有状态机。
- `apps/api/app/services/conversation/__init__.py`
  - 导出 confirmation 类型。
- `apps/api/app/models/conversation.py`
  - `conversation_events.type` ORM 宽度从 `String(32)` 扩到 `String(64)`。
- `apps/api/alembic/versions/df9ed1494afd_widen_conversation_events_type_to_64_.py`
  - DB migration：`conversation_events.type` 32 -> 64，保证 PostgreSQL 能保存
    新事件名。
- `apps/api/tests/test_conversation_confirmation.py`
- `apps/api/tests/test_conversation_orchestrator.py`
- `apps/api/tests/test_conversation_api.py`
- `docs/iterations/m11/11.1.5-plan-confirmation-consent-gate/review.md`

行为：

- `confirm` / `yes` / `proceed` / `continue` / `确认` / `继续` /
  `/confirm` -> `plan_confirmed` + `plan_confirmed` event。
- `cancel` / `abort` / `stop` / `取消` / `停止` / `/cancel` / `/abort` /
  `/stop` -> `task_intake` + `plan_cancelled` event。
- `reject` / `no` / `不要` / `/reject` -> `task_intake` +
  `plan_rejected` event。
- 其他 free text -> stays `awaiting_confirmation` +
  `confirmation_clarification_requested` event。
- `/replay <learned_path_id> <url>` while awaiting confirmation -> stays
  `awaiting_confirmation` +
  `explicit_replay_blocked_by_pending_confirmation` event。
- 所有 confirmation gate event payload 明确包含 `replay_executed: false`。

边界（已遵守）：

- 不修改 11.1.1 task planning schemas。
- 不修改 11.1.2 retrieval implementation。
- 不修改 11.1.3 planner implementation。
- 不修改 11.1.4 preview implementation。
- 不新增 API endpoint。
- 不新增 CLI command。
- 不执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不做 slot binding / form filling。
- 不做 result verification。
- 不实现 Task Result Reporter。
- 不实现 recovery dialogue。
- 不实现 teaching mode。
- 11.1.5 实现阶段未创建 11.1.6 详情目录。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_confirmation.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py -q`
- 结果：`113 passed`
- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_confirmation.py tests/test_conversation_repo.py -q`
- 结果：`145 passed`
- `cd apps/api && ../../.venv/bin/alembic heads`
- 结果：`df9ed1494afd (head)`
- `cd apps/api && ../../.venv/bin/pytest -q`
- 记录结果：`1021 passed, 65 skipped`
- `cd apps/api && ../../.venv/bin/ruff check ...`
- 记录结果：`All checks passed!`
- `git diff --check`
- 结果：clean

### Future · Slot binding contract and deterministic binding MVP

状态：future，尚未分配执行包编号。

目标：

- 将用户任务里的名称、状态、日期、搜索词等绑定到 LearnedPath action
  values。
- 区分 replaceable action value 和 fixed learned action。
- 输出 slot binding proposal。
- 不执行 replay。

### 11.1.6 · Execution via Replay

状态：已完成。

目标：

- 让 `plan_confirmed` 状态下的 confirmed plan 可以通过现有 deterministic replay 执行。
- 只执行已经通过 11.1.5 明确确认的 route plan。
- 复用现有 deterministic replay 能力 / explicit replay hook 底层能力。
- 记录 replay execution evidence 和 conversation execution events。
- 缺少 selected LearnedPath、target URL 或 replay entry context 时返回 blocked 语义，不脑补、不执行。
- 明确 `replay completed` 只表示 replay 调用完成，不等于 business result verified 或 task succeeded。

交付：

- `apps/api/app/services/conversation/execution.py` — `PlanExecutionService` deterministic classifier + context extractor + replay invoker。
- `apps/api/app/schemas/conversation.py` — 新增 `executing`、`execution_finished`、`execution_failed` statuses；新增 4 个 execution event types。
- `apps/api/app/services/conversation/orchestrator.py` — `plan_confirmed` execution gate，状态流转 `plan_confirmed -> executing -> execution_finished/execution_failed`。
- `apps/api/app/routers/conversation.py` — 注入 `execution_handler`。
- `apps/api/tests/test_conversation_execution.py` — 29 tests。
- `apps/api/tests/test_conversation_orchestrator.py` — 7 个 execution gate 集成测试。
- `apps/api/tests/test_conversation_api.py` — 3 个 API-level execution 测试。
- `docs/iterations/m11/11.1.6-execution-via-replay/review.md`

行为：

- `plan_confirmed` + `execute`/`run`/`start`/`执行`/`开始` → `executing` → `execution_finished` (replay succeeded/observed) 或 `execution_failed` (replay drifted/failed)。
- 缺少 `learned_path_id` 或 `target_url` → `plan_execution_blocked`，session 保持 `plan_confirmed`。
- Multi-step route → `plan_execution_blocked`。
- 非 execution intent free text → falls through to state machine (blocked)。
- Explicit `/replay` 保持独立入口。

边界（已遵守）：

- 不重新规划，不调用 Task Path Planner。
- 不做 path selection。
- 不做 slot binding / form filling。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不做 hidden relearning。
- 不做 result verification。
- 不实现 Task Result Reporter。
- 不实现 recovery dialogue / teaching mode。
- 不创建 11.1.7 详情目录。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_execution.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_replay_hook.py tests/test_conversation_confirmation.py -q`
- 结果：`173 passed`
- `cd apps/api && ../../.venv/bin/pytest -q`
- 结果：`1066 passed, 65 skipped`
- `cd apps/api && ../../.venv/bin/ruff check ...`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/alembic heads`
- 结果：`df9ed1494afd (head)`
- `git diff --check`
- 结果：clean

### Future · Result verification and Task Result Reporter

状态：future，尚未分配执行包编号。

目标：

- 基于 replay result、postcondition signals、artifact status、final
  URL / title / DOM signal 生成 result verification。
- Task Result Reporter 汇报结果。
- 不脑补成功。
- 无法验证时返回 `uncertain` / `needs_review`。

### Future · Task-to-path tests and evidence

状态：future，尚未分配执行包编号。

目标：

- 建立 task-execution 测试域。
- 覆盖 retrieval、binding、planner output、confirmation、execution、
  reporting。
- 包含 deterministic E2E / API / CLI / evidence report。
- 不依赖 LLM provider 的测试优先。

## 执行规则

- 开始每个 `11.x` 前必须阅读 `AGENTS.md`、`docs/product-model.md`、
  `docs/iterations/m11/m11-plan.md`、相关总纲和当前执行包的
  `intent.md` / `plan.md`。
- 每次只实现当前包。
- 不调用 `/exploration/autonomous-runs` 或
  `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 不依赖 LLM provider。
- 不引入路线图外产品外壳、身份管理、托管数据或外部通道规划。
- 每个包完成后更新自己的 `review.md`，记录实际交付、验证命令、范围偏差和
  后续风险。
