# 路线图

运营视角下"已交付 / 正在做 / 下一步"的全景。

- 产品**是什么**（L1/L2/L3 生命周期阶段、七个产品内部 Agent、跨阶段不变量）见
  [`product-model.zh.md`](./product-model.zh.md) —— 权威产品参考。
- 历史迭代目录仍可能叫 `phase-N`，但新路线图正文使用
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

## 历史交付 Phase 9 —— 已于 2026-04-21 关闭

主题：自主探索 + 用户驱动验证。关门验证：2026-04-21 通过
`verify-scenario` skill 把 5 个 scenario 各跑了一次，全部
`pass_gate = pass`，supervisor.source 均为 `llm`，5 项评分卡全
`1.0`（element_recognition / action_coverage / verdict_accuracy /
distraction_avoidance / supervisor_agreement）。run_id 都在
`exploration_runs` 表里。

Phase 9 期间值得记的里程碑：

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
  `exploration_runs` 是唯一留下的表。

Phase 9 没有剩余待办。当前活跃交付里程碑是 M10。

## M10 —— Path Asset Foundation / 路径资产基础（进行中）

M10 的目标是让 LearnedPath 成为可复用资产。它**不**实现 L3 实际工作：
没有用户任务对话入口，没有 Agent D Path Planner，也没有 task-to-path
执行闭环。它搭建的是 M11 会调用的确定性执行底座。

- **LearnedPath 落库 —— 已于 2026-04-25 交付（10.1）**。
  `pass_gate = pass` 的运行自动写入 `learned_paths`，按
  `(page_template, query_signature, dom_fingerprint, scenario)` 归档，
  并带 `provisional` / `confirmed` / `flaky` / `deprecated` 四态 trust。
- **Replay execution + drift detection —— 当前任务（10.2）**。
  用户从 LearnedPath catalog 指定一条路径，输入 URL，让引擎按已存
  actions 重跑。结果返回 replay status 和页面变化原因，例如 page
  mismatch、signature changed、target missing、unsupported action。
  这不是 `pass_gate`，不是 Supervisor verdict，也不是任务规划。

M10 关闭标准：LearnedPath 能被持久化、查看、确认 / 废弃，并能确定性
replay；页面变化能以可解释状态返回。

## M11 —— Task-to-Path Planning & Execution MVP

M11 是第一版 L3 实际工作里程碑。用户用自然语言描述任务，WebAgentFlow
从已学路径中选择并绑定参数，执行，然后汇报结果。

纳入 / 明确的产品内部 Agent：

- **Agent D · Path Planner Agent / 路径规划 Agent** —— 读取用户任务和
  学习数据，选择 / 组合路线，把任务参数绑定到可替换 action value，
  并且绝不读取 raw HTML。
- **Agent E · Result Reporter Agent / 结果报告 Agent** —— 读取执行结果，
  输出用户可读报告和 UI 可渲染结构化字段。

预期交付：

- 面向一个目标页面或已知页面集合的任务输入 / chat 入口。
- LearnedPath 检索和排序。
- Slot binding：把姓名、日期、状态、导出格式、搜索词等任务参数填入
  学过的动作值。
- planner 路线或绑定参数不确定时，执行前让用户确认。
- 通过 M10 replay engine 执行，不走 autonomous exploration。
- 用户视角结果报告，必要时关联 artifact / 最终状态。

M11 明确不做：隐藏式自主重学、不做逐步 LLM 浏览器控制、不做完整恢复
对话；失败先返回清晰状态。

## M12 —— Recovery & Handoff / 恢复与接管

M12 把失败和用户中断做成一等产品流程。

纳入 / 明确的产品内部 Agent：

- **Agent F · Recovery Dialogue Agent / 恢复对话 Agent** —— 解释失败步骤，
  给出重新规划 / 从头重跑 / 交给用户的选项，并产出下一步动作。
- **Agent G · Abort Dialogue Agent / 中断对话 Agent** —— 处理用户主动
  中断，给出继续 / 重跑 / 接管 / 放弃等选项。

预期交付：

- L3 执行失败即暂停。
- 重新规划和重跑只在边界处调用 Agent D。
- 自动化无法安全继续时，交给用户进入可视化浏览器引导模式。
- 审计记录区分 engine failure、user abort、user takeover。

## M13 —— User-Guided Learning & Correction / 用户引导学习与纠正

M13 真正实现 L2 用户引导学习，不复活旧 Chrome extension 录制路线，而
是基于可视化 Playwright 浏览器。

预期交付：

- 可视化浏览器接管模式。
- 记录用户真实交互：selector、value、click target、可观测状态变化。
- 带 provenance 写回 LearnedPath actions（`provenance = user`）。
- 路径纠正 UI：编辑或替换既有 LearnedPath。
- 用户纠正驱动 trust 更新。

默认不新增产品 Agent；除非确实无法放入 A-G 角色。

## M14 —— Learning Quality Agents & Coverage Expansion / 学习质量与覆盖扩展

M14 在 L3 快乐路径和接管闭环存在之后，回到 L1 学习质量。同时吸收原
M10 draft backlog：更丰富控件和跨页模式。

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

## M15 —— Automated Evaluation & Continuous Optimization / 自动评估与持续优化

- 对完整 fixture catalogue 做回归 replay。
- 对 confirmed / provisional LearnedPath 做漂移告警。
- 按 page template、scenario、trust state、control type 跟踪质量趋势。
- 定时检查不得静默改写路径，只产出可审核证据。

## M16 —— External Interfaces / Open Tooling / 对外接口

主 L1/L2/L3 闭环可用之后，再稳定开放能力：

- 页面学习、路径规划、执行、验证、用户引导记录的 API contract。
- 面向本地调试和批处理的 CLI 命令。
- 面向第三方 Agent 调度者的 Skill / Tool 形态。

外部 Agent 可以调度 WebAgentFlow，但不得替代 WebAgentFlow 自己做逐步
浏览器自动化。

## 当前交付里程碑的非目标

规范列表见 [`scope-boundaries.zh.md`](./scope-boundaries.zh.md)。要点：
L3 不做实时逐步 LLM 监督；M16 前不做对外 Agent 接口，除非显式重新
排优先级。

---

本文为 [`roadmap.md`](./roadmap.md) 的中文镜像，内容以英文版为准。
