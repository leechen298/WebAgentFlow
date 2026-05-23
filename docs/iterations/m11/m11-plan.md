# M11 全量计划

## 目标

M11 是 Runtime Loop Foundation。它从 M10 已完成的 LearnedPath 路径资产、
catalog、显式 replay 和 drift detection 出发，建立用户与 WebAgentFlow
沟通的运行时闭环。

M11.0 建立 Runtime Conversation Shell 和 Conversation Orchestrator /
Dispatcher 骨架。M11.1 进入 Task-to-Path Planning & Execution MVP。
M11.2 作为 v0.1 后续优化，补运行时观察与真实网页稳健性增强
（Runtime Observation & Realistic Web Hardening）的 scope 和后续执行包边界。

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
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

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
- `apps/api/tests/test_conversation_execution.py` — service-level tests。
- `apps/api/tests/test_conversation_orchestrator.py` — execution gate 集成测试。
- `apps/api/tests/test_conversation_api.py` — API-level execution 测试。
- `docs/iterations/m11/11.1.6-execution-via-replay/review.md`

行为：

- `plan_confirmed` + `execute`/`run`/`start`/`执行`/`开始` → `executing` → `execution_finished` (replay succeeded/observed) 或 `execution_failed` (replay drifted/failed)。
- 缺少 `learned_path_id` 或 `target_url` → `plan_execution_blocked`，session 保持 `plan_confirmed`。
- Multi-step route → `plan_execution_blocked`。
- 非 execution intent free text → falls through to state machine (blocked)。
- Explicit `/replay` 保持独立入口（在 `idle`/`task_intake` 等现有 state machine 允许 replay 的 state 下可用；`awaiting_confirmation` 和 `plan_confirmed` 下不允许绕过 pending / confirmed plan flow）。

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
- 不实现 11.1.7 result verification / Task Result Reporter。

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_execution.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_replay_hook.py tests/test_conversation_confirmation.py -q`
- 结果：`175 passed`
- `cd apps/api && ../../.venv/bin/pytest -q`
- 结果：`1074 passed, 65 skipped`
- `cd apps/api && ../../.venv/bin/ruff check ...`
- 结果：`All checks passed!`
- `cd apps/api && ../../.venv/bin/alembic heads`
- 结果：`df9ed1494afd (head)`
- `git diff --check`
- 结果：clean

### 11.1.7 · Result Verification and Task Result Reporter

状态：已完成（result reporter service + orchestrator/API 集成，1100 full tests passed，ruff clean）。

目标：

- 消费 11.1.6 的 replay execution evidence。
- 生成 conservative verification outcome：`verified` / `failed` / `uncertain` / `needs_review` / `blocked`。
- Task Result Reporter 基于证据汇报结果，不脑补成功。
- 明确 `plan_execution_completed` / replay completed 不等于 task succeeded。
- 无 postcondition evidence 时默认返回 `uncertain` / `needs_review`。
- failed / uncertain 不自动 recovery。

边界：

- 不执行 replay。
- 不重新执行 replay。
- 不调用 autonomous run。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不调用 Page Understanding Agent。
- 不做 Slot Binding / form filling。
- 不实现 recovery dialogue / teaching mode。
- 不创建 11.1.8 详情目录。

文档：

- `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/README.md`
- `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/intent.md`
- `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/plan.md`
- `docs/iterations/m11/11.1.7-result-verification-task-result-reporter/review.md`

### 11.1.8 · Task-to-path Tests and Evidence

状态：完成（1104 API tests passed, 25 E2E passed, ruff clean, no P1/P2）。

目标：

- 对 M11.1 task-to-path MVP 做测试与证据收口。
- 覆盖 domain schema、retrieval / ranking、Task Path Planner、planning
  preview、confirmation gate、execution via replay、Task Result Reporter、
  conversation API runtime、scoped E2E、explicit `/replay` 回归，以及
  negative / blocked / uncertain paths。
- 区分 deterministic tests、exploratory tests、Codex autonomous review、
  manual UI smoke 和 visual UI exploratory。
- 记录 test command、结果、事件序列、代表性 API response、assistant message
  summary、环境 caveats 和 follow-up issues。
- 明确 `replay completed` 仍不等于 task succeeded；`uncertain` /
  `needs_review` 是合法结果；failed / blocked 不触发 recovery 或 hidden
  learning。
- 不做新 runtime feature，不改 11.1.1 到 11.1.7 业务逻辑，不创建 11.1.9。

文档：

- `docs/iterations/m11/11.1.8-task-to-path-tests-and-evidence/README.md`
- `docs/iterations/m11/11.1.8-task-to-path-tests-and-evidence/intent.md`
- `docs/iterations/m11/11.1.8-task-to-path-tests-and-evidence/plan.md`
- `docs/iterations/m11/11.1.8-task-to-path-tests-and-evidence/review.md`
- `docs/testing/results/2026-05-13-11-1-8-task-to-path-tests-and-evidence.md`

验证：

- `cd apps/api && ../../.venv/bin/pytest tests/test_task_path_planner.py tests/test_task_planning_preview.py tests/test_conversation_confirmation.py tests/test_conversation_execution.py tests/test_task_planning_result_reporter.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_task_planning_schemas.py tests/test_task_planning_retrieval.py -q`
- 结果：`294 passed`
- `cd apps/api && ../../.venv/bin/pytest -q`
- 结果：`1104 passed, 65 skipped`
- `cd apps/api && ../../.venv/bin/ruff check app/schemas/conversation.py app/services/conversation app/services/task_planning tests/test_task_path_planner.py tests/test_task_planning_preview.py tests/test_conversation_confirmation.py tests/test_conversation_execution.py tests/test_task_planning_result_reporter.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_task_planning_schemas.py tests/test_task_planning_retrieval.py`
- 结果：`All checks passed!`
- `pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/task-execution.spec.ts`
- 结果：`3 passed (4.0s)`
- `pnpm run test:e2e`
- 结果：`25 passed (13.4s)`
- `git diff --check`
- 结果：clean
- `find docs/iterations/m11 -maxdepth 1 -type d -name '11.1.9*' -print`
- 结果：无 11.1.9 目录

## M11.2 · 运行时观察与真实网页稳健性增强

状态：11.2.3 implementation complete。11.2.2 最小 `wait_result` 能力和
11.2.3 replay-level `observation_summary` 能力已 scoped 收口。

M11.2 是 v0.1 后续优化。它不继续扩展 task-to-path 规划逻辑，而是在
M11.1 已完成的 replay execution / result reporting 后补运行时观察边界。

M11.2 只回答：

- 页面发生了什么？
- 变化是不是等到了？
- 观察到了哪些结构化信号？
- 这些信号能不能作为 result evidence？

M11.2 不回答：

- 失败后怎么办？
- 要不要 retry？
- 要不要 ask user / takeover？
- 要不要 abort / interrupt？
- 要不要提出 recovery proposal？

这些属于 v0.2 / M12。

### Post-action Observation

Post-action Observation 是用户或 replay 主动操作之后，页面在短时间内产生的
可观察变化。

示例：

- 点击提交后 loading 消失。
- 点击提交后 toast 出现。
- 点击操作后 modal 出现。
- 搜索后结果列表刷新。
- 填完字段后按钮从 disabled 变 enabled。
- 提交后 URL / title / text / element 变化。

它解决的问题是：系统不能点完按钮就立刻判断成功失败，而是要知道点完之后
应该等什么变化。

### Passive Runtime Observation

Passive Runtime Observation 是非用户主动操作触发的页面变化。

示例：

- WebSocket 推送新消息。
- SSE 推送状态更新。
- 后台任务完成后页面自动刷新。
- polling 导致列表更新。
- 客服消息自动出现。
- 订单状态被服务端主动更新。

它解决的问题是：页面自己变了，系统要能记录这个变化，并判断它是否影响
当前 replay / result report。

## M11.2 拆分原则

- 每个 `11.2.x` 都必须有清楚的 scope。
- 11.2.0 只做文档范围和 scenario catalog。
- 不在 11.2.0 写代码、测试代码或 fixture。
- 不把运行时观察写成 recovery。
- 不实现 retry policy。
- 不实现 user abort / stop handling。
- 不做 hidden relearning。
- 不调用 autonomous run。
- 不接入 LLM provider。
- 不读 raw HTML。
- 不创建 M12 / 12.x 目录。
- 不创建 v0.2 分支。

## M11.2 执行包拆分

### 11.2.0 · 运行时观察范围与真实场景目录

状态：文档初始化完成。

目标：

- 初始化 M11.2 文档包。
- 明确 M11.2 与 M11.1、M12 的边界。
- 定义 Post-action Observation 和 Passive Runtime Observation。
- 建立 realistic web runtime case catalog。
- 明确后续 11.2.x 包如何展开。

交付：

- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/intent.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/review.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

边界：

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不做 recovery / retry / abort / user interruption。
- 不做 teaching mode。
- 不做 autonomous run。
- 不接 LLM。
- 不读 raw HTML。

### 11.2.1 · 观察信号契约

状态：文档生成完成。

目标：

- 定义 Observation Signal 的文档级 contract。
- 定义 signal kind、scope、推荐字段和 conservative reporting 边界。
- 明确 `page_load_started` / `page_load_finished` 描述浏览器级页面加载、
  导航、完整刷新或 document reload。
- 明确 `loading_started` / `loading_finished` 描述页面内可见 loading UI。
- 明确 timeout / not-observed outcome 属于后续 wait-for-change result 设计，
  不作为 11.2.1 signal kind。

交付：

- `docs/iterations/m11/11.2.1-observation-signal-contract/README.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/intent.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/contract.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/plan.md`
- `docs/iterations/m11/11.2.1-observation-signal-contract/review.md`

边界：

- 不写代码。
- 不新增测试代码。
- 不修改 public API / database schema / TypeScript schema / Python schema。
- 不实现 wait-for-change / page-load waiting。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不做 recovery / retry / abort / interruption / user takeover。
- 不读取或保存 raw HTML。

### 11.2.2 · 等待变化 MVP

状态：最小代码实现完成，scoped review passed；后续 full API suite 已随 11.2.3
收口通过。

目标：

- 定义 Wait-for-change MVP 的文档级设计。
- 定义 replay action 后短窗口等待页面变化的最小语义。
- 定义 Wait Result 字段 proposal 和 status。
- 定义 Wait Strategy 方向。
- 明确 Wait Result 和 Observation Signal 的关系。
- 明确 wait 层不使用 Agent 判断业务成功。
- 明确 Agent 式解释留给 11.2.5 evidence-aware Task Result Reporter。

交付：

- `docs/iterations/m11/11.2.2-wait-for-change-mvp/README.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/intent.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/contract.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/plan.md`
- `docs/iterations/m11/11.2.2-wait-for-change-mvp/review.md`

实现边界：

- Wait-for-change MVP 优先覆盖 `post_action` wait。
- 11.2.2 当前最小实现只实际生成 `url_changed`、`title_changed`，以及作为
  supporting-only signal 的 `network_idle_observed`。
- `page_load_finished` 保留在 schema 中，当前 MVP 不实际生成。
- 11.2.2 不做完整组件库 runtime behavior detection，不把 later component-generated
  runtime surface detection and relation 写入当前 MVP 范围。
- `passive_runtime` 不作为 11.2.2 MVP 的连续后台观察目标。
- Wait Result status 收敛为 `observed`、`timeout`、`skipped`、`not_required`。
- `timeout` / `skipped` / `not_required` 是 wait outcome，不是 Observation Signal kind。
- Wait Strategy 只是后续实现方向，不代表能力已实现。
- `network_idle_observed` 只能作为辅助信号，不能单独代表业务成功。

Agent / Reporter 边界：

- Wait-for-change MVP 不使用 Agent 判断业务是否成功。
- wait 层只负责等待、观察、记录，产出结构化 wait results 和 observation signals。
- 不引入每一步 wait 后的 Agent 业务判断。
- 不引入 Agent 驱动的 retry、recovery、abort、user takeover 或 next-step decision。
- 11.2.5 才考虑 evidence-aware Task Result Reporter 如何消费 wait results 和
  observation signals。

Page Understanding Agent 边界：

- 11.2.2 不调用 Page Understanding Agent。
- Page Understanding Agent 属于 L1 / M14 的页面学习语义理解角色。
- 如果后续需要基于完整 replay evidence 做解释，应由 11.2.5 的 evidence-aware
  Task Result Reporter 承接，而不是把 Page Understanding Agent 放进 wait loop。

边界：

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 public API / database schema / TypeScript schema / Python schema。
- 不实现 runtime observation / wait-for-change / page-load waiting。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不做 recovery / retry / abort / interruption / user takeover。
- 不读取或保存 raw HTML。
- 不创建 M12 / M14 / 11.3 目录。

### 11.2.3 · replay 与观察集成

状态：implementation complete（56 scoped tests passed，1168 full API tests passed，
ruff clean）。

目标：

- 实现 replay-level observation evidence aggregation contract。
- 把 11.2.2 step-level `wait_result` / observation signals 汇总为 replay-level
  evidence summary。
- 明确 observation summary status、primary / supporting signal 聚合、timeout /
  skipped / not_required 统计和 uncertainty flags。
- 为 11.2.5 Task Result Reporter 消费 replay-level observation evidence 准备输入。

交付：

- `docs/iterations/m11/11.2.3-replay-integration-with-observation/README.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/intent.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/contract.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/technical-design.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/test-plan.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/plan.md`
- `docs/iterations/m11/11.2.3-replay-integration-with-observation/review.md`

实现范围：

- 可以按 `technical-design.md` 修改 replay response schema。
- 可以按 `technical-design.md` 新增 replay observation aggregation service。
- 可以按 `technical-design.md` 修改 replay result 组装逻辑。
- 可以按 `test-plan.md` 新增或更新 scoped tests。
- 不接 Task Result Reporter。
- 不改变 `ReplayResult.status`。
- 不做 recovery / retry / abort / user takeover。
- 不实现 Common Component Runtime Semantics。
- 不读取或保存 raw HTML。

### M11.2 deferred cleanup backlog

状态：后续优化记录，不属于 11.2.3 当前实现范围。

- 治理 `execute_action()` / `wait_for_change_after_action()` 的重复等待。当前
  MVP 中 action executor 仍保留动作后的稳定等待，observation layer 也会执行
  post-action wait；后续应逐步把“等待页面变化”的职责收敛到 observation layer。
- 在 11.2.5 Task Result Reporter 消费 observation summary 前细化统计语义。
  当前 `observed_step_count` 统计 wait outcome 为 `observed` 的 step；后续可新增
  或改名为 `wait_observed_step_count`、`primary_observed_step_count`、
  `supporting_only_step_count`，避免 reporter 把 supporting-only evidence 误读为
  primary observation。

### 11.2.4 · 真实网页场景目录与验证用例规划

状态：文档生成完成，fixture 页面 / mock backend / E2E 尚未实现。

目标方向：规划 WebAgentFlow 自建真实网页验证场景库，先系统定义 PC / 移动端
常见页面、业务场景、组件交互、网络延迟、错误响应、复杂度分层和 fixture phase
路线。11.2.4 不是找线上网站验证，也不是直接开发页面；它是后续 validation-site
页面、mock backend 和 E2E 的开发文档输入。

11.2.4.0 已将 scenario catalog 固化为“业务页面复杂度 × 运行条件矩阵 ×
runtime behavior”模型。页面复杂度按业务结构分类；toast、modal、loading、picker
等属于 runtime behavior / interaction pattern，不作为页面业务复杂度分类依据。

交付：

- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/README.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/intent.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/contract.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/technical-design.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/test-plan.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/plan.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/review.md`

Phase 边界：

- 11.2.4.1 建立 Single-page Runtime Fixture Shell。文档包：
  `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/`；当前 shell /
  route / index entry 已实现，具体业务 fixture 尚未实现。
- 11.2.4.2 实现 Single-page Basic Business Pages。文档包：
  `docs/iterations/m11/11.2.4.2-single-page-basic-business-pages/`；状态：
  implementation complete, review pending。当前 basic fixtures 已按
  `fixture-designs/*.md` 重做为 shared shell + per-fixture components；仍保持
  frontend-local deterministic error scope，不接 mock backend / reporter / M12。
- 11.2.4.3 实现 Single-page Medium Business Pages。
- 11.2.4.4 实现 Single-page Complex Business Pages。
- 11.2.4.5 引入 Mock Backend Runtime Conditions，覆盖 slow response、server
  validation、HTTP error status、polling、upload / export 和 async job completion。
- 11.2.4.6 实现 Mobile Single-page Patterns。
- 11.2.4.7 补 E2E Evidence and Review。
- 前端 timer 只用于 deterministic fixture，不代表真实 network evidence；mock
  backend 才负责 HTTP 层 slow response / error status evidence。

11.2.4 planning package boundary:

`11.2.4-realistic-scenario-catalog-fixture-planning/` only defined the scenario
catalog and fixture roadmap. It did not implement runtime source, tests, fixture
pages, mock backend, E2E, API / DB / CLI / Reporter contracts, Task Result
Reporter, M12 recovery / retry / abort, autonomous run, or `verify-scenario`.

Child implementation packages（例如 11.2.4.1、11.2.4.2）按各自目录内的
`README.md`、`contract.md`、`technical-design.md`、`test-plan.md` 和 `plan.md`
执行；父规划包边界不得阻止 child package 开工。

### 11.2.5 · 观察证据接入 Task Result Reporter

状态：计划中。

目标方向：让 Task Result Reporter 可以消费 observation evidence。无明确
postcondition evidence 时仍必须保守返回 `uncertain` / `needs_review`。

### later 11.2.x · Common Component Runtime Semantics

状态：候选增强方向，不重新编号现有 11.2.3 / 11.2.4 / 11.2.5。

目标方向：补充常用组件库运行时语义兼容。它不是 popup support，而是组件库生成的
运行时界面片段识别与关联（component-generated runtime surface detection and
relation）：在 replay action 后，识别由组件库生成或改变的 runtime surface，并
尽可能把新 surface 或状态变化与触发它的 action / element 关联起来。

runtime surface 包括但不限于 dropdown、select option panel、autocomplete panel、
cascader panel、date picker / time picker、popover、tooltip、modal / dialog、
drawer、toast / message、notification、action sheet、bottom sheet、mobile picker、
loading overlay、validation message、virtualized list、inserted option list，
以及 active / selected / checked / disabled / enabled 状态变化。

后续实现原则：

- 优先使用通用 Web 信号：DOM insertion / removal、visibility change、
  aria-expanded、aria-controls、aria-owns、role=listbox / option / menu / dialog /
  tooltip、selected / checked / disabled / active state、bounding rect proximity、
  insertion timing relative to action、focus movement、active descendant。
- 组件库 class 只作为 supporting evidence，例如 `ant-select-dropdown`、
  `el-select-dropdown`、`n-select-menu`、`arco-select-popup`、
  `t-select__dropdown`、`van-popup`、`van-action-sheet`、`nut-popup`、
  `adm-popup`，不能作为唯一依据。
- PC / 管理后台组件库兼容方向包括 Ant Design、Element Plus、Naive UI、Arco
  Design、TDesign、MUI / Material-ish components、Bootstrap-style components。
- 移动端组件库兼容方向包括 Ant Design Mobile、Vant、NutUI、Varlet、Ionic、
  Framework7-style mobile components。
- 不调用 Agent 判断业务成功，不让 LLM 进入 L3 per-step execution loop。
- 不阻塞 11.2.2 最小 wait_result / wait_strategy；建议位置关系为 11.2.2 最小
  wait_result / wait_strategy、11.2.3 replay integration、11.2.4 realistic scenario
  catalog / fixture planning、later 11.2.x Common Component Runtime Semantics、11.2.5 Reporter 消费
  observation / wait evidence。

### 11.2.6 · Codex 真实网页 QA

状态：计划中。

目标方向：组织 Codex / browser QA 对 realistic cases 做人工可读验证记录。
不得把 exploratory 结果伪装成 deterministic pass。

### 11.2.7 · 运行时观察测试与证据

状态：计划中。

目标方向：对 M11.2 observation 能力做测试和证据收口。它是 evidence closure，
不是新 runtime feature 包。

## 11.3 · Interactive Chat Closed Loop

状态：accepted（implementation review passed, manual smoke passed）。

目标：将 M11.0 / M11.1 已有的 conversation、LearnedPath、learning、replay
能力收束成第一个普通用户入口 `wagent chat`。用户不需要理解 session id、
Workbench、LearnedPath、preview 或 confirm，只通过持续聊天完成“学习页面 ->
执行已学操作”的最小闭环。

本包第一阶段只覆盖 validation-site `/login` happy path：

```text
wagent chat
-> 学习一下这个登录页怎么登录，地址是 http://localhost:5175/login
-> 我会学习：在登录页输入账号密码，并点击“登录”按钮。
-> 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。
-> 帮我登录
-> 我会执行：输入账号密码，并点击“登录”按钮完成登录。
-> 登录完成。
```

关键契约：

- `wagent chat` 是顶层 CLI 命令，不替代 `wagent conversation ...` developer
  workflow。
- `wagent chat` 创建 `current_mode=interactive_chat` session，并写入
  `metadata.client=wagent_chat`、`metadata.runtime_policy=auto_execute_happy_path`。
- Conversation runtime 只在 `session.current_mode == "interactive_chat"` 时启用
  chat happy path；dispatch metadata 只作为审计辅助。
- 学习完成必须以 `learned_path_id` 真实产生且可查询为准。
- 当前 session `learned_actions` 按 alias 去重，同 alias 后写覆盖前写。
- “帮我登录”只命中当前 session learned action；不做 global LearnedPath fallback。
- 命中单一 learned action 后直接 replay，不进入 11.1.5 confirmation gate。
- 非 `interactive_chat` session 继续走现有 planning preview / confirmation /
  execution via replay。
- `wagent chat` 默认 HTTP timeout 不低于 180s，并支持 `--timeout` 覆盖。
- validation-site 端口固定为 `http://localhost:5175`，console 为
  `http://localhost:5174`，API 为 `http://localhost:8001`。

执行包目录：

- `docs/iterations/m11/11.3-interactive-chat-closed-loop/`

非目标：

- 不做 `/users`、真实业务页或多页面 workflow。
- 不做 M12 recovery / retry / abort / takeover。
- 不做复杂 LLM 意图理解。
- 不废除 confirmation gate。
- 不做 streaming conversation。

## 11.3.1 · Visible Chat Browser Operation

状态：implementation complete（scoped tests passed, manual visible-browser smoke pending）。

目标：让 `wagent chat` 的学习和执行网页操作默认以用户可见的项目内置 Playwright
Chromium 运行。普通用户可以看到浏览器打开、页面加载、输入、点击和跳转；不希望看到
浏览器时，可以通过 `wagent chat --headless` 选择后台运行。

本包是 11.3 Interactive Chat Closed Loop 的产品体验收尾增强。它不把能力绑定到具体页面；
具体页面只作为 `test-plan.md` 中的人工验收靶子。

当前 scoped implementation 已完成：CLI 支持默认 visible 和 `--headless` opt-out，
Conversation runtime 会把 session-level visibility policy 传入 learning / replay 链路。
scoped CLI / API tests passed；真实可见浏览器人工 smoke 尚未在 review 中记录。

关键契约：

- `wagent chat` 默认 create session metadata 写入 `browser_visibility=visible`。
- `wagent chat --headless` 写入 `browser_visibility=headless`。
- Conversation runtime 必须优先读取 session metadata；dispatch metadata 只做审计。
- 默认 visible 只作用于 `session.current_mode == "interactive_chat"`。
- 非 `interactive_chat` 的 `wagent conversation ...`、planning preview、confirmation gate
  和 explicit replay 继续保持既有行为。
- 学习链路把 visibility policy 转换为 `LearningRunRequest.headless`。
- 执行链路把 visibility policy 传到 replay hook / `run_replay`。
- Playwright 使用项目已安装的 Chromium，不使用用户系统 Chrome profile。
- CLI 文案继续面向普通用户，不暴露 selector、id、className、LearnedPath、run_id 或
  replay id。

执行包目录：

- `docs/iterations/m11/11.3.1-visible-chat-browser-operation/`

非目标：

- 不实现用户系统 Chrome / profile 复用。
- 不做 streaming step progress。
- 不做用户接管、恢复、重试或 M12 recovery。
- 不改变 confirmation gate。
- 不把具体页面写成功能边界。

## 11.3.2 · Chat History & Debug Console

状态：implementation complete（implementation review passed, UI smoke pending）。

目标：为已有 Conversation 持久化补齐产品化 history / debug 入口。当前不是没有聊天记录存储，
而是有底层 session / message / event store，没有能让用户、开发者或 Codex CLI
方便复查和复用历史会话的看板与 CLI 聚合入口。

本包定位是可观察性和调试入口，不是新执行能力：

```text
wagent chat
-> 创建 interactive_chat session
-> 输出 session id
-> 后续可在 Console Chat History 看到该 session
-> 可查看 transcript / events / learned actions / replay evidence / raw JSON
-> Codex CLI 可用 history payload 判断上下文
-> 可通过 wagent conversation send 或 wagent chat --resume 继续调试
```

关键契约：

- 新增 `GET /conversation/sessions`，支持 `current_mode`、`status`、更新时间范围和
  `limit` 过滤。
- 新增 `GET /conversation/sessions/{session_id}/history`，聚合返回 session、messages、
  events、learned_actions、learning_runs、replay_summaries 和 raw JSON。
- Console 新增 `/conversation/history` 和 `/conversation/history/:session_id`。
- 详情页至少包含 Transcript、Events、Learned Actions、Replay / Learning Evidence、
  Raw JSON。
- CLI 新增 `wagent conversation list` 和 `wagent conversation history`。
- `wagent chat` 创建新 session 后输出 session id。
- `wagent chat --resume <session_id>` 只能 resume 既有 `interactive_chat` session。
- History / Debug surface 必须忠实展示已持久化数据，不发明 internal Agent verdict。
- 本包不触发 `verify-scenario`、autonomous run 或 product-driven browser execution。

执行包目录：

- `docs/iterations/m11/11.3.2-chat-history-debug-console/`

非目标：

- 不做复杂搜索、全文检索、长期归档或批量导出。
- 不做账号体系、多用户权限、云端用户数据或脱敏策略。
- 不做 LLM 总结历史、任务评分系统或失败恢复。
- 不做 M12 recovery / retry / abort / takeover。
- 不做 stable external M16 CLI / Skill / Tool interface。

## 11.3.3 · Product-Level Chat Test Site Separation

状态：accepted（implementation review passed, product-level CLI smoke passed）。

目标：把 `validation-site` 工程验证靶场和 `wagent chat` 产品级人工验收靶场拆开。
`validation-site` 继续保留 specs / assertions / pass_gate / scorecard /
`verify-scenario` 等 deterministic regression 能力；新增 `product-test-site`
用于验证普通用户通过 `wagent chat` 提供 URL 和必要输入，系统观察页面、学习操作、
沉淀 LearnedPath，并在同一聊天中执行已学操作。

本包已实现 `apps/product-test-site`，并通过 product-level CLI smoke。它不修改
11.3.2，也不迁移 `11.2.4.2-single-page-basic-business-pages`。

关键契约：

- `validation-site` 继续作为工程验证靶场，不删除、不弱化、不重命名。
- 产品级验收站点为 `apps/product-test-site`，package name 为
  `@web-agent-flow/product-test-site`，dev port 为 `5176`。
- 根目录 `pnpm run dev` 同时启动 product-test-site；单独 filter dev 只能作为
  开发调试入口，不能替代普通用户一键启动路径。
- 当前端口边界保持：console `5174`、validation-site `5175`、product-test-site
  `5176`、API `8001`。
- 第一阶段产品级页面规划为 `/workspace-login`，文案与 validation-site `/login`
  明显不同：`工作台入口`、`操作员账号`、`访问口令`、`进入工作台`、
  `工作台首页` / `已进入工作台`。
- 产品级 `wagent chat` learning path 不应读取
  `apps/validation-site/specs/*.assertions.json`。
- 产品级 `wagent chat` learning path 不应传 `spec_id` / `scenario`，也不应从
  assertions 取输入值。
- 产品级 learning 不应硬编码 `/login`、固定 host 或固定 route；学习目标必须来自用户输入的 URL。
- 执行只能命中当前 session 已学习过的 target URL / site；未学习过的站点或页面必须返回
  `还没学过这个站点或页面，需要先学习。`，不得跨站点命中历史 LearnedPath。
- 用户必须通过自然语言提供 URL 和必要输入，例如
  `地址是 http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456`。
- 修改或删除 `login.assertions.json` 不应影响 product-test-site 学习。
- 如果实现阶段仍靠 `spec_id=login` / `scenario=valid_credentials` 完成产品级学习，
  或用户没有在聊天中提供输入却从 validation spec 自动拿到输入，不得标记 accepted。

收口证据：

- Product-level `wagent chat` smoke session：`20602dde-1a64-4e81-8784-9b7949a9d866`。
- Learning run id：`c4564860-5140-4f13-a552-bca6697208df`。
- LearnedPath id：`03fb1fa1-2589-45cf-8322-4ba3f2809077`。
- Replay：`replay_status=succeeded`，`final_url=http://localhost:5176/workspace-home`。
- 未学习 URL fallback：`还没学过这个站点或页面，需要先学习。`。

执行包目录：

- `docs/iterations/m11/11.3.3-product-chat-test-site-separation/`

非目标：

- 不实现真实业务系统接入。
- 不实现复杂多页面 workflow、订单查询闭环或完整 slot binding。
- 不实现用户接管、M12 recovery / retry / abort。
- 不引入 LLM 复杂意图理解。
- 不改造 Chat History / Debug Console。
- 不实现 Visible Browser 本身。
- 不重构 validation-site。

## 11.3.4 · Conversation Intake Agent

状态：implementation complete（scoped tests passed, real LLM smoke pending）。

目标：补齐 `wagent chat` 的自然语言入口层。M11.3.3 已经让用户可以通过
product-test-site 完成产品级学习和执行 smoke，但当前语言入口仍主要靠 deterministic
parser / regex / alias 匹配。11.3.4 定义并实现 Conversation Intake Agent / 对话理解 Agent，
把用户自然语言转成 schema-constrained intent / target / action / slots / missing fields，
再交给 Conversation Orchestrator 校验和执行。

核心原则：

```text
不是让 LLM 控制浏览器。
是让 LLM 理解用户说的话。
```

关键契约：

- 第一阶段 intent 类型为 `learn_operation`、`execute_operation`、
  `provide_missing_info`、`unknown`。
- Intake 输出必须通过 JSON / Pydantic schema 校验。
- `slots[]` 必须通用化，包含 `name`、`semantic_type`、`label_seen`、`value`、
  `sensitive`、`source`，不只服务登录页。
- 缺少信息时保存 `pending_intake`，用户下一轮补充信息后合并并继续同一个流程。
- `pending_intake` 在 learning 成功、用户取消 / exit、新学习目标覆盖或 turns 用尽时清除；
  schema 校验失败时保留，允许用户重说。
- `provide_missing_info` 只能在当前 session 存在 `pending_intake` 时生效。
- Intake Agent 只能提供 `ask_user_message_hint`；最终用户文案由 Conversation
  Orchestrator 统一生成或过滤。
- `canonical_goal` 只作为匹配辅助，不是执行授权。
- Intake output 是 conversation intake evidence，不得写入 LearnedPath 作为页面观察事实、
  replay result、Supervisor verdict 或 execution proof。
- `password` / `token` / `access_secret` 等 sensitive slots 在 history / events /
  debug console / prompt logs 中默认 redacted。
- 每条 WAgent 用户可见回复必须记录 response provenance，区分 `code`、`agent`、
  `hybrid`、`unknown`。
- LLM-backed 回复必须留下脱敏 LLM trace，包括 provider、model、request id / trace id、
  schema validation、latency、token usage、raw request / response redaction 状态。
- 代码生成的回复也必须标注 producer，例如 `conversation_orchestrator_code` 或
  `interactive_chat_runtime_code`。
- Codex CLI 是外部开发 / 测试 Agent，不是 WebAgentFlow runtime 的 Reply Producer。
- LLM trace 是 reply generation evidence，不得写入 LearnedPath、replay result、
  Supervisor verdict 或 page observation evidence。
- malformed JSON、schema 校验失败、低 confidence 或 provider unavailable 时不得触发
  learning / replay；provider unavailable 可 fallback deterministic parser，但不得标记
  LLM-intake acceptance passed。
- 非 `interactive_chat` developer workflow 继续保持原 preview / confirmation 路径。

实现收口：

- Commit：`a08d434 feat: add conversation intake provenance tracing`。
- 已实现 ConversationIntakeService、ConversationIntakeResult schema、LLM-backed provider entry、
  deterministic fallback、pending intake guardrails、sensitive redaction、response provenance、
  redacted LLM trace 和 Conversation History detail 展示。
- Scoped tests passed：API 101 passed、CLI 13 passed、Console ConversationHistoryDetailPage
  169 tests passed、scoped ruff passed、`git diff --check` clean。
- 未执行真实 LLM-backed smoke，因此 LLM-intake acceptance 仍 pending。
- 人工发现的裸 URL + “学习”上下文恢复问题转入 11.3.5，并扩大为面客 Agent
  路由与应用技能运行时设计。

执行包目录：

- `docs/iterations/m11/11.3.4-conversation-intake-agent/`

非目标：

- 不让 LLM step-by-step 操作浏览器。
- 不让 LLM 输出 selector / browser actions / learned_path_id 并执行。
- 不做复杂多页面 workflow。
- 不做 M12 recovery / retry / abort。
- 不做真实业务系统适配。
- 不做完整风险 / consent policy。

## 11.3.5 · Customer-Facing Agent Router & Skill Runtime

状态：docs review passed；本地代码已有 runtime pieces，后续按 11.3.5.x working
runtime 拆包继续同步和收口。

目标：把 `wagent chat` 从“代码初筛 + Intake intent + 直接 learn / execute”升级为
“上下文收集 + 面客 Agent 路由 + 代码裁决 + 应用技能运行时”的产品入口。裸 URL、
短句续接和 no-path 学习引导仍是本轮必须解决的用户体验，但它们不再作为孤立 bug
处理，而是落在 Router / Orchestrator / Worker Agent / Skill Runtime 的责任边界里。

核心原则：

```text
Customer-Facing Agent Router != Conversation Orchestrator
Router 是建议者。
Orchestrator 是代码侧裁决者。
Skill Runtime 是执行者。
```

关键契约：

- Customer-Facing Agent Router 读取 Intake result、conversation context、page understanding、
  learned action summary 和 Application Skill Registry，只输出 route recommendation。
- Conversation Orchestrator 负责 session state、target resolution、pending state、scope、
  MVP 边界、confirmation、skill invocation、progress events 和最终用户文案。
- Application Skill Registry 是应用能力目录，不是 Agent 列表。第一版能力包括
  `collect_conversation_context`、`inspect_target_page`、`understand_page`、
  `lookup_learned_actions`、`ask_user_for_missing_info`、`start_learning`、
  `start_replay`、`learn_then_execute`、`record_progress_event`、`record_agent_trace`。
- Page Understanding Agent 可读取 page-context bundle，输出页面摘要、可见控件、支持目标
  和必需 slots；不得输出 selector、browser steps、page classification contract 或
  learned_path_id。
- Learning Agent 组织学习流程，Web Operation Agent 组织网页操作执行；二者只能通过
  Orchestrator / Skill Runtime 请求能力。
- 本轮明确复用现有 HTML -> Full AST、Full AST -> Simplified AST、PageAnalysis、
  form label extraction、action planning、execution runtime、ExplorationRun steps、
  LearnedPath model / actions、wait-for-change signals、replay observation、
  task planning schemas 和 response provenance。
- target resolution 优先级：用户消息显式 URL > `pending_target` > 最近提到 URL /
  no-path context > 当前 session 唯一 learned target > 未来 active tab > 追问。
- M11.3.5 不实现 active browser tab，不得假设该能力存在。
- 本轮不实现正式 Risk Policy；明显高影响或不可逆动作不进入自动
  learn_then_execute，正式 risk / consent policy 留给后续迭代。
- Router / Page Understanding 默认 no-thinking / low-latency structured JSON，不保存
  chain-of-thought。
- Agent prompt 作为版本化 prompt asset 存放在 `apps/api/app/prompts/`，service 代码
  只引用 prompt id / version / loader，不内嵌大段 system prompt；LLM trace 记录
  prompt id、version、hash、schema 和 redaction 状态。
- 裸 URL 不直接 execute；保存 pending target 并追问用户想学习或执行什么。
- CLI 对模糊输入显示中性 loading，不提前猜测“执行”。
- History detail 展示 Intake / Router / Orchestrator / Worker Agent / skill / final
  response provenance，并保持 sensitive redaction。
- 非 `interactive_chat` developer workflow 不变。

执行包目录：

- `docs/iterations/m11/11.3.5-customer-facing-agent-router-skill-runtime/`

非目标：

- 不让 LLM 操作浏览器。
- 不让 Router 直接调用 skill。
- 不输出 selector / browser actions / learned_path_id 作为执行授权。
- 不做 M12 recovery / retry / abort。
- 不做复杂多页面 workflow。
- 不做真实业务系统适配。
- 不重新引入已移除的旧用户操作录制 / Chrome extension 栈。

## 11.3.5.1 · Conversation Entry Gate & Chat Latency UX

状态：ready_for_implementation（docs review passed, implementation in progress）。

目标：作为 11.3.5 的 patch-level 优化，在 Conversation Intake Agent / Customer-Facing
Agent Router 之前增加轻量入口门禁，并把 `wagent chat` 的等待体验从一次性进度文案升级为
持续 working 状态。当前一次性 `正在理解你的需求。` 只能说明客户端没有提前猜“学习/执行”，
不能视为类似 Codex CLI / Claude Code CLI 的 loading / working UX。

核心原则：

```text
Conversation Entry Gate 不是 Router。
Conversation Entry Gate 不是新的工作 Agent。
Conversation Entry Gate 不调用 skill。
Conversation Entry Gate 不触发 learning / replay。
Conversation Entry Gate 只判断是否需要进入网页任务 runtime。
```

关键契约：

- Entry Gate 位于 Intake / Router 之前，只作用于 `interactive_chat`。
- Entry Gate 使用低延迟、非 thinking、schema-constrained 输出，只做网页任务相关性判断。
- 非网页任务、普通问候、能力询问和闲聊应快速得到统一 WAgent 口径的友好回复，
  并引导用户回到 WebAgentFlow 的网页学习、执行和调试能力。
- URL、学习、执行、页面操作等网页任务候选继续进入 11.3.5 runtime。
- provider timeout、malformed JSON、schema 校验失败或 low confidence 时不得触发
  learning / replay。
- Entry Gate trace 是 conversation evidence，不是 LearnedPath、replay、Supervisor 或
  pass_gate evidence。
- CLI 必须在等待 `/dispatch` 返回期间显示持续 working indicator；该体验参考 Codex CLI /
  Claude Code CLI 的 agentic CLI 沟通原则，但不复制具体视觉样式。progress / working
  状态不是正式 WAgent 回复。
- History detail 应展示 entry gate category、latency、provider / model、是否跳过
  Intake / Router 以及最终回复 provenance。

执行包目录：

- `docs/iterations/m11/11.3.5.1-conversation-entry-gate-latency-ux/`

非目标：

- 不做完整闲聊系统。
- 不新增产品 Agent 角色。
- 不让 Entry Gate 替代 Intake、Router 或 Orchestrator。
- 不让 Entry Gate 调用 skill、打开浏览器、选择 LearnedPath 或输出 selector / browser steps。
- 不实现 active browser tab、M12 recovery / retry / abort 或正式 risk / consent policy。

## 11.3.5.x · Working Runtime Follow-up Packages

状态：规划锚定完成，具体执行包按需生成完整七件套。

这组包继续挂在 11.3.5 下，而不是升格成 11.4。原因是它们都属于
Customer-Facing Agent Router & Skill Runtime 的 working runtime 收口：让 `wagent chat`
从“能进入 Agent runtime”推进到“能在 product-test-site 上完成可验证网页操作”。

完整施工稿：

- [`11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](./11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)
- [`11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](./11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)

施工原则：

- 旧 M11 切分可以调整，但每个执行包必须可验收、可回滚、可解释。
- 11.3.5.2 目录已经存在，继续作为 Chat Task State Reducer、learning preconditions、
  working runtime 总设计和测试入口的锚点；暂不为了改名迁移目录。
- `/items`、参数化 replay、ExecutionEvidence、Reporter 接入、`pending_choice`、
  `active_task`、基础恢复和 TaskPathPlanner chat 接入不得塞进一个大迭代。
- `ExecutionEvidence` 是新增 / 扩展 contract。现有 TaskResultReporter 需要 adapter 才能
  消费 replay result + 页面证据。
- “学习新增 A -> 执行新增 B”依赖参数化 learning / replay slot override；不能只靠固定
  LearnedPath action value 重放。
- P0 验收必须证明 replay 实际填入执行阶段的新值 B，而不是学习阶段录制的 A。
- TaskPathPlanner 已实现，但不进入 `/items` 单路径 P0 happy path；只用于多候选、
  模糊目标、planning preview / confirmed execution path。

| Package | 目标 | 状态 / 顺序 |
|---|---|---|
| 11.3.5.2 · Chat Task State Reducer & Learning Preconditions | 文档同步、working runtime 总设计、turn-based reducer、learning preconditions 和测试入口 | 当前锚点 |
| [11.3.5.3 · Product Test Site `/items` Fixture](./11.3.5.3-product-test-site-items-fixture/) | 新增 `apps/product-test-site` `/items` 列表测试页；只提供学习 / 执行新增项目的稳定页面基座 | implementation complete（product-test-site build passed, `/items` smoke passed） |
| [11.3.5.4 · Parameterized Learning / Replay Slots](./11.3.5.4-parameterized-learning-replay-slots/) | 补 `item_name` 等业务 slot 抽取、学习填值、`value_slot` 参数绑定和 replay `slot_overrides`，支持学习 A 后按用户新输入执行 B | ready_for_implementation（design review passed） |
| [11.3.5.5 · ExecutionEvidence & TaskResultReporter Adapter](./11.3.5.5-execution-evidence-result-reporter-adapter/) | 新增 / 扩展执行证据 contract，runtime stop 前采集 DOM evidence，并把 replay result + page evidence 适配成保守结果回复 | ready_for_implementation（design review passed） |
| [11.3.5.6 · WAgent Chat `/items` Closed-loop Evaluation](./11.3.5.6-wagent-chat-items-closed-loop-evaluation/) | 沉淀 `/items` 学习 / 执行闭环测试方案、实跑结果、完整日志和 Codex 复核记录 | implementation complete（closed-loop pass，result recorded） |
| [11.3.5.7 · Pending Choice & Minimal Active Task Ledger](./11.3.5.7-pending-choice-active-task-ledger/) | 多候选澄清、choice 私有映射、最小 active task 状态账本、pending 清理 / 过期和 cancel cleanup | implementation complete（code review passed，targeted tests passed） |
| [11.3.5.8 · Basic Failure Recovery](./11.3.5.8-basic-failure-recovery/) | 基础失败恢复：重试、重新学习、取消；不做复杂自治恢复 | implementation complete（code review passed，targeted tests passed） |
| [11.3.5.9 · TaskPathPlanner Multi-candidate Chat Integration](./11.3.5.9-taskpathplanner-multi-candidate-chat-integration/) | 多 learned actions、模糊目标、planning path 下接入 TaskPathPlanner 和 choice mode | implementation complete（code review passed，targeted tests passed） |

第一条可验收窄闭环：

```text
apps/product-test-site /items
-> 学习新增项目
-> 参数化执行新增项目，填入执行阶段的新 item_name
-> runtime stop 前采集页面证据
-> TaskResultReporter 保守回复
-> docs/testing/results 记录结果和日志复核
```

## 11.3.6 · WAgent Runtime Eval Program

状态：closed_pass_with_caveats（final closeout rerun pass）。

11.3.6 不直接实现 runner，也不继续增加 Customer-Facing Agent Router / Skill Runtime
的产品能力。它是 WAgent runtime eval 的总体测试规划包：定义 hard gates、artifact、
exit code、redaction、Codex 审计边界和 11.3.6.x 子包路线。

定位：

```text
11.3.6 program
-> 11.3.6.1 runner core + /items closed loop
-> 11.3.6.2 failure recovery eval
-> 11.3.6.3 pending choice multi-candidate eval
-> 11.3.6.4 planner-backed choice eval
-> 11.3.6.5 program closeout sweep
-> 11.3.6.6 gate failure fixes
```

子包路线：

| Package | 目标 | 状态 |
|---|---|---|
| [11.3.6.1 · WAgent Runtime Eval Runner Core](./11.3.6.1-wagent-runtime-eval-runner-core/) | 实现 runner v1，覆盖 `items_closed_loop` 和 `single_path_direct_replay_regression` | implemented_and_live_eval_passed |
| [11.3.6.2 · Failure Recovery Eval](./11.3.6.2-failure-recovery-eval/) | recovery menu safety、retry / relearn / cancel、private payload safety | implementation_complete_verified |
| [11.3.6.3 · Pending Choice Multi-candidate Eval](./11.3.6.3-pending-choice-multi-candidate-eval/) | A/B/C public choice、private map、用户选择后执行正确 path | implementation_complete_verified |
| [11.3.6.4 · Planner-backed Choice Eval](./11.3.6.4-planner-backed-choice-eval/) | vague goal、planner-backed choice path、single-path bypass Planner 回归 | implementation_complete_verified |
| [11.3.6.5 · Runtime Eval Program Closeout](./11.3.6.5-runtime-eval-program-closeout/) | 收口 11.3.6.3 / 11.3.6.4 implementation evidence、result artifact、review 状态和 program 索引 | completed_after_fix_rerun |
| [11.3.6.6 · Runtime Eval Gate Failure Fixes](./11.3.6.6-runtime-eval-gate-failure-fixes/) | 修复 service-available rerun 暴露的 pending choice payload leak、planner choice no-execution 和 raw artifact redaction failures | implementation_complete_verified |

关键边界：

- 11.3.6 program 本身 docs-only，不写 runner 代码。
- 11.3.6.1 承接已通过评审的 runner core 设计。
- 11.3.6.2 已实现稳定 eval-only hook 和 recovery gates；final closeout rerun live
  Conversation eval 已通过。
- 11.3.6.3 runner case 已实现；final closeout rerun pending-choice eval 已通过。Caveat：
  eval 使用 eval-only candidate binding，不证明 `/items` 有三个真实 distinct product actions。
- 11.3.6.4 runner case 已实现；final closeout rerun planner-backed choice 和
  single-path bypass regression 均已通过。Caveat：`planner_top_choice_observable` 仍为
  非 required `not_observable` warning。
- 11.3.6.6 已实现并验证；final closeout rerun 中 items、failure recovery、pending choice、
  planner choice 均返回 exit `0`。
- 11.3.6 closeout 的 pass 口径必须保持为 runtime execution capabilities pass with
  documented caveats。它验证已学路径复用、参数化执行、evidence reporting、多候选选择、
  planner-backed choice 分支和 basic recovery menu；它不验证页面级自动能力发现、自动学习
  页面所有操作、完整操作库生成或任意用户任务自动命中执行。
- 11.3.6.x runner 通过 Conversation API 驱动，不把 direct replay API 冒充 WAgent
  runtime 闭环。
- Codex 复核 artifact，不替 runner 判定 pass / fail。
- 不调用 autonomous-run endpoints。
- 不默认调用 `verify-scenario`。

迭代文档：

- [`11.3.6-wagent-runtime-eval-program/`](./11.3.6-wagent-runtime-eval-program/)
- [`11.3.6.1-wagent-runtime-eval-runner-core/`](./11.3.6.1-wagent-runtime-eval-runner-core/)
- [`11.3.6.2-failure-recovery-eval/`](./11.3.6.2-failure-recovery-eval/)
- [`11.3.6.3-pending-choice-multi-candidate-eval/`](./11.3.6.3-pending-choice-multi-candidate-eval/)
- [`11.3.6.4-planner-backed-choice-eval/`](./11.3.6.4-planner-backed-choice-eval/)
- [`11.3.6.5-runtime-eval-program-closeout/`](./11.3.6.5-runtime-eval-program-closeout/)
- [`11.3.6.6-runtime-eval-gate-failure-fixes/`](./11.3.6.6-runtime-eval-gate-failure-fixes/)

## 11.3.7 · User-facing WAgent Behavior Eval

状态：proposed（docs drafted，implementation pending）。

11.3.7 是 11.3.6 之后的用户视角产品行为验收包。它不再重复测试 `value_slot`、
`slot_overrides`、Reporter adapter、pending choice private map 等底层零件，而是验证
普通用户进入时，WAgent 是否能自己完成：

```text
用户输入
-> 解析页面 / 目标 / 意图
-> 查询 learned actions
-> 判断 known / unknown / ambiguous
-> 学习、执行、追问或安全拒绝
-> 基于 evidence 回复
-> 失败时给出安全恢复出口
```

第一批 required cases：

| Case | 目标 |
|---|---|
| URL-only known page | 用户只发页面 URL，WAgent 自动列出已学操作并让用户选择 |
| URL-only unknown page | 用户只发未学习页面，WAgent 说明未学过并引导学习 / 查看 / 取消 |
| execute-known action | 用户明确要求执行已学操作，WAgent 自动匹配路径、补参数、执行并验证 evidence |
| execute-unknown action | 用户要求执行未学操作，WAgent 不直接 replay，而是询问学习并执行 / 只学习 / 取消 |
| vague input | 用户说得模糊或乱说，WAgent 不执行，要求补页面或操作目标 |

后续扩展：

- explicit learn；
- pending slot continuation；
- A / 1 / 第一个 choice selection；
- failure recovery menu；
- controlled page capability discovery；
- controlled multi-operation learning；
- natural-language reuse across multiple learned actions。

硬性泛化约束：

- 测试页面 URL、route、页面文案、按钮名、字段名、DOM test id、fixture 业务内容和测试别名
  不得出现在功能代码或产品 prompt 中。
- 这些测试目标细节只能存在于 fixture、eval spec、test data、测试文件、docs、redacted
  artifact 中。
- 后续实现必须先建立 forbidden-token scan，再运行行为 case；如果发现功能代码或产品 prompt
  包含测试目标细节，11.3.7 必须 fail。

迭代文档：

- [`11.3.7-user-facing-wagent-behavior-eval/`](./11.3.7-user-facing-wagent-behavior-eval/)

## Later M11.x · Page Context Bridge Decision Point

状态：候选决策点，不是已确定执行包。

M11.2 / M11.3 完成后，可以根据实际验证结果决定是否插入一个小型 later M11.x。
候选方向是 Page Context Bridge / 页面语义上下文桥接。

它不是完整 M14，也不是完整 Page Understanding Agent 提前实现。

### Why this may be needed

M11.1 / M11.2 可以在没有 Page Understanding Agent 的情况下跑通：

```text
用户任务
-> LearnedPath retrieval / ranking
-> Task Path Planner
-> 用户确认
-> replay execution
-> observation / wait evidence
-> Task Result Reporter
```

但 M11.2 收口后，如果发现主要瓶颈不是“执行和观察”，而是：

- learned path 的业务语义太弱。
- Task Path Planner 缺少页面上下文。
- Task Result Reporter 汇报像执行日志，不像任务结果。
- execution evidence 有了，但缺少页面级语义解释。

则可以考虑插入 Page Context Bridge。

### Candidate scope

Page Context Bridge 只作为候选后续包记录，不在 11.2.2 或 11.3 interactive
chat closed loop 中实现。

候选目标：

- 定义轻量 Page Context Contract。
- 从已有 LearnedPath metadata、page_template、scenario、route plan、observation
  evidence 中整理页面上下文。
- 为 Task Path Planner 和 Task Result Reporter 提供轻量语义上下文。
- 不要求 L3 实时读取 raw HTML。
- 不让 LLM 进入 per-step execution loop。

示例 Page Context：

```json
{
  "page_context_summary": "这是一个订单查询页面",
  "known_task_domain": "search_and_filter",
  "expected_result_shape": "列表刷新 / 出现目标文本 / 导出文件",
  "source": "learned_path_metadata"
}
```

### Explicit non-goals

Page Context Bridge 不等于 M14 提前。

Page Context Bridge 不做：

- 不实现完整 Page Understanding Agent。
- 不实现 Attempt Evaluation Agent。
- 不实现 Learning Report Agent。
- 不重构 L1 autonomous learning。
- 不读取 raw HTML 做 runtime planner。
- 不让 LLM 在 L3 每一步看网页决定怎么点。
- 不替代 Task Path Planner。
- 不替代 Task Result Reporter。
- 不做 recovery / retry / abort / user takeover。
- 不创建 M14 范围内的 learning quality / coverage / negative knowledge 系统。

完整 Page Understanding Agent 仍然属于后续 M14 范围。

Page Context Bridge 只是一个 later M11.x 可选决策点：如果语义上下文成为瓶颈，
再考虑插入；否则继续进入 M12 Recovery & Abort Dialogue。

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
