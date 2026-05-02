# 路线图

运营视角下"已交付 / 正在做 / 下一步"的全景。

- 产品**是什么**（三个阶段、七个 Agent、跨阶段不变量）见
  [`product-model.zh.md`](./product-model.zh.md) —— 权威产品参考。
- 12 阶段架构时间线请见 [`architecture.zh.md`](./architecture.zh.md) §E。

## 已交付（基础设施 + 自主探索子系统）

2026-04-20 清理之后，仓库里唯一的产品表面就是**基于 Playwright 的
自主探索管线**。早期迭代（录制、Chrome 扩展、任务驱动探索、技能 /
执行记录 / 学习调试 UI）已经从代码中移除 —— 见
`memory/project_legacy_stack_removed.md`。12 阶段的历史时间线
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

## Phase 9 —— 已于 2026-04-21 关闭

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
  它们的正式 scenario 是 Phase 10 的交付物。
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

Phase 9 没有剩余待办。Phase 10 现已开启。

## 下一阶段 —— Phase 10：路径抽象 & 经验累积

Phase 9 关门之后，重心从"引擎能不能驱动一个页面"转到"能不能复用
学过的东西，并覆盖更多控件形态"：

- **LearnedPath 落库** —— 审核通过的 exploration run 变成
  LearnedPath 条目，按页面签名 + 场景归档，带溯源信息。
- **跨页模式挖掘** —— 发现不同页面共享相同动作形态（登录、搜索、CRUD）。
- **基于已存路径回放执行**，带针对当前页面分析的漂移检测。
- **弹层式控件支持** —— 扩展 `page_analyzer` + `action_planner`，
  让它们能处理"必须先点一下才暴露交互面"的组件（Cascader、
  DatePicker、RangePicker、MonthPicker、表格表头的列 sort /
  filter）。engine 需要先点触发器，再去操作弹出的面板。
  原生内联非文本控件（radio / checkbox 组）属于 Phase 9 范围 ——
  Phase 10 只在此基础上追加弹层形态。
- **自定义 click-toggle 控件** —— Tag 筛选等基于 `<span>` /
  `<div>` 的伪按钮 pill，非原生 form input。和弹层分开单列是
  因为触发器本身就是交互面，没有弹出面板可操作；和弹层归同一
  phase 则是因为两者都遵循"点击改变一个 query 参数"的约定。
- **Form-label extractor · 覆盖范围扩充** —— analyzer 当前的
  `form_label_extractor` 只带了 Ant Design（匹配 `.ant-form-item`
  → `.ant-form-item-label`）和原生 HTML5 `<label for>` 两个
  handler。Phase 10 结束前，把其他遵循同一 Form.Item 约定、仅 class
  前缀不同的主流 Vue / React 表单库补上。候选清单：
  - Element Plus（`el-form-item`）
  - Naive UI（`n-form-item`）
  - Arco Design（`arco-form-item`）
  - TDesign（`t-form-item`）
  - Quasar（`q-field__label`）—— 形态稍微不同，可能需要独立 handler
  - Material UI / MUI v5（`MuiFormControl-root` 包
    `MuiInputLabel-root`）—— 范式不同，单独 handler
  每个新 handler 大约 15 行 Python，`extract_label` 的分派器已经支持
  第一个命中即返回。按 fixture 需要或真实页面报告触发时再补。代码落地后，回到
  `apps/validation-site/specs/users.assertions.json` 补齐 Tier 2
  scenario，让每个控件都有对应的场景验证。由于 fixture 页面本身
  上一阶段就搭好了，评分卡从红变绿就是改进的量化证据。

## 再往后（Phase 11–12）

- Phase 11 —— 用户纠正 & 行为教学（用户修改一个 LearnedPath，系统学习用户改了什么、为什么）。
- Phase 12 —— 自动化评估 & 持续优化体系（对整个 fixture 目录做回归、漂移告警）。

## 当前阶段的非目标

规范列表见 [`scope-boundaries.zh.md`](./scope-boundaries.zh.md)。要点：
Phase 3 不做实时逐步 LLM 监督、不做跨设备同步。CLI / Skill /
对外 Agent 接口**也不在本阶段**，但是一个长期交付方向 —— 见
[`product-model.zh.md`](./product-model.zh.md) §10。

---

本文为 [`roadmap.md`](./roadmap.md) 的中文镜像，内容以英文版为准。
