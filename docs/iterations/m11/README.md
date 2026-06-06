# M11 · Runtime Loop Foundation

M11 的目标是让 WebAgentFlow 从“路径资产可以持久化、查看、显式 replay”
进入“用户可以通过运行时入口和 WebAgentFlow 沟通”的阶段。M10 已经完成
LearnedPath persistence、catalog、replay execution + drift detection；
M11 在这个确定性底座上建立 runtime loop。

M11 不是重新做 L1 autonomous learning，也不允许 LLM 逐步控制浏览器。
用户始终和 WebAgentFlow 这个应用沟通，内部 Agent 边界由
Conversation Orchestrator / Dispatcher 管理。

M11.0 先做 Runtime Conversation Shell & Agent Orchestration。它建立
CLI-first 的最小运行时沟通入口、session state、消息 / 事件边界和
orchestrator 骨架。M11.1 进入 Task-to-Path Planning & Execution MVP。
M11.2 在 v0.1 后续优化中补运行时观察与真实网页稳健性增强
（Runtime Observation & Realistic Web Hardening），
只定义页面变化观察和 evidence 边界，不进入 M12 recovery / retry / abort。

M11.0 也是 M11.1 Task-to-Path、M12 Recovery / Abort、M13 Guided Teaching
的共同入口层。当前最小可行 runtime surface 是 CLI-first：先跑通完整功能
闭环，再扩展更丰富的操作员界面或稳定对外接口。

## M11 收口状态

状态：`review complete`

M11 runtime 已按当前 v0.1 范围收口：M11.0 conversation shell、M11.1
task-to-path happy path、M11.2 scoped observation hardening、M11.3 interactive
chat productization，以及 11.3.7 first-wave user-facing WAgent behavior eval
均已有对应实现 / 验收记录。

收口证据：
[`docs/testing/results/m11-runtime-final-closeout-20260524.md`](../../testing/results/m11-runtime-final-closeout-20260524.md)。

该状态不代表完整页面全量自动能力发现、批量学习所有操作、full learn-then-execute、
Console UI smoke、外部黑盒站点验证或 M12 recovery / retry / abort 已完成。外部验证站点迁移
另作独立工作，不纳入本次 M11 收口。

## 迭代索引

- [m11-plan](./m11-plan.md) —— M11 全量计划与 M11.0 / M11.1 执行包拆分。状态：持续更新。
- [11.0-runtime-conversation-shell-orchestration](./11.0-runtime-conversation-shell-orchestration/) —— M11.0 总纲：Runtime Conversation Shell 与 Conversation Orchestrator 规划。状态：完成。
- [11.0.1-conversation-domain-contract](./11.0.1-conversation-domain-contract/) —— conversation session / message / event / command / state contract。状态：完成。
- [11.0.2-conversation-session-store](./11.0.2-conversation-session-store/) —— session / message / event persistence。状态：完成。
- [11.0.3-conversation-api](./11.0.3-conversation-api/) —— conversation API endpoints。状态：完成。
- [11.0.4-runtime-cli-shell](./11.0.4-runtime-cli-shell/) —— CLI-first runtime conversation shell。状态：完成。
- [11.0.5-orchestrator-dispatcher](./11.0.5-orchestrator-dispatcher/) —— Orchestrator / Dispatcher state routing。状态：完成。
- [11.0.6-explicit-replay-command-hook](./11.0.6-explicit-replay-command-hook/) —— 显式 `/replay <learned_path_id> <url>` hook。状态：完成。
- [11.0.7-conversation-tests-and-evidence](./11.0.7-conversation-tests-and-evidence/) —— conversation 测试域与证据。状态：完成。
- [11.1-task-to-path-planning-execution](./11.1-task-to-path-planning-execution/) —— M11.1 总纲：Task-to-Path Planning & Execution MVP。状态：完成。
- [11.1.1-task-planning-domain-contract](./11.1.1-task-planning-domain-contract/) —— task / candidate / route / binding / verification domain contract。状态：完成（17 schema，33 passed）。
- [11.1.2-learned-path-retrieval-ranking](./11.1.2-learned-path-retrieval-ranking/) —— LearnedPath retrieval and deterministic ranking。状态：完成（38 retrieval tests，71 combined passed）。
- [11.1.3-task-path-planner-mvp](./11.1.3-task-path-planner-mvp/) —— Task Path Planner MVP。状态：完成（21 planner tests passed）。
- [11.1.4-task-planning-dispatch-preview](./11.1.4-task-planning-dispatch-preview/) —— Task Planning Dispatch Preview。状态：完成（64 targeted tests passed，962 full API tests passed）。
- [11.1.5-plan-confirmation-consent-gate](./11.1.5-plan-confirmation-consent-gate/) —— Plan Confirmation and Consent Gate。状态：完成（confirmation gate + slash decision commands，review passed）。
- Slot Binding contract and deterministic binding MVP —— 状态：future，尚未分配执行包编号。
- [11.1.6-execution-via-replay](./11.1.6-execution-via-replay/) —— Execution via Replay。状态：完成（execution service + orchestrator/API coverage，full API tests passed，ruff clean）。
- [11.1.7-result-verification-task-result-reporter](./11.1.7-result-verification-task-result-reporter/) —— Result Verification and Task Result Reporter。状态：完成（result reporter service + orchestrator/API 集成，1100 full tests passed，ruff clean）。
- [11.1.8-task-to-path-tests-and-evidence](./11.1.8-task-to-path-tests-and-evidence/) —— Task-to-path Tests and Evidence。状态：完成（1104 API tests passed, 25 E2E passed, ruff clean, no P1/P2）。
- [11.2-runtime-observation-realistic-hardening](./11.2-runtime-observation-realistic-hardening/) —— M11.2 总纲：运行时观察与真实网页稳健性增强。状态：11.2.0 文档初始化完成。
- [11.2.1-observation-signal-contract](./11.2.1-observation-signal-contract/) —— Observation Signal Contract。状态：文档生成完成。
- [11.2.2-wait-for-change-mvp](./11.2.2-wait-for-change-mvp/) —— Wait-for-change MVP。状态：最小代码实现完成，scoped review passed；后续 full API suite 已随 11.2.3 收口通过。
- [11.2.3-replay-integration-with-observation](./11.2.3-replay-integration-with-observation/) —— Replay Integration with Observation。状态：implementation complete（56 scoped tests passed, 1168 full API tests passed, ruff clean）。
- [11.2.4-realistic-scenario-catalog-fixture-planning](./11.2.4-realistic-scenario-catalog-fixture-planning/) —— Realistic Scenario Catalog & Fixture Planning。状态：文档生成完成，fixture 页面 / mock backend / E2E 尚未实现。
- [11.2.4.1-single-page-runtime-fixture-shell](./11.2.4.1-single-page-runtime-fixture-shell/) —— Single-page Runtime Fixture Shell。状态：完成（fixture-site runtime observation shell / route / index entry implemented）。
- [11.2.4.2-single-page-basic-business-pages](./11.2.4.2-single-page-basic-business-pages/) —— Single-page Basic Business Pages。状态：implementation complete, review pending；当前已按页面级 fixture designs 重做 7 个 PC basic fixtures。
- 11.2.x · Common Component Runtime Semantics（常用组件库运行时语义兼容）—— later M11.2.x 候选增强；记录组件库生成的 runtime surface detection and relation，不属于 11.2.2 当前 MVP。
- [11.3-interactive-chat-closed-loop](./11.3-interactive-chat-closed-loop/) —— Interactive Chat Closed Loop：`wagent chat` 小白用户闭环，当前只覆盖 `/entry` happy path。状态：accepted（implementation review passed, manual smoke passed）。
- [11.3.1-visible-chat-browser-operation](./11.3.1-visible-chat-browser-operation/) —— Visible Chat Browser Operation：`wagent chat` 默认以用户可见的项目内置 Playwright Chromium 学习和执行网页操作，支持 `--headless` opt-out。状态：implementation complete（scoped tests passed, manual visible-browser smoke pending）。
- [11.3.2-chat-history-debug-console](./11.3.2-chat-history-debug-console/) —— Chat History & Debug Console：补 Conversation session list、aggregate history、Console history 页面、CLI list/history/resume，服务人工测试和 Codex CLI 调试复用。状态：implementation complete（implementation review passed, UI smoke pending）。
- [11.3.3-product-chat-test-site-separation](./11.3.3-product-chat-test-site-separation/) —— Product-Level Chat Test Site Separation：拆分 fixture-site 工程验证靶场与 fixture-site 产品级 chat 人工验收靶场，避免 validation spec / assertion oracle 污染 `wagent chat` 产品路径。状态：accepted（implementation review passed, product-level CLI smoke passed）。
- [11.3.4-conversation-intake-agent](./11.3.4-conversation-intake-agent/) —— Conversation Intake Agent：为 `wagent chat` 定义并实现 schema-constrained 自然语言入口层，让 LLM 理解用户话语并输出结构化 intent / target / action / slots / missing fields，代码继续负责校验和执行；同时 Conversation History detail 展示 WAgent 回复来源和脱敏 LLM trace。状态：implementation complete（scoped tests passed, real LLM smoke pending）。
- [11.3.5-customer-facing-agent-router-skill-runtime](./11.3.5-customer-facing-agent-router-skill-runtime/) —— Customer-Facing Agent Router & Skill Runtime：把 chat recovery 问题扩展为面客 Agent 路由与应用技能运行时，定义 Router / Orchestrator / Worker Agent / Application Skill Registry 边界，复用 AST、PageAnalysis、LearnedPath 和 replay evidence；完整 working runtime 施工稿见 [`working-runtime-construction.md`](./11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)。状态：planning_refined。
- [11.3.5.1-conversation-entry-gate-latency-ux](./11.3.5.1-conversation-entry-gate-latency-ux/) —— Conversation Entry Gate & Chat Latency UX：作为 11.3.5 的 patch-level 优化，在 Intake / Router 前加入轻量入口门禁，避免非网页消息进入重型 Agent runtime，并把 `wagent chat` 等待体验从一次性文案升级为持续 working 状态。状态：ready_for_implementation（docs review passed, implementation in progress）。
- [11.3.5.2-chat-task-state-reducer-learning-preconditions](./11.3.5.2-chat-task-state-reducer-learning-preconditions/) —— Chat Task State Reducer & Learning Preconditions：承接 11.3.5 working runtime 总设计、状态推进、learning preconditions 和测试入口；作为后续 11.3.5.x working runtime 拆包的规划锚点。状态：draft_requirements。
- [11.3.5.3-fixture-site-items-fixture](./11.3.5.3-fixture-site-items-fixture/) —— Product Test Site `/records` Fixture：新增 `apps/fixture-site` 列表测试页，只提供第一条 working runtime happy path 的页面基座。状态：implementation complete（fixture-site build passed, `/records` smoke passed）。
- [11.3.5.4-parameterized-learning-replay-slots](./11.3.5.4-parameterized-learning-replay-slots/) —— Parameterized Learning / Replay Slots：补 `record_name` 等业务 slot 抽取、学习填值、`value_slot` 参数绑定和 `slot_overrides`；解决“学习 A 后执行 B”的参数化执行缺口。状态：ready_for_implementation（design review passed）。
- [11.3.5.5-execution-evidence-result-reporter-adapter](./11.3.5.5-execution-evidence-result-reporter-adapter/) —— ExecutionEvidence & TaskResultReporter Adapter：新增 / 扩展执行证据 contract，在 runtime stop 前采集 DOM evidence，并把 replay result + page evidence 适配到保守结果回复。状态：ready_for_implementation（design review passed）。
- [11.3.5.6-wagent-chat-records-closed-loop-evaluation](./11.3.5.6-wagent-chat-records-closed-loop-evaluation/) —— WAgent Chat `/records` Closed-loop Evaluation：沉淀 `/records` 学习 / 执行闭环测试方案、实跑结果和日志复核记录。状态：implementation complete（closed-loop pass，result recorded）。
- [11.3.5.7-pending-choice-active-task-ledger](./11.3.5.7-pending-choice-active-task-ledger/) —— Pending Choice & Minimal Active Task Ledger：补多候选澄清、choice 私有映射、最小 active task 状态账本、pending 清理 / 过期和 cancel cleanup。状态：implementation complete（code review passed，targeted tests passed）。
- [11.3.5.8-basic-failure-recovery](./11.3.5.8-basic-failure-recovery/) —— Basic Failure Recovery：补基础失败恢复菜单：重试、重新学习、取消；不做复杂自治恢复。状态：implementation complete（code review passed，targeted tests passed）。
- [11.3.5.9-taskpathplanner-multi-candidate-chat-integration](./11.3.5.9-taskpathplanner-multi-candidate-chat-integration/) —— TaskPathPlanner Multi-candidate Chat Integration：只在多候选、模糊目标、planning path 中接入 TaskPathPlanner，不进入单路径 happy path。状态：implementation complete（code review passed，targeted tests passed）。
- [11.3.6-wagent-runtime-eval-program](./11.3.6-wagent-runtime-eval-program/) —— WAgent Runtime Eval Program：runtime eval 总体测试规划，定义 11.3.6.x 子包、artifact、exit code、hard gates 和 Codex 审计边界。状态：closed_pass_with_caveats（final closeout rerun pass）。
- [11.3.6.1-wagent-runtime-eval-runner-core](./11.3.6.1-wagent-runtime-eval-runner-core/) —— WAgent Runtime Eval Runner Core：实现 runner v1，覆盖 `/records` closed loop 和 single-path direct replay regression。状态：implemented_and_live_eval_passed。
- [11.3.6.2-failure-recovery-eval](./11.3.6.2-failure-recovery-eval/) —— Failure Recovery Eval：扩展 runner 覆盖 recovery menu safety、retry / relearn / cancel 出口和 private payload safety。状态：implementation_complete_verified（live Conversation eval pass）。
- [11.3.6.3-pending-choice-multi-candidate-eval](./11.3.6.3-pending-choice-multi-candidate-eval/) —— Pending Choice Multi-candidate Eval：扩展 runner 覆盖 A/B/C public choice、private map safety 和用户选择后执行正确 action。状态：implementation_complete_verified（pending-choice eval pass）。
- [11.3.6.4-planner-backed-choice-eval](./11.3.6.4-planner-backed-choice-eval/) —— Planner-backed Choice Eval：扩展 runner 覆盖 vague goal、TaskPathPlanner-backed choices 和 single-path bypass Planner 回归。状态：implementation_complete_verified（planner-backed choice and single-path bypass pass）。
- [11.3.6.5-runtime-eval-program-closeout](./11.3.6.5-runtime-eval-program-closeout/) —— Runtime Eval Program Closeout：核对 11.3.6.3 / 11.3.6.4 implementation、artifact、review closeout，并同步 11.3.6 program 状态。状态：completed_after_fix_rerun（final closeout rerun pass）。
- [11.3.6.6-runtime-eval-gate-failure-fixes](./11.3.6.6-runtime-eval-gate-failure-fixes/) —— Runtime Eval Gate Failure Fixes：修复 11.3.6.5 service-available rerun 暴露的 pending choice public payload leak、planner-backed choice selection no-execution 和 raw artifact redaction failures。状态：implementation_complete_verified（fixes implemented，final eval rerun pass）。
- [11.3.7-user-facing-wagent-behavior-eval](./11.3.7-user-facing-wagent-behavior-eval/) —— User-facing WAgent Behavior Eval：下一阶段用户视角验收，覆盖 URL-only、execute-known、execute-unknown、learn-explicit / vague-input 等入口行为，并加入测试页面细节不得进入功能代码或产品 prompt 的 hard gate。状态：pass（first-wave user-facing behavior gates passed，full learn-then-execute remains follow-up）。
- [11.3.8-external-black-box-validation-recovery](./11.3.8-external-black-box-validation-recovery/) —— External Black-box Validation Recovery：M11.3 post-closeout recovery follow-up / umbrella planning package，用于把外部黑盒验证失败拆成 11.3.8.x child packages；不是 implementation package。状态：PACKAGE_COMPLETE（final external black-box validation PASS）。
- [11.3.8.1-learning-action-goal-preservation](./11.3.8.1-learning-action-goal-preservation/) —— Learning Action Goal Preservation：保留 learning intake 中的 business goal、canonical goal、business object / match terms 和 useful aliases，避免 learned action identity 退化为 `Learn how to create`。状态：implementation_complete_pending_followup（metadata preservation implemented in HEAD；suggested utterances、matcher consumption、external black-box revalidation remain follow-up）。
- [11.3.8.2-suggested-utterance-generation](./11.3.8.2-suggested-utterance-generation/) —— Suggested Utterance Generation：基于已保留的 business goal / canonical goal / useful aliases 生成可复用 utterances，避免只保存教学 wrapper 变体。状态：PACKAGE_COMPLETE（deterministic utterance generation implemented；11 learning service tests and 89 chat runtime tests passed；external black-box validation not run）。
- [11.3.8.3-learned-action-matching-improvement](./11.3.8.3-learned-action-matching-improvement/) —— Learned Action Matching Improvement：执行阶段已消费 canonical goal、business goal、business object、aliases、match terms 和 reusable utterances，并保护 search/delete same-object、ambiguous、多 generic verb-only 和 object substring 场景。状态：PACKAGE_COMPLETE（95 chat runtime tests and 15 router tests passed；external black-box validation not run）。
- [11.3.8.4-regression-tests](./11.3.8.4-regression-tests/) —— Regression Tests：已创建七件套并通过 read-only design / safety review；已新增 target-agnostic repo-local regression，把 metadata、utterance、matcher 和 replay handoff 串起来。状态：PACKAGE_COMPLETE（122 focused tests passed；external black-box validation not run）。
- [11.3.8.5-external-black-box-revalidation-closeout](./11.3.8.5-external-black-box-revalidation-closeout/) —— External Black-box Revalidation / Closeout：final approved rerun PASS，latest result docs 已基于真实证据更新。状态：PASS。
- [11.3.8.6-slot-alias-and-form-binding-fix](./11.3.8.6-slot-alias-and-form-binding-fix/) —— Slot Alias & Form Binding Fix：修复 11.3.8.5 暴露的 slot alias / create-form field binding 缺口。状态：PACKAGE_COMPLETE。
- [11.3.9-conversation-debug-timeline](./11.3.9-conversation-debug-timeline/) —— Conversation Debug Timeline：把现有 Conversation History detail 升级为人能读懂的 `wagent chat` 运行轨迹，解释用户输入、路由、选项、LLM trace、learning/replay/recovery 等过程；不把 raw payload 倒进后端终端。状态：docs_generated_pending_design_review。
- [11.3.10-autonomous-filter-capability-learning](./11.3.10-autonomous-filter-capability-learning/) —— Autonomous Filter Capability Learning：M11.3 post-closeout umbrella / campaign package，修复 URL-only learning 在筛选页只学到单个搜索按钮的问题，并把学习反馈拆成 capability discovery 与 outcome gate 两个 child package。状态：children_complete_live_validation_not_run（repo-local non-live verification complete；等待用户授权 live `/users` validation）。
- [11.3.10.1-filter-capability-discovery-learning](./11.3.10.1-filter-capability-discovery-learning/) —— Filter Capability Discovery Learning：实现 product-level URL-only learning 的筛选控件 inventory、single / pairwise / all-supported scenario matrix、run history 和 LearnedPath evidence gate。状态：PACKAGE_COMPLETE（non-live tests passed；live autonomous validation not run）。
- [11.3.10.2-learning-outcome-gate-chat-feedback](./11.3.10.2-learning-outcome-gate-chat-feedback/) —— Learning Outcome Gate Chat Feedback：基于 11.3.10.1 的 aggregate capability result 实现 success / partial_success / failed / unverified 用户反馈、控制词过滤和 Ctrl+C 退出记录。状态：PACKAGE_COMPLETE（chat / CLI focused tests passed；live autonomous validation not run）。
- [11.3.11-terminal-state-agent-learning-stop-control](./11.3.11-terminal-state-agent-learning-stop-control/) —— Terminal State Agent Learning Stop Control：M11.3 post-closeout umbrella / campaign package，修复自主探索不知道 attempt 何时到达可评价终态的问题；规划 Terminal State Agent、Page Understanding terminal hints、browser event evidence、Attempt Evaluation / LearnedPath gate 和证据详情展示。状态：PACKAGE_COMPLETE（all six child packages complete；live autonomous validation not run）。
- [11.3.11.1-terminal-state-agent-contract-taxonomy](./11.3.11.1-terminal-state-agent-contract-taxonomy/) —— Terminal State Agent Contract Taxonomy：为 11.3.11 定义 terminal-state evidence taxonomy、scoped Terminal State Agent evaluator-worker 边界、product-model / roadmap 对齐、redaction/storage 方向和后续 child gate。状态：PACKAGE_COMPLETE（docs-only verification passed；runtime implementation not authorized）。
- [11.3.11.2-browser-event-recorder](./11.3.11.2-browser-event-recorder/) —— Browser Event Recorder：新增 target-agnostic browser event timeline、redaction、correlation_id / step action scope 和非 live 测试，为后续终态判断提供浏览器事件证据。状态：PACKAGE_COMPLETE（49 targeted tests passed；live autonomous validation not run）。
- [11.3.11.3-page-understanding-terminal-hints](./11.3.11.3-page-understanding-terminal-hints/) —— Page Understanding Terminal Hints：新增 deterministic PageAnalysis terminal hints、candidate terminal states、PageTerminalHintSet schema 和非 live 测试，为后续 stop control 提供页面语义提示。状态：PACKAGE_COMPLETE（27 targeted tests passed；live autonomous validation not run）。
- [11.3.11.4-terminal-state-agent-stop-control](./11.3.11.4-terminal-state-agent-stop-control/) —— Terminal State Agent Stop Control：新增 deterministic advisory terminal-state classifier、`TerminalStateVerdict`、stop/wait/continue/unverified_stop 元数据和非 live 测试；不改变 pass_gate、Supervisor、LearnedPath ingest 或真实等待循环。状态：PACKAGE_COMPLETE（35 targeted tests passed；live autonomous validation not run）。
- [11.3.11.5-attempt-evaluation-ingest-gate](./11.3.11.5-attempt-evaluation-ingest-gate/) —— Attempt Evaluation Ingest Gate：定义并实现 deterministic AttemptIngestEvaluation gate，确保 terminal_unverified / terminal_failed / missing terminal evidence 不会沉淀为成功 LearnedPath。状态：PACKAGE_COMPLETE（43 targeted tests passed；live autonomous validation not run）。
- [11.3.11.6-evidence-console-and-regression-suite](./11.3.11.6-evidence-console-and-regression-suite/) —— Evidence Console and Regression Suite：在 Console run detail 展示 persisted terminal / ingest evidence summary，并补 API/detail、组件、build 回归。状态：PACKAGE_COMPLETE（87 API tests passed；158 console tests passed；console build passed；live autonomous validation not run）。
- [11.3.12-bounded-learning-composable-capability-assets](./11.3.12-bounded-learning-composable-capability-assets/) —— Bounded Learning and Composable Capability Assets：M11.3 post-closeout umbrella / campaign package，定义 LearnedCapability 原子学习资产、bounded learning policy、learning batch lifecycle 和 code-owned capability composition；父包不直接授权实现，四个 child packages 已完成 repo-local closeout，live validation 未运行。状态：PACKAGE_COMPLETE。
- [11.3.12.1-learned-capability-asset-foundation](./11.3.12.1-learned-capability-asset-foundation/) —— LearnedCapability Asset Foundation：新增 LearnedCapability 资产层的 schema / model / repo / migration / compatibility foundation；不改变学习批次、bounded planner、chat timeout 或 runtime composition。状态：PACKAGE_COMPLETE（18 targeted tests passed；64 LearnedPath regression tests passed；offline Alembic SQL generation passed；online DB migration unverified due local env）。
- [11.3.12.2-bounded-learning-batch-lifecycle](./11.3.12.2-bounded-learning-batch-lifecycle/) —— Bounded Learning Batch Lifecycle：新增 durable `LearningBatch` / bounded policy / cancel-timeout-detach 语义、LearningRunService batch closeout、chat batch metadata 和 repo-local regression；状态：PACKAGE_COMPLETE（140 focused tests passed；82 compatibility tests passed；scoped ruff passed；offline Alembic SQL generation passed；online DB migration unverified due local env）。
- [11.3.12.3-page-understanding-capability-hints](./11.3.12.3-page-understanding-capability-hints/) —— Page Understanding Capability Hints：新增 redacted `CapabilityHintSet` schema、PageAnalyzer hint 输出、hint-aware capability discovery、schema-level redacted-ref validation 和 focused regression；状态：PACKAGE_COMPLETE（58 scoped tests passed；scoped ruff passed；hardcoding scan reviewed；live validation not run）。
- [11.3.12.4-capability-composition-runtime](./11.3.12.4-capability-composition-runtime/) —— Capability Composition Runtime：定义 deterministic composition plan、candidate compatibility、LearnedPath preference、private execution handoff 和 promotion guard；状态：PACKAGE_COMPLETE（227 scoped tests passed；scoped ruff passed；hardcoding scan reviewed；live validation not run）。
- [11.3.13-learning-batch-browser-session-reuse](./11.3.13-learning-batch-browser-session-reuse/) —— Learning Batch Browser Session Reuse：M11.3 post-closeout mixed design package，优化 product-level learning batch 内 `ExecutionRuntime` 生命周期，让 seed analysis 和 scenario loop 复用同一个 visible Playwright Chromium，并在 batch terminal 后统一关闭，避免每个 scenario 反复弹窗。状态：docs_generated_pending_design_review（implementation not authorized）。

`11.0-runtime-conversation-shell-orchestration/` 是 M11.0 总纲目录，不是
一次性施工包。具体实现拆到 `11.0.x-*` 执行包；每个执行包都必须独立维护
`intent.md`、`plan.md`、`review.md`，并且每次只施工当前包。
`11.2-runtime-observation-realistic-hardening/` 是 M11.2 总纲和 11.2.0
文档初始化目录，不代表 runtime observation 功能已经实现。
`11.2.1-observation-signal-contract/` 只定义文档级 Observation Signal Contract，
不代表 wait-for-change、page-load waiting 或 reporter integration 已实现。
`11.2.2-wait-for-change-mvp/` 已完成最小 step-level wait result 能力，但当前只支持
`url_changed`、`title_changed` 和 supporting-only `network_idle_observed`。
它不代表 page-load waiting、Agent 判断或 reporter integration 已实现。
`11.2.3-replay-integration-with-observation/` 已完成 replay-level observation
evidence aggregation 代码实现：schema、aggregation service、replay integration
和 56 个 scoped tests。11.2.3 不接 Task Result Reporter，不做 recovery / retry /
abort。
`11.2.4-realistic-scenario-catalog-fixture-planning/` 只规划 WebAgentFlow 自建
真实网页验证场景库。它定义 PC / 移动端 scenario catalog、复杂度分层、Phase 1
单页面 fixture、Phase 2 mock backend 和后续 E2E evidence 路线；不代表 fixture
页面、mock backend 或 E2E 已实现。
`11.2.4.1-single-page-runtime-fixture-shell/` 已实现 runtime observation fixture
shell 的入口、route namespace、fixture metadata、stable anchor 和 reset convention。
它不代表具体业务 fixture 页面、mock backend 或 E2E 已实现。
`11.2.4.2-single-page-basic-business-pages/` 已按 `fixture-designs/*.md` 页面级设计文档
重做 `/runtime-observation/basic/*` 下的 7 个 PC basic business fixtures。当前实现采用
shared shell + per-fixture components，保持 frontend-local deterministic error scope；
不接 mock backend、replay、reporter 或 M12 recovery。
`11.3.1-visible-chat-browser-operation/` 是 11.3 interactive chat 的收尾增强。它已实现
`wagent chat` 学习和执行网页操作时默认打开用户可见的项目内置 Playwright Chromium，
并允许用户通过 `--headless` 选择后台运行。该能力不绑定具体页面；具体页面只作为
测试计划中的验收样例。当前 scoped CLI / API tests passed，真实可见浏览器人工 smoke
尚未在 review 中记录。
`11.3.2-chat-history-debug-console/` 是 11.3 interactive chat 的可观察性和调试入口补齐。
它不新增聊天 / 学习 / 执行能力，而是把已有 conversation sessions、messages、events 和
session metadata 产品化为 history list、aggregate history detail、Console 页面以及 CLI debug
命令，方便人工测试和 Codex CLI 复用历史会话继续调试。
`11.3.3-product-chat-test-site-separation/` 是 11.3 interactive chat 的产品级验收边界
拆分包。它已新增 `apps/fixture-site`，端口 `<fixture-port>`，并把 product-level
`wagent chat` learning 从 validation specs / `spec_id` / `scenario` oracle 中拆出。
根 `pnpm run dev` 已接入 fixture-site；product-level CLI smoke 已通过，session
`20602dde-1a64-4e81-8784-9b7949a9d866` 沉淀 LearnedPath
`03fb1fa1-2589-45cf-8322-4ba3f2809077` 并成功 replay 到 `/workspace-home`。
它不迁移 `11.2.4.2`，也不覆盖 `11.3.2`。
`11.3.4-conversation-intake-agent/` 是 11.3 interactive chat 的自然语言入口补齐包。
它新增并实现产品模型角色 Conversation Intake Agent / 对话理解 Agent，但不让 LLM 直接操作浏览器。
本包实现 schema-constrained intake、pending_intake、redaction、Orchestrator guardrails、
response provenance 和 redacted LLM trace history；
后续实现必须保持 “LLM 理解用户语言，代码校验和执行” 的边界。本包也包含 response provenance
/ LLM trace 要求：`/conversation/history/:session_id` 应能显示每条 WAgent 回复的生成来源，
包括代码路径、内部 Agent role、LLM provider / model / trace，以及脱敏后的 raw record。
Codex CLI 是外部开发 / 测试 Agent，不是产品内部 Reply Producer。
`11.3.5-customer-facing-agent-router-skill-runtime/` 是 11.3 interactive chat 的面客
Agent 路由与应用技能运行时设计包。它把裸 URL、短句续接和 no-path 学习引导上升到
Router / Orchestrator / Skill Runtime 责任边界：Customer-Facing Agent Router 只建议
下一步交给谁，Conversation Orchestrator 代码侧裁决能否执行，Skill Runtime 调用
已注册应用能力。该包明确复用 HTML AST、Simplified AST、PageAnalysis、ExplorationRun steps、
LearnedPath actions、replay observation、task planning schemas 和 response provenance；
不实现 active browser tab，不让 LLM 直接操作浏览器，不让 Router 直接调用 skill。
`11.3.5.1-conversation-entry-gate-latency-ux/` 是 11.3.5 的 patch-level 入口体验优化。
它不新增 Agent 角色，不改 Skill Runtime 主架构；只在 Intake / Router 前增加轻量
Conversation Entry Gate，并要求 CLI 在等待 API 返回期间显示持续 working 状态。
非网页消息应快速友好回复并引导用户回到 WebAgentFlow 的网页操作能力；网页任务候选
继续进入 11.3.5 runtime。
`11.3.6-wagent-runtime-eval-program/` 是 11.3 working runtime 的本地验收体系总纲。
它不实现 runner，而是定义 11.3.6.x 子包路线：11.3.6.1 做 runner core 和 `/records`
两条核心回归，11.3.6.2 / 11.3.6.3 / 11.3.6.4 后续分别扩展 failure recovery、
pending choice 和 planner-backed choice eval。Codex 在该体系中只做 artifact 审计员，
不作为 pass / fail 裁判。11.3.6 closeout 的 `pass_with_caveats` 只表示受控 runtime
执行能力通过：已学路径参数化复用、evidence reporting、pending choice、planner-backed
choice 分支和 basic recovery menu；它不代表 WAgent 已经具备页面级自动能力发现、
自动学习所有操作、自动生成完整操作库或面对任意新任务自动命中并执行的产品能力。
`11.3.6.1-wagent-runtime-eval-runner-core/` 承接原 11.3.6 runner 设计，负责第一版
可执行 runner。它通过 Conversation API 一次性运行 `/records` closed loop 和 single-path
direct replay regression，按 hard gates 写出 JSON / Markdown 证据，并用 exit code 表示
验收结果。
`11.3.6.2-failure-recovery-eval/` 是 11.3.6 program 的第二个执行包。它已在
runner core 上增加 `failure_recovery_menu_safety`，用 eval-only hook 验证
11.3.5.8 recovery menu 和 private payload redaction；首版不把 retry execution 成功作为
required gate，也不调用 autonomous-run endpoints。最终 closeout rerun 已通过 live
Conversation eval。
`11.3.6.3-pending-choice-multi-candidate-eval/` 是 11.3.6 program 的第三个执行包。它计划在
runner core 上增加 `pending_choice_multi_candidate`，用当前 eval run 的多候选 setup
验证 11.3.5.7 pending choice public payload、private map safety 和选择 A 后执行正确 action；
planner-backed choice 留到 11.3.6.4。最终 closeout rerun 已通过，状态：
`implementation_complete_verified`。Caveat：当前 setup 为 eval-only candidate binding，
不证明 `/records` 已有三个真实 distinct product actions。
`11.3.6.4-planner-backed-choice-eval/` 是 11.3.6 program 的第四个执行包。它计划在 runner
core 上增加 `planner_backed_choice`，验证 11.3.5.9 TaskPathPlanner-backed choice path、
sanitized planner events、private payload safety，以及单路径明确目标必须 bypass Planner 的回归。
最终 closeout rerun 已通过，状态：`implementation_complete_verified`。Caveat：
`planner_top_choice_observable` 仍是非 required `not_observable` warning，且 planner setup
为 eval-only candidate binding。
`11.3.6.5-runtime-eval-program-closeout/` 是 11.3.6 program 的收口扫尾包。它不新增 runner
case，也不修 runtime；它用于运行或记录 pending-choice / planner-choice eval、补齐 result artifact、
回填 11.3.6.3 / 11.3.6.4 review，并同步 11.3.6 program 与 M11 索引。状态：
`completed_after_fix_rerun`。最终 rerun 中 items、failure recovery、pending choice、
planner choice 均返回 exit `0`。
`11.3.6.6-runtime-eval-gate-failure-fixes/` 是上述失败后的代码型 fix 文档包。它不新增
eval case，也不扩大产品能力；只要求修复 pending choice public/private payload separation、
planner-backed choice selection 到 execution 的 runtime 连接，以及 eval runner artifact redaction。
本包已实现并通过最终 rerun；同时修复了最终 items rerun 暴露的 complete-intake ask flag
normalization 缺口。
`11.3.7-user-facing-wagent-behavior-eval/` 是 11.3.6 之后的用户视角验收包。它要验证的不是
底层 slot / reporter / recovery 零件，而是普通用户输入进入时，WAgent 是否知道该查 learned
actions、该学习、该执行、该追问、该拒绝乱来，以及执行后是否基于 evidence 回复。第一批
case 聚焦 URL-only known / unknown、unknown 后选择学习必须进入真实 learning flow、
execute-known、execute-unknown、execute-unknown 后选择 learn / learn-then-execute、
vague-input 和 forbidden target scan；后续再扩展 explicit learn、pending continuation、
choice selection、failure recovery 和受控 page capability learning。该包加入 hard gate：
测试页面链接、route、页面文案、按钮名、字段名、DOM test id、fixture item names 和
operation aliases 不得进入功能代码或产品 prompt，只能存在于 fixture、eval spec、测试、
docs 和 artifact 中；当前已有 fixture-site runtime 特判也必须清理，未清理则 11.3.7
只能 blocked，不能 pass。
该包已通过 first-wave user-facing behavior eval：latest artifact 记录 commit `e91c0f5`，并在
`79156d8` 中刷新 artifacts / review / testing result。通过范围只覆盖第一批用户入口行为、
known / unknown isolation、forbidden-target scan、public redaction 和 Conversation API 边界；
不声明完整页面全量自动能力发现、批量学习所有操作或任意任务自动执行能力。
`11.3.8-external-black-box-validation-recovery/` 是 11.3.7 之后的 M11.3
post-closeout recovery follow-up / umbrella planning package。它承接
`docs/testing/results/external-black-box-validation-latest.md` 和
`docs/testing/results/pv-cli-003-failure-triage-20260525.md` 中记录的外部黑盒验证
失败：`PV-CLI-002` 学习完成但 action label 过于泛化，`PV-CLI-003` 尚未修复，
执行新值时没有匹配到已学 create inventory item action。该父包把修复拆成
`11.3.8.1` 到 `11.3.8.5` 的 child package sequence，但父包本身不授权 runtime
代码修改。`11.3.8.1-learning-action-goal-preservation/` 是第一个 child code package；
当前状态为 `implementation_complete_pending_followup`，HEAD 已包含学习完成后 session
learned action metadata 保存 `business_goal`、`canonical_goal`、business object /
`match_terms` 和 useful aliases 的 scoped implementation。`11.3.8.2-suggested-utterance-generation/`
当前已完成 deterministic reusable utterances，覆盖 full business phrase、slot-value
exclusion、truncated-wrapper repair 和 clean utterance preservation。它不修 matcher、
不跑外部黑盒重验。

`11.3.9-conversation-debug-timeline/` 是 M11.3 post-closeout 的 observability /
debug UX follow-up。它承接 `11.3.2-chat-history-debug-console/` 已有 history list/detail
基础，但目标更窄：把 raw messages / events / traces 翻译成后台详情页中的人类可读运行轨迹，
让用户和开发者理解 `wagent chat` 当前在理解什么、为什么等待用户选择、为什么产生某个回复。
本包不新增 runtime 行为、不新增内部 Agent、不改变 learning / replay / recovery 语义，
也不把完整 LLM request / response 或 private payload 打到后端终端。

`11.3.10-autonomous-filter-capability-learning/` 是 M11.3 post-closeout 的第二个
umbrella / campaign package。它不把当前问题当成单句文案 hotfix，而是把 URL-only
learning 在筛选页上只沉淀一个搜索按钮 LearnedPath 的缺口拆成两个 child package。
`11.3.10.1-filter-capability-discovery-learning/` 已补 L1 autonomous learning 的
filter capability discovery、scenario matrix、run history 和 LearnedPath evidence gate；
`11.3.10.2-learning-outcome-gate-chat-feedback/` 已基于 child 1 的 aggregate result
判断 success / partial_success / failed / unverified，并修复“开始学习”等控制词污染
learned action identity 的问题。两个 child package 已完成 repo-local non-live
verification；真实 `/users` live autonomous validation 尚未运行，需用户明确授权。

`11.3.11-terminal-state-agent-learning-stop-control/` 是 M11.3 post-closeout 的第三个
umbrella / campaign package。它承接 11.3.10 暴露出的更深层问题：筛选页、导出、弹窗、
静默刷新等场景下，L1 autonomous exploration 不知道一次 attempt 何时已经到达可评价终态。
本包完成 `Terminal State Agent / 终态判断 Agent` 边界、Page Understanding terminal hints、
browser event timeline、post-action advisory terminal verdict、Attempt Evaluation / LearnedPath gate 以及
LearnedPath / run history 证据详情入口。`11.3.11.1-terminal-state-agent-contract-taxonomy`
已完成 docs/product-model/roadmap alignment closeout；`11.3.11.2-browser-event-recorder`
已完成 target-agnostic browser event timeline 和非 live tests；`11.3.11.3-page-understanding-terminal-hints` 已完成 deterministic terminal hints
和非 live tests；`11.3.11.4-terminal-state-agent-stop-control` 已完成 advisory terminal-state
classifier 和非 live tests；`11.3.11.5-attempt-evaluation-ingest-gate` 已完成 deterministic ingest
gate 和非 live tests；`11.3.11.6-evidence-console-and-regression-suite` 已完成 evidence display
和 regression closeout。11.3.11 campaign complete；live autonomous validation not run。
运行时代码仍必须等待对应 child 七件套、设计复核和 `implementation_authorized: yes`。
该能力未来可被 M14 learning quality / negative knowledge 复用，但当前执行路由属于
M11.3 post-closeout。

11.2 后续 backlog：

- 治理 `execute_action()` / `wait_for_change_after_action()` 的重复等待，避免
  action executor 和 observation layer 双重等待拖慢多 step replay。
- 在 11.2.5 Task Result Reporter 消费前细化 observation count 语义，例如
  `wait_observed_step_count`、`primary_observed_step_count`、
  `supporting_only_step_count`。

## Later M11.2.x · Common Component Runtime Semantics

M11.2 后续应补充常用组件库运行时语义兼容。该方向不是 popup support，而是
component-generated runtime surface detection and relation：在 replay action 后，
识别由常用组件库生成或改变的运行时界面片段，并尽可能把新出现或变化的 runtime
surface 与触发它的 action / element 关联起来。

runtime surface 可以是 dropdown、select option panel、autocomplete panel、
cascader panel、date picker、time picker、popover、tooltip、modal、dialog、
drawer、toast、message、notification、action sheet、bottom sheet、mobile picker、
loading overlay、validation message、virtualized list、inserted option list，
也可以只是 active / selected / checked / disabled / enabled 状态变化。

后续实现原则：

- 优先使用 DOM insertion / removal、visibility change、aria-expanded、
  aria-controls、aria-owns、role=listbox / option / menu / dialog / tooltip、
  selected / checked / disabled / active state、bounding rect proximity、
  insertion timing relative to action、focus movement、active descendant 等通用
  Web 信号。
- 组件库 class 只作为 supporting evidence，例如 `ant-select-dropdown`、
  `el-select-dropdown`、`n-select-menu`、`arco-select-popup`、
  `t-select__dropdown`、`van-popup`、`van-action-sheet`、`nut-popup`、
  `adm-popup`，不能作为唯一依据。
- 后续兼容范围同时覆盖 PC / 管理后台组件库和移动端组件库。
- 不调用 Agent 判断业务成功，不让 LLM 进入 L3 per-step execution loop。
- 不阻塞 11.2.2 最小 wait_result / wait_strategy 实现。

## Later M11.x · Page Context Bridge Decision Point

M11.2 / M11.3 完成后，可以根据实际验证结果决定是否插入一个小型 later
M11.x。这个条目是候选决策点，不是已确定执行包。

候选方向是 Page Context Bridge / 页面语义上下文桥接。它不是完整 M14，
也不是完整 Page Understanding Agent 提前实现。

如果 M11.2 收口后发现主要瓶颈不是“执行和观察”，而是 learned path 的业务语义
太弱、Task Path Planner 缺少页面上下文、Task Result Reporter 汇报像执行日志、
或 execution evidence 有了但缺少页面级语义解释，可以考虑该候选点。

候选目标：

- 定义轻量 Page Context Contract。
- 从已有 LearnedPath metadata、page_template、scenario、route plan、observation
  evidence 中整理页面上下文。
- 为 Task Path Planner 和 Task Result Reporter 提供轻量语义上下文。
- 不要求 L3 实时读取 raw HTML。
- 不让 LLM 进入 per-step execution loop。

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
