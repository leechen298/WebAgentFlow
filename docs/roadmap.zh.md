# 路线图

运营视角下"已交付 / 正在做 / 下一步"的全景。

- 产品**是什么**（三个阶段、七个 Agent、跨阶段不变量）见
  [`product-model.zh.md`](./product-model.zh.md) —— 权威产品参考。
- 12 阶段架构时间线请见 [`architecture.zh.md`](./architecture.zh.md) §E。

## 已交付（Phase 1–7 + 探索子系统脚手架）

- 页面事实基础（客户端抓 HTML → 服务端 `lxml` 解析为 Full AST）。
- 扩展端录制用户事件（click / input / change / navigate / richtext-input），带 AST 关联和 DOM mutation 跟踪。
- 从主事件 + 变更构建 Step。
- Agent 输入契约 + 页面 / 步骤 / 组合理解（6C / 6D / 6E）。
- Phase 7 完整执行层：Playwright runtime、6 级 locator resolver、action executor、post-action observer。
- 任务驱动探索：TaskDefinition JSON → `run_exploration` → success criteria → supervisor 评估 → Exploration Workbench UI（`/exploration`）。

## 当前阶段 —— Phase 9：自主探索 + 用户驱动验证

基础设施已就绪：

- **自主探索流水线**（端到端）
  - `page_analyzer.py` —— 实时页面元素发现（纯结构分类）
  - `action_planner.py` —— 规则驱动的多字段规划器，按语义角色匹配（username / password / email / search / text）
  - `autonomous_explorer.py` —— 编排器 + SSE 事件分发
  - `exploration_supervisor.py` —— 项目内 LLM Agent（MiniMax M2.7，保留 `<think>` 推理轨迹以便透明化）
  - `page_verification.py` —— 基线对照器，5 项独立评分
- **自建 validation-site**（`apps/validation-site/`）—— 首页目录 + 首个 fixture（登录）+ mock 后端 `/validation-api`
- **登录页基线 spec**（`specs/login.{md,assertions.json}`），含 `valid_credentials` + `invalid_credentials` 两个场景
- **Autonomous Workbench**（`/exploration/autonomous`）—— 用户驱动的 UI，7 个区块：运行配置、实时 SSE 状态、页面分析、执行时间线、验证（self + supervisor + 评分卡）、来源标识、SSE 原始事件审计（带复制）
- **透明化**：Supervisor 推理轨迹在 UI 上可见；每个 SSE 事件都在审计面板里，带复制按钮；截图支持点击放大预览
- **UI 语言感知的 Supervisor**：UI 当前语言透传给 LLM prompt
- **文档拆分**：精简后的 `CLAUDE.md` + `docs/architecture.md` + `docs/scope-boundaries.md`

Phase 9 已完成：

- [x] **Run 落库** —— 每次 autonomous run 都写入 `exploration_runs` 表，
  `strategy_json.kind = "autonomous"`，带 `spec_id / scenario / verdict`。
  历史列表与详情：`GET /exploration/autonomous-runs/list|get`。
- [x] **按 spec 预填表单** —— workbench 挂载时拉 `GET /exploration/specs`，
  选择 `spec_id` 后 scenario 下拉框从规范动态加载；切换 scenario 自动用
  `scenarios[scenario].inputs` 覆写 `fill_values`。
- [x] **场景命名去特化** —— 登录页 scenario 名从 `success / failure` 改成
  `valid_credentials / invalid_credentials`；schema `VisibleOn` 从
  2 值 `Literal` 放宽为自由 scenario key。
- [x] **登录页用户验证**（2026-04-18）—— 用户在 workbench 亲跑 D1
  （`valid_credentials`）和 D2（`invalid_credentials`），两次验证评分卡
  5 项**全绿**。Run `a7b9c035-…`（D1）和 `3d830c63-…`（D2）已落库，
  在 `/api/exploration/autonomous-runs/list` 可见。

Phase 9 尚未完成：

- [ ] **第二个 fixture 页 —— `users`（用户目录）**。形态于
  2026-04-18 敲定：
  - **UI 侧（做全）**：Vue 页面用一整套 Ant Design 的企业级搜索表单
    —— 文本框、select、radio group、date 输入、Cascader、DatePicker、
    RangePicker、MonthPicker、TimePicker、Tag 筛选 —— 加上带列 sort
    和列 filter 的 Ant Design Table。后端是 mock 的
    `/validation-api/users`，接收过滤参数返回对应数据。
  - **Spec 侧（做窄）**：`specs/users.{md,assertions.json}` 只写
    Phase 9 engine 应该能过的 scenario。已覆盖：`filter_by_name`、
    `no_match`（text 输入 + Search），以及 `filter_by_status`
    （原生 `<input type=radio>` 组 + Search —— 用一个内联非文本
    控件证明 planner 不止会驱动 text 输入）。
  - **弹层式控件**（Cascader、所有 Picker 变体、Tag 筛选、表格列的
    sort/filter）**本轮刻意不写 scenario**。它们留在页面上是为了让
    analyzer 扫过去顺带产出诊断信息，但它们正式的 scenario 是
    Phase 10 的交付物。
  - 这是 Phase 9 进入 Phase 10 前的**最后一道门**。

## 下一阶段 —— Phase 10：路径抽象 & 经验累积

只有 Phase 9 收尾完成（至少一个非登录 fixture 被用户审核通过）才开始：

- **LearnedPath 落库** —— 审核通过的 exploration run 变成 LearnedPath 条目，按页面签名 + 场景归档，带溯源信息。
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
