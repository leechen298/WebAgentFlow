# 架构

## 目标

WebAgentFlow 提供一个结构化平台：学习网页、复用已验证 LearnedPath、
基于学习数据规划任务执行，并对照人工编写的基线验证结果 —— 由 Vue
控制台、FastAPI 后端、Python worker 脚手架和 Playwright runtime 协作。

## 系统分层

1. **表示层** —— Vue 控制台提供面向操作者的界面。
2. **应用层** —— FastAPI 服务承载 API 契约、编排入口、集成边界。
3. **执行层** —— Playwright runtime + 异步 worker，负责浏览器自动化。
4. **基础设施层** —— PostgreSQL、Redis、MinIO 分别提供持久化、缓存、对象存储。

## 各 app 职责

- `apps/console` —— 操作者 UI：autonomous workbench、运行历史、引导首页。
- `apps/api` —— HTTP API、LLM provider 层、autonomous exploration、page verification、validation-api mock 后端。
- `apps/worker` —— 异步执行骨架（当前是脚手架）。
- `apps/validation-site` —— 自主探索的自建测试 fixture（login、users 等）。
- `apps/cli` —— Python CLI（`wagent`）与 `verify-scenario` Claude Code skill。

---

## 当前进展

下面的旧 12 阶段列表记录的是技术路线历史。当前规划术语以
[`product-model.zh.md`](./product-model.zh.md) 和
[`roadmap.zh.md`](./roadmap.zh.md) 为准：产品生命周期阶段是 L1 / L2 /
L3，交付里程碑是 M10 / M11 / ...

当前交付里程碑：**M10 Path Asset Foundation / 路径资产基础**。当前
可执行包：`10.2-replay-execution-drift-detection`。

**已完成阶段：**

1. **页面事实基础** —— 原始 HTML 抓取、HTML → Full AST（服务端 lxml）、Full AST schema。
2. **用户事件录制** —— click / input / change / navigate / richtext-input，带完整上下文。
3. **Event–AST 关联** —— 事件映射到 AST 节点（exact / ancestor / none + fallback）。
4. **DOM mutation 录制** —— MutationObserver 监听顶层 + 同源 iframe、批处理、噪音过滤、AST 关联。
5. **Operation Step 构建** —— 把主事件与后续 DOM mutation 关联为一个 Step。
6. **Agent 对页面与步骤的初步理解** —— LLM provider 层、agent 输入契约、页面理解（6C）、步骤理解（6D）、组合输出（6E）、服务端 event AST 匹配。
7. **完整执行能力（Playwright）** —— 单步执行链：
   - 7A：ExecutionRequest / ExecutionResult 契约、6 级 locator priority、`build_execution_request`。
   - 7B：Playwright browser / context / page 生命周期、`create_execution_runtime`。
   - 7C：6 级优先 locator resolver、SelectorDescriptor、region-scoped 消歧。
   - 7D：`execute_action()`，支持 click / fill / select / check / uncheck / hover / press / navigate / scroll。
   - 7E：`observe_post_action()` / `execute_and_observe()`、变化检测、目标元素后置状态。

**探索子系统**（建在 Phase 7 之上）：

- **Success evaluator** —— 规则式，评估 6 类条件（url_changed / url_contains / title_contains / element_present / html_changed / no_error），三态语义（success / failure / uncertain）。
- **Task definitions** —— `data/tasks/` 下的外部 JSON 文件，描述站点特定任务，带溯源信息。
- **Exploration loop** —— 通用引擎，零站点特化代码。
- **Exploration supervisor** —— 事后 LLM 评估（verdict / summary / anomalies / suggestions），失败时走规则 fallback。
- **Exploration Workbench** —— 前端页面 4 个区：task 配置、执行时间线、页面状态 + supervisor、用户 verdict。

**自主探索子系统**（新，用户通过 workbench 驱动）：

- **Page analyzer**（`services/learning/page_analyzer.py`）—— 实时页面元素发现，纯结构分类（禁止关键词 / 站点启发式）。从 HTML type + 通用 name/placeholder 词素推断 fillable 的 `semantic_role`（username / password / email / search / text）。
- **Action planner**（`services/learning/action_planner.py`）—— 规则式多字段规划器。`fill_values` 字典按语义角色匹配最合适的 fillable；没有结构化 submit 时用 fallback 按钮从附近 clickable 里挑。
- **Autonomous explorer**（`services/learning/autonomous_explorer.py`）—— 编排器，通过 SSE 发出阶段事件。结果 verdict 是 `success | incomplete | no_progress | uncertain`。
- **Page verification comparator**（`services/learning/page_verification.py`）—— 对照人工基线（`apps/validation-site/specs/<page>.assertions.json`），产出 5 项独立评分（element_recognition / action_coverage / verdict_accuracy / distraction_avoidance / supervisor_agreement）。**不做总分**。
- **Autonomous Workbench**（`pages/AutonomousWorkbenchPage.vue`）—— 用户驱动 UI，SSE 实时进度；**7 个区块**：运行配置、实时阶段状态、页面分析、执行时间线（每步截图支持 `<a-image>` 点击放大）、验证（self verdict + supervisor + 5 项评分）、SSE 原始事件审计（每条事件都记录，带复制按钮 + 全屏 modal）、来源标识。
- **Supervisor 透明化** —— Supervisor Agent 的 `<think>...</think>` 推理轨迹保留在 `LlmResponse.thinking`，在 supervisor 卡片以折叠面板"思考过程"展示。旁边标注模型 ID（`_model`）。`llm_provider.py` 里的 `generate_structured` 通过 `_split_thinking()` 拆出 thinking 而不是静默丢弃。
- **UI 语言感知的 Supervisor** —— UI locale（BCP-47，如 `zh` / `en` / `ja`）通过流式端点透传到 Supervisor prompt，以"用 {language} 写所有自然语言字段"覆盖默认的"跟随页面标题语言"规则。映射表在 `autonomous_explorer._LANGUAGE_NAMES`。
- **Validation site**（`apps/validation-site`）—— 自建 Vue fixture（目前有 login + dashboard，将来更多），autonomous exploration 不依赖公网站点（避免 CAPTCHA / 限流噪声）。`/` 路由是 `IndexPage.vue`，目录化展示可用 fixture。

---

## B. 技术路线变更 —— 客户端 vs 服务端 AST

**旧路线**：客户端 DOM walker（`initial-state.ts`）直接从浏览器里的 live DOM 产出语义化 StateNode 树。

**现路线**：职责拆分。

- **客户端（扩展）** 抓原始 HTML（页面 + iframe 文档），发给服务端。
- **服务端（API）** 用 `lxml.html` 解析 HTML → Full AST，映射到项目自定义的 Full AST schema。

映射层刻意做薄：tag 归一、属性过滤、文本节点交错、可见性检测。**parser 原始的树结构原样保留** —— 不重组、不语义解读、不结构重写。

为什么这么做：

- 服务端解析更稳、更可调、更可测。
- 日志、错误处理、回归测试都好做。
- 与浏览器 DOM API 解耦 —— 以后 parser 升级后，可以重跑存储的 HTML，不用再次访问页面。
- 第三方 parser（`lxml` 等）能稳健处理真实世界里的畸形 HTML。

关键文件：

- 服务端 parser：`apps/api/app/services/html_ast_parser.py`（基于 `lxml.html`）
- Full AST schema：`apps/api/app/schemas/ast.py`
- 执行子包：`apps/api/app/services/execution/`
- Learning 子包：`apps/api/app/services/learning/`
- Page verification schema：`apps/api/app/schemas/page_verification.py`
- Page analysis schema：`apps/api/app/schemas/page_analysis.py`
- Exploration router：`apps/api/app/routers/exploration.py`
- Validation API router：`apps/api/app/routers/validation_api.py`
- Validation specs：`apps/validation-site/specs/*.{md,assertions.json}`

### AST 双轨：客户端 vs 服务端职责

项目目前同时维护两套 AST 相关系统，各司其职，**不冲突**，但边界必须守住。

**服务端 FullAST**（`html_ast_parser.py` → `ast_simplifier.py`）：

- 页面事实的权威表示。
- `page_analyzer.py` 在 autonomous 探索时消费 Full AST 来发现交互元素。
- `page_verification.py` 用同一份 AST 表示把实际页面和 spec 基线做对照。

> 客户端录制相关的通路（`apps/extension`）已经下线；autonomous 探索直接驱动可见的 Playwright 浏览器。

---

## C. Full AST vs Simplified AST

**Full AST**（当前焦点）：

- 页面事实层 —— 主要的状态表示。
- 保留第三方 parser 的原始树结构。
- 保留兄弟顺序、父子关系、文本节点顺序。
- 保留关键属性、iframe 内容（作为子树 —— 见下文）。
- **不**重构、不重组、不为树添加语义抽象。
- **不**做早期语义压缩或信息丢失。
- 由客户端抓取的 HTML 在服务端生成。

**Simplified AST**（未来，**不是**当前交付里程碑）：

- Full AST 的**结构保留投影** —— 不是改写。
- 保持与 Full AST 相同的树形。
- **不**重排兄弟、不发明"标题 + 内容"容器、不重排节点。
- 主要做**属性剪枝**，**不做**结构变换。
- 作为 LLM 友好的视图，由 Full AST 确定性推导而来。

> Simplified AST 是 Full AST 的结构保留投影。

---

## D. iframe 表示

第三方 HTML parser 会解析源 HTML 里的 `<iframe>` 标签，但 iframe 内部的文档是单独的一份文档，必须由客户端单独抓取并传给服务端。

在 Full AST 里，**iframe 内部内容作为 `<iframe>` 节点的子树挂载**，而不是侧通道字段：

- `<iframe>` 是树里的常规元素节点。
- 内部 frame 文档解析后作为子树挂上去。
- 用一个合成的 `<frame-body>` 包裹节点作为 iframe 子树的根。
- 没有 `frame_content` 这类侧通道字段 —— 全局统一用树结构。

> iframe 是一个节点，frame 文档作为它的子树挂上去，不是侧通道字段。

这样做的好处：

- 树遍历器处理 iframe 内容和处理其他子树一样。
- 下游消费者无需对 iframe 做特殊处理。
- 多层 iframe 嵌套通过递归自然支持。

---

## E. 历史开发时间线（旧 12 步视图）

这份列表保留作架构历史，不是当前路线图术语。向前规划请使用
`roadmap.zh.md` 的 M10 / M11 / ...。

1. ~~Page fact foundation~~ ✅
2. ~~User event recording~~ ✅
3. ~~Event–AST association~~ ✅
4. ~~DOM mutation recording~~ ✅
5. ~~Operation Step building~~ ✅
6. ~~Agent initial understanding of pages and steps~~ ✅
7. ~~Full execution capability (Playwright)~~ ✅
8. Wait-for-expected-change 机制 + 自动化测试（部分已被 `pass_gate`、
   scorecard、page verification 吸收）
9. ~~Exploration loop + success evaluation + autonomous workbench~~ ✅
10. Path abstraction & 经验累积（当前交付里程碑 M10）
11. User correction & 行为教学（已重塑为 M13）
12. 自动化评估 & 持续优化体系（已重塑为 M15）

**关键并行关系：**

- **Phase 7 执行**已完成 —— 为 exploration 提供原子动作层。
- **Exploration 子系统**建在 Phase 7 之上 —— TaskDefinition → `run_exploration` → success evaluation → supervisor 评估。
- **自主探索子系统**仍是学习基础 —— URL → `autonomous_explorer.run_autonomous_exploration` → page verification 评分卡 → 用户在 workbench 审核。
- **Path abstraction（M10）**在 exploration 验证通过之后起步。

---

## F. 工具 / 数据分离

应用是纯引擎。**站点特定知识绝不硬编码在 Python 代码里。**

- **Verification specs** 在 `apps/validation-site/specs/*.{md,assertions.json}`
  —— 描述页面的人工基线，包含正向路径与负向路径两类场景。
- **自主引擎**（`autonomous_explorer.py`）通用 —— 拿到 URL（可选配
  spec + scenario）后在运行时发现结构。
- **切换目标站点**等于新增一份 spec，不改 Python 代码。

---

## G. Services 子包结构

`apps/api/app/services/` 下只有少数几组能力，全部服务于 autonomous
exploration。

**`services/execution/`** —— Playwright runtime：

- `execution_runtime.py` —— chromium/context/page 生命周期封装。
- 公共 API 通过 `__init__.py` 导出。

**`services/learning/`** —— 自主探索 + 页面校验：

- `autonomous_explorer.py` —— 编排、SSE 事件、Supervisor LLM 调用。
- `page_analyzer.py` —— 实时页面元素发现。
- `action_planner.py` —— 规则驱动的多字段规划器。
- `supervisor_observations.py` —— LLM 观察原子 schema + 代码侧裁决推导。
- `page_verification.py` —— spec 基线对照器，输出 5 项评分。
- `page_signature.py` —— 纯函数（`path_template` / `query_signature`
  / `dom_fingerprint`），计算 LearnedPath 身份四元组。由 exploration
  路由的 `pass_gate = pass` 写回 hook 调用。

**`services/analysis/`** —— 分析辅助（如 `form_label_extractor.py`）。

**顶层平铺 services**：`html_ast_parser.py`、`ast_simplifier.py`、
`llm_provider.py`。

---

## 基础设施

Docker Compose（`infra/docker/docker-compose.yml`）提供：

- **PostgreSQL 16** —— 主数据库。
- **Redis 7.4** —— 缓存 / 队列。
- **MinIO** —— 对象存储（端口 9000 API / 9001 控制台）。

仓库根部复制 `.env.example` 为 `.env`。console 有自己的 `apps/console/.env.example`。

## Worker

`apps/worker/app/` 运行轮询的 `JobRunner` loop。当前是脚手架 —— 心跳日志已有，job 执行逻辑未实现。

---

## 另见

- [`product-model.zh.md`](./product-model.zh.md) —— **产品形态权威文档**。
  本文讲"代码怎么组织"，产品形态讲"代码要实现什么"。在决定**做什么**
  之前先看产品形态。
- [`scope-boundaries.zh.md`](./scope-boundaries.zh.md) —— 当前交付里程碑**刻意不做**的事。
- [`roadmap.zh.md`](./roadmap.zh.md) —— v0.1 发布切出的运营里程碑。
- [`../CLAUDE.zh.md`](../CLAUDE.zh.md) —— 给 AI 编码 Agent 的会话级指引。

---

本文为 [`architecture.md`](./architecture.md) 的中文镜像，内容以英文版为准。
