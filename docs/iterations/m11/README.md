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
- [11.2.2-wait-for-change-mvp](./11.2.2-wait-for-change-mvp/) —— Wait-for-change MVP。状态：最小代码实现完成，scoped review passed；full API suite 需在非 sandbox 环境补跑。
- [11.2.3-replay-integration-with-observation](./11.2.3-replay-integration-with-observation/) —— Replay Integration with Observation。状态：implementation complete（55 scoped tests passed, 1167 full API tests passed, ruff clean）。
- 11.2.x · Common Component Runtime Semantics（常用组件库运行时语义兼容）—— later M11.2.x 候选增强；记录组件库生成的 runtime surface detection and relation，不属于 11.2.2 当前 MVP。

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
和 55 个 scoped tests。11.2.3 不接 Task Result Reporter，不做 recovery / retry /
abort。

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

## Possible M11.3 · Page Context Bridge Decision Point

M11.2 完成后，可以根据实际验证结果决定是否插入一个小型 M11.3。这个条目是
候选决策点，不是已确定执行包；本轮不创建 11.3 目录。

M11.3 的候选方向是 Page Context Bridge / 页面语义上下文桥接。它不是完整 M14，
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

M11.3 不做：

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
