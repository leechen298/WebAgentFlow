# 路线图

运营视角下"已交付 / 正在做 / 下一步"的全景。

- 产品**是什么**（L1/L2/L3 生命周期阶段、产品内部 Agent A-H、跨阶段不变量）见
  [`product-model.zh.md`](./product-model.zh.md) —— 权威产品参考。
- 迭代目录使用 `docs/iterations/m10/` 这类里程碑路径。路线图正文使用
  **交付里程碑 M<N>**，避免和生命周期阶段 L1/L2/L3 混淆。
- 历史 12 步架构时间线请见 [`architecture.zh.md`](./architecture.zh.md) §E。

## 已交付（基础设施 + 自主探索子系统）

2026-04-20 清理之后，仓库里唯一的产品表面就是**基于 Playwright 的
自主探索管线**。早期迭代（录制、Chrome 扩展、任务驱动探索、技能 /
执行记录 / 学习调试 UI）已经从代码中移除 —— 见
`memory/project_legacy_stack_removed.md`。12 步历史时间线
见 [`architecture.zh.md`](./architecture.zh.md) §E。

基础设施：

- 服务端 HTML → Full AST（`html_ast_parser.py` + `ast_simplifier.py`，
  用 `lxml`）
- Playwright chromium 生命周期封装
  （`services/execution/execution_runtime.py`）
- 自建 validation-site（`apps/validation-site/`）+ mock
  `/validation-api` 后端

自主探索管线（端到端）：

- `page_analyzer.py` —— 实时页面元素发现（纯结构分类；Ant Design 5
  的 `css-dev-only-do-not-override-<hash>` 在兜底 selector 中被跳过）
- `action_planner.py` —— 规则驱动的多字段规划器，按语义角色匹配
  （username / password / email / search / text / name / role / status）
- `autonomous_explorer.py` —— 编排器 + SSE 事件分发 +
  `_run_supervisor` LLM 调用
- `supervisor_observations.py` —— LLM 只产出观察原子，verdict 在代码
  侧推导；`pass_gate` 三态（`pass` / `fail` / `unverified`）
- `page_verification.py` —— 基线对照器，5 项独立评分
- `routers/exploration.py` —— `/autonomous-runs[/stream]`、
  `/specs[/{id}]`、`/autonomous-runs[/{run_id}]`、`/screenshots/{file}`
- 持久化：每次 run 都写入 `exploration_runs` 表，
  `strategy_json.kind = "autonomous"` + `spec_id / scenario / verdict`

操作员界面：

- Autonomous Workbench（`/exploration/autonomous`）—— 7 个区块：
  运行配置 / 实时 SSE 状态 / 页面分析 / 执行时间线 /
  验证（self + supervisor + 5 项评分卡）/ 来源标识 /
  SSE 原始事件审计（带复制）
- 运行历史（`/exploration/autonomous/history`）—— 列表 + 详情页
  （详情页复用 workbench 的区块）
- 透明化：Supervisor `<think>` 推理轨迹可见；每个 SSE 事件都在审计
  面板里；截图支持点击放大
- Supervisor 语言感知（UI 当前语言透传给 LLM prompt）
- 三态最终结论通过 `pass_gate` 暴露 —— `pass` 需要 LLM 高置信度 +
  规则全绿；其他都落到 `unverified` 或 `fail`

对外入口：

- `wagent` CLI（`apps/cli/`）+ `verify-scenario` Claude Code skill
  —— 一次性触发一次 run，把 supervisor 结论 + 评分卡 + `run_id` 以
  结构化 JSON 返回

已写好的 spec：

- `login.{valid_credentials, invalid_credentials}`
- `users.{filter_by_name, filter_by_status, no_match}`

## 历史交付 M9 —— 已于 2026-04-21 关闭

主题：自主探索 + 用户驱动验证。关门验证：2026-04-21 通过
`verify-scenario` skill 把 5 个 scenario 各跑了一次，全部
`pass_gate = pass`，supervisor.source 均为 `llm`，5 项评分卡全
`1.0`（element_recognition / action_coverage / verdict_accuracy /
distraction_avoidance / supervisor_agreement）。run_id 都在
`exploration_runs` 表里。

M9 期间值得记的里程碑：

- [x] Run 落库 + workbench 按 spec 预填 + 自由 scenario key。
- [x] 登录页用户验证 —— `valid_credentials` 与 `invalid_credentials`
  两个 scenario 均 5/5（2026-04-18）。
- [x] 第二个 fixture —— `users`（用户目录）：
  - UI 侧用了一整套 Ant Design 企业级搜索表单
    （文本框、select、radio group、date 输入、Cascader、
    DatePicker、RangePicker、MonthPicker、TimePicker、
    Tag 筛选）+ 带列 sort / filter 的 Ant Design Table。
  - Spec 侧覆盖 `filter_by_name`、`no_match`、`filter_by_status`
    —— 文本输入 + Search 按钮，加一个原生内联非文本控件
    （radio group），证明 planner 不止能驱动 text 输入。
  - 弹层式控件（Cascader、所有 Picker 变体、Tag 筛选、表头列
    sort / filter）**故意**只摆在页面上、**不**写 scenario，
  它们的正式 scenario 已迁入 M14 覆盖 backlog。
- [x] Tier A 打磨：selector 构造器跳过 Ant Design 5 的
  `css-dev-only-do-not-override-<hash>` class；`no_match` 在空状态
  占位行修掉后重新验过。
- [x] Tier B 打磨：运行历史页（列表 + 详情）；语义角色分类器
  新增 `name` / `role` / `status` 三个桶。
- [x] Supervisor 观察原子化重构 —— LLM 只吐观察原子、verdict 由
  代码推导；`pass_gate` 三态（`pass` / `fail` / `unverified`）
  在 UI + CLI 都能看到。
- [x] 老功能清理（2026-04-20）—— 录制 / 技能 / 执行记录 / Chrome
  扩展 / 任务驱动探索从代码、数据库、文档中一并移除；
  在当时的清理点上，仅保留 `exploration_runs`；M10 后续新增了
  `learned_paths`。

M9 没有剩余待办。M10 现已关闭；下一步交付里程碑是 M11.0。

## M10 —— Path Asset Foundation / 路径资产基础（已于 2026-05-08 完成）

M10 已经让 LearnedPath 成为可复用资产。它仍然是基础里程碑，不是 L3
task runner：不做运行时 conversation shell、不做 Agent D Path Planner、
不做 Agent H Teaching Guide Agent，也不做 task-to-path 执行闭环。它
搭建的是 M11 会调用的确定性执行底座。

- **LearnedPath 落库 —— 已于 2026-04-25 交付（10.1）**。
  `pass_gate = pass` 的运行自动写入 `learned_paths`，按
  `(page_template, query_signature, dom_fingerprint, scenario)` 归档，
  并带 `provisional` / `confirmed` / `flaky` / `deprecated` 四态 trust。
  迭代记录：
  [`docs/iterations/m10/10.1-learned-path-persistence/`](./iterations/m10/10.1-learned-path-persistence/)。
  端到端证据：`run_id=6c97c030-5aae-4f93-8abd-91c4446df9d7`
  -> `learned_path_id=31d3cf58-65a8-4298-bafc-9feee1ed6a90`，
  scorecard 5/5，supervisor source `llm`。
- **LearnedPath catalog —— 已交付（10.1.5）**。
  console 已有资产级 LearnedPath catalog，用来查看路径、source run、
  已存 actions 和 trust 状态。路径级 trust 操作放在 catalog；run
  history 继续区分 run review 和只读 LearnedPath 关联。
- **Replay execution + drift detection —— 已交付 / 已于 2026-05-08 完成（10.2）**。
  用户从 LearnedPath catalog 指定一条路径，输入 URL，让引擎按已存
  actions 重跑。结果返回 replay status 和页面变化原因，例如 page
  mismatch、signature changed、target missing、unsupported action。
  这不是 `pass_gate`，不是 Supervisor verdict，也不是任务规划。

M10 收口时，LearnedPath 已经可以持久化、进入 catalog、执行 trust 操作、
显式 replay，并返回可解释 drift。deterministic E2E 已建立并通过
（`pnpm run test:e2e`，9 passed）。Codex exploratory validation 已完成
首轮证据报告（`PASS 12 / FAIL 0 / BLOCKED 0 / NOT_RUN 4`）。10.2 replay /
drift 结果未来会成为 failure evidence 和 drift evidence 的来源，但 10.2
本身没有实现完整 negative knowledge store。

下一步：**M11.0 Runtime Conversation Shell & Agent Orchestration / 运行时沟通与 Agent 编排**。

## M11.0 —— Runtime Conversation Shell & Agent Orchestration / 运行时沟通与 Agent 编排

M11.0 建立第一版运行时产品入口，让用户可以和 WebAgentFlow 沟通。这个
阶段 CLI 即可，因为目标是先跑通完整功能闭环，再打磨更丰富的操作员
界面。

预期交付：

- CLI-first 的运行时沟通入口；用户和 **WebAgentFlow** 沟通，而不是
  直接和 Agent D / E / F / G / H 沟通。
- 代码侧 Conversation Orchestrator / Dispatcher，维护 session state，
  并把用户消息和 engine events 路由到 Agent D / E / F / G / H 边界；
  这些能力随对应里程碑逐步上线。
- 支持任务输入、确认、暂停、继续、abort、takeover 的基础消息或命令。
- 先服务 M11.1 快乐路径，同时为 M12 恢复 / 中断对话和 M13 教学流程
  铺好状态结构。
- 统一从 WebAgentFlow 视角输出给用户。

这是运行时产品入口。它不是 M16 external CLI / API surface，也不是当前
`verify-scenario` 开发验证工具。

## M11.1 —— Task-to-Path Planning & Execution MVP / 任务到路径规划与执行 MVP

M11.1 是第一版 L3 实际工作里程碑。用户通过 M11.0 conversation surface
描述任务；WebAgentFlow 从已学路径中选择并绑定参数，通过 M10 replay
engine 执行，在能力范围内验证任务结果，然后汇报结果。

纳入 / 明确的产品内部 Agent：

- **Agent D · Path Planner Agent / 路径规划 Agent** —— 读取用户任务和
  学习数据，选择 / 组合路线，把任务参数绑定到可替换 action value，
  并且绝不读取 raw HTML。
- **Agent E · Result Reporter Agent / 结果报告 Agent** —— 读取执行结果、
  postcondition check、artifact status 和 final-state signals，输出
  用户可读报告和 UI 可渲染结构化字段。

预期交付：

- LearnedPath 检索和排序。
- Slot binding：把姓名、日期、状态、导出格式、搜索词等任务参数填入
  学过的动作值。
- planner 路线或绑定参数不确定时，执行前让用户确认。
- 通过 M10 replay engine 执行，不走 autonomous exploration。
- task result verification MVP：postcondition check、artifact status、
  final-state signals；无法验证时明确报告 `uncertain` / `needs review`。
- basic artifact capture / return：下载文件、导出、截图、最终 artifact
  reference。
- action risk & consent gate MVP：危险、不可逆、外部发送、批量修改、
  权限修改或用户自定义敏感操作，在执行前需要确认。

第一版 risk gate 可以由 Orchestrator 持有的 deterministic policy + 用户
可配置规则完成。本里程碑不新增新的 Agent。

M11.1 明确不做：隐藏式自主重学、不做逐步 LLM 浏览器控制、不做完整恢复
对话；失败先返回清晰状态，并交给后续 M12 能力处理。

## M12 —— Recovery & Abort Dialogue / 恢复与中断对话

M12 把失败和用户中断做成一等产品流程。它依赖 M11.0 conversation shell，
因为恢复和中断是运行时对话，不是孤立的执行状态。

纳入 / 明确的产品内部 Agent：

- **Agent F · Recovery Dialogue Agent / 恢复对话 Agent** —— 解释失败步骤，
  给出 continue / rerun / replan / takeover / abandon 选项，并产出下一
  个边界动作。
- **Agent G · Abort Dialogue Agent / 中断对话 Agent** —— 处理用户主动
  中断，给出 continue / rerun / replan / takeover / abandon 选项。

预期交付：

- L3 执行失败即暂停。
- 恢复对话只在规划边界处调用 Agent D。
- 用户主动中断和用户请求停止的 abort dialogue。
- 自动化无法安全继续时，交给 M13 的 User Demonstration 或 Guided
  Teaching。
- 审计记录区分 engine failure、user abort、recovery choice、user
  takeover。

如果 M13 尚未实现，M12 MVP 可以先停在 pause + explanation + user
choice，不承诺完整 recording 或教学模式写回。

## M13 —— User-Guided Learning, Teaching & Correction / 用户引导学习、教学与纠正

M13 真正实现 L2 用户引导学习。它包含两个子模式：User Demonstration 和
Guided Teaching。

纳入 / 明确的产品内部 Agent：

- **Agent H · Teaching Guide Agent / 教学引导 Agent** —— 沟通下一步教学
  动作，提出 highlight target，询问澄清问题，但不直接操作浏览器。

预期交付：

- 可视化 Playwright 浏览器，用于 takeover / teaching mode。
- User Demonstration recording：用户操作页面，系统记录真实 interaction、
  selector、value、click target 和可观测状态变化。
- Guided Teaching：WebAgentFlow 通过元素 highlight、shadow、
  indicator、tooltip 或下一步提示引导用户；真实 click / input /
  selection 仍由用户执行。
- 只有用户真实动作可以带 provenance 写回 LearnedPath actions
  （`provenance = user`）。
- Agent H 的建议只是 guidance，不能直接写成 LearnedPath action。
- 路径纠正 UI：编辑或替换既有 LearnedPath。
- 用户纠正和 correction evidence 驱动 trust 更新。

## M14 —— Learning Quality, Coverage & Negative Knowledge / 学习质量、覆盖与负面知识

M14 在 L3 快乐路径和接管闭环存在之后，回到 L1 学习质量。同时吸收原
M10 draft backlog：更丰富控件、模式泛化和负面知识。

纳入 / 明确的产品内部 Agent：

- **Agent A · Page Intent Agent / 页面意图 Agent** —— 把页面用途理解从
  Supervisor 评估里拆出来。
- **Agent B · Attempt Evaluator Agent / 尝试评估 Agent** —— 保持简单：
  输出观察 / 异常，耐久 verdict 仍由代码推导。
- **Agent C · Learning Reporter Agent / 学习报告 Agent** —— 给用户汇报：
  页面是什么、哪些路径可靠、哪些失败过、哪里需要用户补教、trust 如何
  变化。

迁移到这里的覆盖 backlog：

- 弹层控件：Cascader、DatePicker、RangePicker、MonthPicker、表头
  sort / filter。
- 自定义 click-toggle 控件：Tag-as-filter、pill filters、非原生
  checkbox / radio。
- Form-label extractor 扩展：Element Plus、Naive UI、Arco Design、
  TDesign、Quasar、MUI，按 fixture 或真实页面证据触发。
- Cross-page pattern mining：login / search / CRUD metadata，供 Agent D
  后续消费。

Negative knowledge / failure evidence 在这里正式化：

- 存储 failed attempts、replay drift、`target_missing`、
  `unsupported_action` 和 user correction evidence。
- 供 Agent D planning、Agent B evaluation、learning quality report 和
  M15 automated evaluation 消费。
- 更丰富的 postcondition pattern 和 artifact verification pattern 可以
  放在 M14 或 M15，取决于实现范围。

## M15 —— Automated Evaluation, Audit & Hygiene / 自动评估、审计与卫生

- 对 confirmed / provisional LearnedPath 做 fixture catalogue 和选定真实
  页面基线的回归 replay。
- 按 page template、scenario、trust state、control type、drift reason
  跟踪 failure evidence 趋势。
- 对 confirmed / provisional LearnedPath 做 drift alert。
- task result verification trend tracking。
- artifact existence 和 retention check。
- conversation、recovery、teaching session audit。
- data、log、screenshot、artifact、LLM prompt payload 的 retention /
  cleanup policy。
- 定时检查不得静默改写路径，只产出可审核证据。

## M16 —— External Interfaces / 对外接口

M16 在主 L1/L2/L3 闭环可用之后稳定开放能力。它不是 M11.0 runtime
conversation CLI。

预期交付：

- 页面学习、路径规划、执行、验证、artifact、用户引导记录的版本化 API
  contract。
- 面向外部调度、本地脚本和批处理的稳定 CLI 命令。
- 面向第三方 Agent 调度者的 Skill / Tool 形态。
- 第三方 scheduler interface。
- 有开发能力的用户可以通过 CLI / API 把 WebAgentFlow 接入自己的系统或
  自建操作台。

外部 Agent 可以调度 WebAgentFlow，但不得替代 WebAgentFlow 自己做逐步
浏览器自动化。

## M17 —— Multi-page Workflow Composition / 多页面工作流编排

M17 把 L3 从单路径执行扩展到 workflow composition。

预期交付：

- 把多个 LearnedPath 编排成更大的 workflow。
- 跨页面传递状态，例如 search -> detail -> export。
- 支持跨页面的 workflow-level recovery、takeover 和 teaching mode。
- Agent D 可以组合已经学会的路径，但不能从 raw HTML 凭空发明浏览器
  路径。

## M18 —— CLI Distribution & Integration Readiness / CLI 分发与集成就绪

M18 在 runtime loop 和 workflow composition 可用之后，稳定 CLI / API
分发和集成能力。

预期交付：

- 稳定 CLI 分发。
- Docker / local packaging。
- API / CLI examples。
- scripting 和 batch-usage recipes。
- 接入用户自建系统或操作台的 integration cookbook。
- 版本化 CLI / API contract 和兼容策略。

## M10 收口后的过渡非目标

规范列表见 [`scope-boundaries.zh.md`](./scope-boundaries.zh.md)。在 M11.0
迭代文档写出之前，刚完成的 M10.2 边界仍作为历史参考。要点：

- 不做运行时 conversation shell。
- 不做 Agent D、Agent H 或 L3 task runner。
- 不做 L3 task result verification。
- 不做 artifact lifecycle。
- 不做 multi-page workflow composition。
- 不做 action risk gate。
- 不托管目标网页 session 或权限；登录态失效、权限不足、认证页回退和
  操作失败都属于 runtime failure / recovery 问题。

---

本文为 [`roadmap.md`](./roadmap.md) 的中文镜像，内容以英文版为准。
