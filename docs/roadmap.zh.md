# 路线图

运营视角下"已交付 / 正在做 / 下一步"的全景。  
12 阶段架构时间线请见 [`architecture.zh.md`](./architecture.zh.md) §E。

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
- **登录页基线 spec**（`specs/login.{md,assertions.json}`），含 success + failure 两个场景
- **Autonomous Workbench**（`/exploration/autonomous`）—— 用户驱动的 UI，7 个区块：运行配置、实时 SSE 状态、页面分析、执行时间线、验证（self + supervisor + 评分卡）、来源标识、SSE 原始事件审计（带复制）
- **透明化**：Supervisor 推理轨迹在 UI 上可见；每个 SSE 事件都在审计面板里，带复制按钮；截图支持点击放大预览
- **UI 语言感知的 Supervisor**：UI 当前语言透传给 LLM prompt
- **文档拆分**：精简后的 `CLAUDE.md` + `docs/architecture.md` + `docs/parser-rules.md` + `docs/scope-boundaries.md`

Phase 9 尚未完成（见下方"后续计划"）：

- [ ] **用户亲自验证** Autonomous Workbench 在登录页的 D1（成功）/ D2（失败）两个场景 —— 用户驱动，不是 Claude Code 代跑
- [ ] **Run 落库** —— 每次 autonomous run 按 `spec_id + scenario + timestamp` 存库，用来追踪基线随时间的变化（Q3 设计债）
- [ ] **按 spec 预填表单** —— 选择 `spec_id + scenario` 后自动从 `scenarios[scenario].inputs` 预填 `fill_values`，替代当前登录特化的硬编码默认值（Q5 设计债）
- [ ] **场景命名去特化** —— 把登录页 scenario 名从 `success / failure` 改成 `valid_credentials / invalid_credentials`，避免和系统 verdict 枚举撞词（Q4 设计债）
- [ ] **第二个 fixture 页** —— 在 `apps/validation-site/` 里再做一个列表 / 查询页，配 `specs/<page>.assertions.json`，证明 workbench 能跑非登录形态的页面

## 下一阶段 —— Phase 10：路径抽象 & 经验累积

只有 Phase 9 收尾完成（至少一个非登录 fixture 被用户审核通过）才开始：

- **LearnedPath 落库** —— 审核通过的 exploration run 变成 LearnedPath 条目，按页面签名 + 场景归档，带溯源信息。
- **跨页模式挖掘** —— 发现不同页面共享相同动作形态（登录、搜索、CRUD）。
- **基于已存路径回放执行**，带针对当前页面分析的漂移检测。

## 再往后（Phase 11–12）

- Phase 11 —— 用户纠正 & 行为教学（用户修改一个 LearnedPath，系统学习用户改了什么、为什么）。
- Phase 12 —— 自动化评估 & 持续优化体系（对整个 fixture 目录做回归、漂移告警）。

## 当前阶段的非目标

规范列表见 [`scope-boundaries.zh.md`](./scope-boundaries.zh.md)。要点：不做 CLI、不做 skill 注册表、不做实时逐步 LLM 监督、不做跨设备同步。

---

本文为 [`roadmap.md`](./roadmap.md) 的中文镜像，内容以英文版为准。
