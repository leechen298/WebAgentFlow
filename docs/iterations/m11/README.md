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
- [11.2.4.1-single-page-runtime-fixture-shell](./11.2.4.1-single-page-runtime-fixture-shell/) —— Single-page Runtime Fixture Shell。状态：完成（validation-site runtime observation shell / route / index entry implemented）。
- [11.2.4.2-single-page-basic-business-pages](./11.2.4.2-single-page-basic-business-pages/) —— Single-page Basic Business Pages。状态：implementation complete, review pending；当前已按页面级 fixture designs 重做 7 个 PC basic fixtures。
- 11.2.x · Common Component Runtime Semantics（常用组件库运行时语义兼容）—— later M11.2.x 候选增强；记录组件库生成的 runtime surface detection and relation，不属于 11.2.2 当前 MVP。
- [11.3-interactive-chat-closed-loop](./11.3-interactive-chat-closed-loop/) —— Interactive Chat Closed Loop：`wagent chat` 小白用户闭环，当前只覆盖 `/login` happy path。状态：accepted（implementation review passed, manual smoke passed）。
- [11.3.1-visible-chat-browser-operation](./11.3.1-visible-chat-browser-operation/) —— Visible Chat Browser Operation：`wagent chat` 默认以用户可见的项目内置 Playwright Chromium 学习和执行网页操作，支持 `--headless` opt-out。状态：implementation complete（scoped tests passed, manual visible-browser smoke pending）。
- [11.3.2-chat-history-debug-console](./11.3.2-chat-history-debug-console/) —— Chat History & Debug Console：补 Conversation session list、aggregate history、Console history 页面、CLI list/history/resume，服务人工测试和 Codex CLI 调试复用。状态：implementation complete（implementation review passed, UI smoke pending）。
- [11.3.3-product-chat-test-site-separation](./11.3.3-product-chat-test-site-separation/) —— Product-Level Chat Test Site Separation：拆分 validation-site 工程验证靶场与 product-test-site 产品级 chat 人工验收靶场，避免 validation spec / assertion oracle 污染 `wagent chat` 产品路径。状态：accepted（implementation review passed, product-level CLI smoke passed）。
- [11.3.4-conversation-intake-agent](./11.3.4-conversation-intake-agent/) —— Conversation Intake Agent：为 `wagent chat` 定义并实现 schema-constrained 自然语言入口层，让 LLM 理解用户话语并输出结构化 intent / target / action / slots / missing fields，代码继续负责校验和执行；同时 Conversation History detail 展示 WAgent 回复来源和脱敏 LLM trace。状态：implementation complete（scoped tests passed, real LLM smoke pending）。
- [11.3.5-customer-facing-agent-router-skill-runtime](./11.3.5-customer-facing-agent-router-skill-runtime/) —— Customer-Facing Agent Router & Skill Runtime：把 chat recovery 问题扩展为面客 Agent 路由与应用技能运行时，定义 Router / Orchestrator / Worker Agent / Application Skill Registry 边界，复用 AST、PageAnalysis、LearnedPath 和 replay evidence。状态：proposed（docs generated, implementation not started）。

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
拆分包。它已新增 `apps/product-test-site`，端口 `5176`，并把 product-level
`wagent chat` learning 从 validation specs / `spec_id` / `scenario` oracle 中拆出。
根 `pnpm run dev` 已接入 product-test-site；product-level CLI smoke 已通过，session
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
