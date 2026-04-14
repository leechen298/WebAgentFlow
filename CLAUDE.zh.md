# CLAUDE.zh.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指导。

> **多 Agent 同步规则**：本文件与 `CLAUDE.md`（英文版）和 `AGENTS.md`（供 Codex 及其他 AI Agent 使用）保持同步。任何一个文件修改时，其他文件必须同步更新。

## 项目概述

WebAgentFlow 是一个面向 Agent 驱动的 Web 工作流引擎的 monorepo，包含：
- Vue 3 前端控制台（`apps/console`）
- FastAPI 后端 API（`apps/api`）
- Python Worker 服务（`apps/worker`）
- Chrome MV3 浏览器扩展录制器（`apps/extension`，基于 WXT 构建）
- 共享 TypeScript 包（`packages/`）

## 当前项目方向

### A. 当前阶段与进展

项目按 12 阶段开发时间线推进。阶段 1–6 已完成，阶段 7 进行中（7A 已完成）。

**已完成的阶段：**
1. **页面事实基础** — 原始 HTML 抓取、HTML → Full AST（服务端，lxml）、Full AST schema
2. **用户事件录制** — click、input、change、navigate、richtext-input 等关键事件及完整上下文
3. **事件与 AST 关联** — 事件映射到 AST 节点（精确/祖先/无 + 降级信息）
4. **DOM 变更录制** — 顶层文档及同源 iframe 的 MutationObserver，批量处理，降噪，AST 关联
5. **操作步骤（Step）构建** — 将主事件与后续 DOM 变更关联为一个 Step
6. **Agent 初步理解页面与步骤** — LLM Provider 层、Agent 输入契约、页面理解（6C）、步骤理解（6D）、综合输出（6E）、服务端事件 AST 匹配
7A. **执行契约** — ExecutionRequest/ExecutionResult schema、定位优先级（6 级）、数据消费边界、`build_execution_request` 统一入口
7B. **执行运行时** — Playwright browser/context/page 生命周期、导航、页面观测（URL/title/HTML/截图）、统一错误处理、`create_execution_runtime` 工厂

**当前阶段（7）：接入完整执行能力（Playwright）** — 真实浏览器自动化（7A 契约 + 7B 运行时已完成 → 下一步 7C 定位器）

### B. 技术路线变更

技术方案已从之前的方向转变。

**之前的方案**：客户端 DOM walker（`initial-state.ts`）直接从浏览器的 live DOM 生成语义化的 StateNode 树，在浏览器端单次遍历中完成 HTML 解析、组件分类和语义提取。

**当前方案**：将职责拆分到客户端和服务端：
- **客户端（扩展）**——抓取页面和 iframe 内容文档的原始 HTML，发送到服务端
- **服务端（API）**——使用成熟的第三方 HTML 解析库将 HTML 解析为 Full AST，然后将解析输出映射到项目自有的 Full AST schema

解析管道为：**第三方库进行 HTML 解析 + 项目自有的 Full AST schema 和薄映射逻辑**。

映射层刻意保持轻薄：标签规范化、属性过滤、文本节点交错和可见性检测。**解析器的原始树结构原样保留**——不做重组、不做语义解读、不做结构重写。Full AST 应尽量贴近第三方解析器的输出。

这一转变的原因：
- 服务端解析更稳定、更易调试和测试
- 日志、错误处理和回归测试都很方便
- 与浏览器 DOM API 解耦——可以用改进的解析器重新处理已存储的 HTML，无需重新访问页面
- 第三方 HTML 解析器（如 `lxml` 等）能稳健处理真实世界的畸形 HTML
- 现有的客户端解析器（`initial-state.ts`）仍可用，但主要 AST 管道正在迁移到服务端

服务端解析器：`apps/api/app/services/html_ast_parser.py`（使用 `lxml.html`）
Full AST schema：`apps/api/app/schemas/ast.py`
服务端事件匹配器：`apps/api/app/services/server_ast_matcher.py`
执行契约 schema：`apps/api/app/schemas/execution.py`
执行契约构建器：`apps/api/app/services/execution_contract.py`
执行运行时：`apps/api/app/services/execution_runtime.py`

#### 双轨 AST：客户端与服务端职责

项目当前维护两套 AST 相关系统。它们服务于不同目的，**不互相冲突**，但必须遵守各自边界：

**客户端 AstIndex**（`apps/extension/src/recorder/ast-index.ts`）：
- 录制期实时匹配工具
- 在浏览器中运行，即时将事件/mutation 关联到 stateTree 节点
- 为每个事件生成 `astMatch`（confidence、nodeId、nodeLabel、areaLabel）
- **不是**页面结构或执行层定位的权威来源

**服务端 FullAST**（`html_ast_parser.py` → `ast_simplifier.py` → `server_ast_matcher.py`）：
- 页面事实层的权威表示
- 页面理解（6C）、步骤理解（6D）、组合理解（6E）均基于服务端 AST
- `server_ast_matcher.py` 提供 `server_ast_match`——事件在权威 AST 上的定位
- Phase 7 执行层应消费服务端 AST 和 `server_ast_match`，而非客户端 stateTree

**关系与消费优先级：**
- 客户端 `astMatch` 作为录制期辅助信息保留
- `server_ast_match` 是事件的服务端权威定位
- 下游消费者（step_builder、agent_input）优先使用 `server_ast_match`，无可用时 fallback 到客户端 `astMatch`
- Mutation 的服务端重定位**尚未实现**——mutation 当前仍仅使用客户端 `astMatch`

> 目标不是"立刻将所有 AST 统一到服务端"。客户端 AstIndex 保留用于实时录制。服务端 AST 是理解层和执行层的权威来源。

### C. Full AST 与 Simplified AST

**Full AST**（当前重点）：
- 页面事实层——主要状态表示
- 保留第三方解析器的原始树结构
- 保留兄弟顺序、父子关系、文本节点顺序
- 保留关键属性、iframe 内容（作为子树——见 D 节）
- 不对树进行重组、重新分组或添加语义抽象
- 不做提前的语义压缩或信息丢失
- 在服务端从抓取的 HTML 生成

**Simplified AST**（未来，非本阶段）：
- Full AST 的**保结构投影**——不是重写
- 保持与 Full AST 相同的树形状
- 不重组兄弟节点、不发明"标题 + 内容"容器、不重排节点
- 主要进行**属性裁剪**，而非结构变换
- 作为从 Full AST 确定性派生的 LLM 友好视图

> Simplified AST 是 Full AST 的保结构投影。

### D. Iframe 表示

第三方 HTML 解析器从源 HTML 中解析 `<iframe>` 标签。但 iframe 的内部文档内容是一个独立的文档，客户端必须单独抓取并传给服务端。

在 Full AST 中，**iframe 内部内容作为 `<iframe>` 节点的子树挂载**，而非作为旁路字段：

- `<iframe>` 是树中的普通元素节点
- 框架文档内容被解析后作为子树挂载
- 一个合成的 `<frame-body>` 包装节点作为 iframe children 中的文档根
- 没有特殊的 `frame_content` 或类似旁路字段——全程使用统一的树结构

> iframe 是一个节点，框架文档作为其子树挂载，而非旁路字段。

这种方式意味着：
- 树遍历器处理 iframe 内容的方式与处理其他子树相同
- 下游消费者不需要对 iframe 做特殊处理
- 多级 iframe 嵌套通过递归自然处理

### E. 开发时间线（12 阶段）

1. ~~页面事实基础~~ ✅
2. ~~用户事件录制~~ ✅
3. ~~事件与 AST 关联~~ ✅
4. ~~DOM 变更录制~~ ✅
5. ~~操作步骤（Step）构建~~ ✅
6. ~~Agent 初步理解页面与步骤~~ ✅
7. **接入完整执行能力（Playwright）** ← 当前 — 真实浏览器自动化，覆盖完整操作能力
8. 等待预期变化机制 + 自动化测试（并行线，与阶段 7 同步启动）
9. 执行闭环稳定化 — 动作 → 等待 → 判断 → 下一步
10. 路径抽象与经验沉淀（阶段 7 之后启动，持续增长）
11. 用户修正与行为示教
12. 自动化评测与持续优化体系

**关键并行关系：**
- **Agent 理解（阶段 6）** 已完成 — 为执行层提供页面/步骤/综合理解
- **自动化测试（阶段 8B）** 必须在具备执行能力时同步介入，而非后补 — 执行能力和测试能力一起长
- **路径抽象（阶段 10）** 不是最终总结模块 — 从执行开始后就逐步展开，跟系统一起长

### F. 明确不在范围内（当前阶段）

以下内容**不属于**当前实现阶段：
- 回放执行策略
- 用户行为 ↔ 页面变化因果建模
- 历史路径模板缓存
- 用户修正与行为示教
- 为可读性重组 DOM 的"页面摘要器"方案

## 常用命令

### 环境搭建与开发
```bash
# 安装依赖
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'

# 启动基础设施（PostgreSQL、Redis、MinIO）
docker compose -f infra/docker/docker-compose.yml up -d

# 执行数据库迁移
pnpm run db:migrate:api

# 运行所有组件
pnpm run dev             # 本地开发
pnpm run dev:lan         # 局域网可访问（绑定 0.0.0.0）

# 运行单个组件
pnpm run dev:console     # Vite 开发服务器（端口 5174）
pnpm run dev:api         # Uvicorn 开发服务器（端口 8001）
pnpm run dev:worker
```

### 构建、检查、测试
```bash
# 构建
pnpm run build              # 构建全部
pnpm run build:packages     # 构建共享包（console 之前需要先构建）
pnpm run build:console
pnpm run build:extension

# 代码检查与格式化
pnpm run lint               # ESLint + Ruff
pnpm run format             # Prettier + Ruff

# 前端测试（Vitest）
pnpm run test               # 运行所有 console 测试
pnpm run test:dev           # 监听模式
pnpm run test:coverage
pnpm run test:single        # 通过环境变量指定单个文件

# API 测试（Pytest）
cd apps/api && .venv/bin/pytest                             # 所有测试
cd apps/api && .venv/bin/pytest tests/test_health.py -v    # 单个文件
cd apps/api && .venv/bin/pytest -k "test_create" -v        # 模式匹配
```

## Git 安全规则

- 任何分支名以 `-local` 结尾的开发分支仅限本地，绝不能推送到任何远程仓库。
- 执行 `git push` 之前，必须先检查当前分支名。如果分支以 `-local` 结尾，停止操作，不要推送。
- 如果 `-local` 分支上的工作需要发布，先创建或移动一个非 `-local` 分支到同一提交，然后推送那个分支。

## API 架构

FastAPI 后端（`apps/api/app/`）采用严格的分层架构：
- **Routers**（`routers/`）：仅 HTTP 端点，基于动作的路由
- **Services**（`services/`）：业务逻辑
- **Repositories**（`repos/`）：SQLAlchemy 数据访问
- **Models**（`models/`）：ORM 模型，使用 JSON 列存储灵活的载荷
- **Schemas**（`schemas/`）：Pydantic 请求/响应模型
- **Core**（`core/`）：配置（Pydantic BaseSettings）、数据库会话、Redis、日志、异常

### 基于动作的路由
所有端点使用动作后缀代替 RESTful HTTP 动词：
- `POST /recordings/create`、`GET /recordings/list`、`GET /recordings/get?recording_id=...`
- `POST /recordings/update`、`POST /recordings/delete`
- `/skills/*` 和 `/runs/*` 遵循相同模式
- `GET /health`——数据库连接检查

### 响应格式
所有响应使用信封格式：`{"code": 0, "msg": "ok", "data": {...}}`。在 `schemas/base.py` 中定义为 `ApiResponse[T]`。前端 axios 拦截器自动解包 `data`。

### 数据库
- 通过 Docker Compose 提供 PostgreSQL，SQLAlchemy 2.x，Alembic 迁移
- 所有模型继承 `UUIDPrimaryKeyMixin` + `TimestampMixin`（`id`、`created_at`、`updated_at`）
- JSON 列：`Recording.events`、`Recording.meta`；`Skill.definition`；`Run.input_payload`、`Run.result_payload`、`Run.logs`

## 前端架构

Vue 3 控制台（`apps/console/src/`）使用：
- **Router**（`router/index.ts`）：所有路由包裹在 `MainLayout` 中
- **Stores**（`stores/`）：Pinia——`app.ts`（全局状态、API 连通性），以及按资源划分的 recordings、skills、runs store
- **API 客户端**（`api/`）：按资源分的 Axios 模块；拦截器透明解包 `ApiResponse.data`
- 路径别名 `@` 映射到 `src/`

前端测试在 `src/__tests__/` 中，使用 Vitest + `@vue/test-utils`。使用 Pinia 的测试必须在 `beforeEach` 中调用 `setActivePinia(createPinia())`。

### API 代理 vs 直连模式
通过 `apps/console/.env` 中的 `VITE_USE_DEV_PROXY` 控制：
- `true`——Vite 代理 `/api` 请求（避免 CORS，同源）
- `false`——直接调用 `VITE_API_BASE_URL`；需要在 API 端设置 `CORS_ALLOWED_ORIGINS`

## 扩展架构

基于 WXT 框架构建（`apps/extension/`）：
- `entrypoints/background.ts`——Service Worker（MV3）
- `entrypoints/content.ts`——注入页面用于事件捕获和 DOM 变更追踪
- `entrypoints/popup/`——Vue 3 录制 UI（状态、名称输入、开始/停止）
- 录制状态通过扩展存储持久化

### DOM 变更追踪

录制期间，扩展通过 `MutationObserver` 监控顶层文档和同源 iframe 文档的 DOM 变化。关键文件：

- `src/recorder/mutation-observer.ts`——`DomMutationTracker` 类：观察 childList/attributes/characterData 变更，以约 500ms 间隔批量处理，映射到 AST 节点，发出 `DomMutationRecord[]`
- 变更记录存储在 `RecorderState.domMutations` 中，提交时包含在 `meta.domMutations` 中
- 每条变更携带：目标元素信息、变更详情（什么改变了）、AST 关联（精确/祖先/无 + 降级）、框架信息、区域上下文
- 噪声过滤：script/style/svg 标签、框架管理属性（_ngcontent、data-v-）、扩展元素
- Iframe 支持：同源 iframe 递归观察；跨域静默跳过
- 前端：RecordingDetailPage 上的"DOM Changes"标签页显示变更时间线，包含类型、目标、AST 匹配和变更详情

## 初始状态解析器——DOM 到 AST 规则（客户端，正逐步被服务端替代）

> **注意**：本节文档记录的是现有的客户端 DOM walker（`initial-state.ts`）。主要的 AST 管道正在迁移到服务端 HTML → Full AST（见上方"当前项目方向"）。这些客户端规则对扩展代码仍然有效，但新的 AST 能力应在服务端的 `apps/api/app/services/html_ast_parser.py` 中构建。

扩展的 `initial-state.ts` 从 live DOM 构建简化 AST（StateNode 树）。修改或扩展解析器时，以下规则是**强制约束**。

### 核心原则：统一递归 + 降级

解析器通过统一的递归流程处理每个 DOM 节点：

```
walkNode(el):
  1. classifyNode(el)     → 统一分类（已知组件 > class/tag/id > 原生 HTML > null）
  2. tryProcess(el, type) → 尝试用匹配的处理器提取
  3. 处理器返回空 → 降级到 walkChildren 通用递归
  4. walkChildren 也空 + 存在可见内容 → localHtml 降级（type: 'custom'）
```

**任何分支失败都不得静默丢弃内容**。处理器返回 `[]` 意味着"我无法处理这个，请降级"——而非"这个元素没有内容"。

### 首要原则：DOM 保真优先

解析器不是"理解页面再重写它"——而是"忠实地将页面转录为结构化中间表示"。

1. **原始 DOM 树关系优先**——输出 JSON 的 `children` 顺序必须匹配原始 DOM 顺序
2. **兄弟顺序优先**——绝不为语义抽象重排兄弟节点
3. **节点类型优先**——每个 DOM 节点应按其实际类型保留
4. **隐藏节点必须保留**——通过 `cssState` 标注，绝不跳过
5. **复杂节点必须保留 localHtml 降级**——当语义提取不充分时
6. **绝不重组原始页面结构**以形成"标题 + 内容"或"分组 + 详情"等抽象

### 分类优先级（从高到低，首次匹配生效）

1. **已知组件库元素**——如 `el-select`、`ant-cascader`、`van-cell`、`n-date-picker`。作为整体组件类型处理，**绝不拆解为内部 DOM 结构**（例如 el-select 内部有 input 仍然视为 select）。组件分类器（`component-classifier.ts`）使用前缀无关检测，覆盖 12+ UI 库。

2. **可通过 class/tag/id 识别的自定义结构**——如 `class="xx-select"`、`role="listbox"` 等开发者命名的组件，通过模式匹配分类。

3. **标准 HTML 语义元素**——`<table>`、`<input>`、`<select>`、`<button>`、`<a>` 等，按原生语义处理。

4. **无法分类的元素**——递归 walkChildren 提取子节点结构。如果存在可见内容但无法提取，生成 `type: 'custom'` 节点并附带 `localHtml`（最多 500 字符）。

### 元素类型规则

**表格**：提取表头和行数据。每行中的每个单元格都经过统一的 `walkNode` 处理路径（不是纯文本提取）。`table` 节点既有 `rows`（文本摘要用于前端展示）也有 `children`（来自 walkNode 的完整结构供 Agent 分析）。

**Iframe**：同源 iframe 通过 `contentDocument` 递归解析（遵循相同规则）；跨域 iframe 静默跳过。生成 `blockType: 'iframe-content'` 的 section 节点。支持多级嵌套 iframe。

**导航区域**：通过 HTML5 语义标签（`nav`、`aside`、`header`、`footer`）和 ARIA 角色（`role="navigation"` 等）在主内容根**之外**检测。支持嵌套子菜单（如 `el-submenu` + `aria-haspopup`）。叶节点为 `link` 或 `button` 类型，携带 `href`、`active` 状态和 `selector`。**导航和菜单内容绝不能跳过或丢弃**——它们对于跨系统操作场景至关重要。

**表单容器**：通过已知的 form-item 模式（`.el-form-item`、`.ant-form-item` 等）检测，作为标签 + 控件对处理。如果内容区域包含多个交互元素（≥2 个非简单控件，或 ≥3 个简单控件），递归展开为 `group` + `children`，而非扁平化为单个叶节点。如果 processFormItem 返回空（例如 `el-form-item__actions` 实际上是按钮容器），则**降级**到通用 walkChildren。

### 多框架初始状态合并

一个页面可能包含多个框架（顶层 + 一个或多个 iframe，iframe 可能嵌套）。每个框架独立运行内容脚本并发送 `RECORDING_INITIAL_STATE`。background 的 `setInitialState`（`state.ts`）处理方式如下：

- **同一 frameId 的重复发送**（例如 content.ts 两次遍历）→ 基于评分竞争替换（保留评分更高的）
- **不同 frameId** → **始终合并**。iframe 的 stateTree 作为 `iframe-content` section 追加到现有状态中。无论嵌套深度或 iframe 数量，每个框架的内容都被保留
- **绝不用替换代替合并**——顶层框架的导航/菜单和 iframe 的业务内容同等重要；iframe 中更高的节点数或评分不能覆盖顶层内容

### 可见性处理

所有遍历逻辑使用统一的可见性处理——**绝不跳过不可见元素**。`shouldSkip` 仅过滤 `SKIP_TAGS`（script/style/svg 等纯技术标签），不检查 `isVisible`。不可见元素（`display:none`、`visibility:hidden`）仍然被解析并通过 `cssState` 字段标注。`display:none` 表示未渲染且不可点击（如收起的菜单）；`visibility:hidden` 表示占据空间但仍接收交互。

**不同的遍历类型（导航 vs 内容）不能使用不同的可见性处理**——所有遍历共享相同规则。

### 截断降级

当 `MAX_NODES`（300）或 `MAX_NAV_ITEMS`（100）导致收集被截断时，**剩余内容不能被静默丢弃**。被截断的导航区域会在 section 节点上附加 `localHtml`，保留原始 HTML 以供后续展开。

### 信息保留原则

优先保留对 Agent 理解页面功能有分析价值的信息：页面做什么、有哪些交互元素、当前状态是什么。没有直接分析价值但后续可能需要的信息（如完整导航菜单原始 HTML）存储在 `localHtml` 中，不在 Agent 的主要分析路径中。

### 禁止做法

- **绝不基于假设跳过元素**——除 `SKIP_TAGS` 外不设硬编码跳过列表。所有元素都必须处理（包括不可见的）。绝不假设开发者遵循语义化 HTML 规范。
- **绝不拆解已知复合组件**——`el-select` 是一个 `select` 节点，而非 `input` + `div` + `ul`。组件边界就是分类边界。
- **绝不生成空容器**——children 为空的 section/group 节点必须丢弃。
- **绝不静默丢弃内容**——任何分类失败都必须降级到通用递归；如果通用递归也失败且存在可见内容，必须生成 localHtml 降级。被截断的内容必须保留 localHtml。
- **绝不扁平化复杂结构**——如果容器有多个交互子元素，必须递归展开为子树，不能扁平化为单个叶节点 + localHtml。
- **绝不添加专用逻辑**——所有处理规则必须通用，不能有针对特定组件库或页面结构的 if-else 分支。所有遍历类型共享相同的过滤和处理规则。
- **绝不为语义整洁而重组页面结构**——不要将并列兄弟节点合并为"标题 + 内容"块，不要为"清晰"改变节点边界，不要为"整洁"重排节点，不要吞没中间的提示/警告/按钮组/状态文本以形成"标题 + 内容"模式。
- **绝不将复杂单元格降级为纯文本**——表格图片列必须保留 `src`，操作列必须保留真实按钮，input-number 必须作为结构化控件保留。
- **绝不将多个按钮拼接为单个字符串**——按钮必须作为独立节点保留。
- **绝不只保留主控件而忽略兄弟辅助信息**——form-item 中的提示/描述/状态文本必须保留。

### 输出结构

- **容器节点**（`section`、`group`）：有 `children[]`、`blockType`、`label`。**没有 `selector`**。截断时可携带 `localHtml`。
- **叶节点**（`input`、`select`、`button`、`link`、`custom` 等）：有 `selector`、`value`、`label`。**没有 `children`**。
- **`table` 节点**：可以是叶节点（`rows[][]`）或容器节点（`children[]`），取决于单元格复杂度。
- **`localHtml`**：仅用于语义提取不充分的叶节点，最多 500 字符。
- **`rawHtmlSnapshot`**：独立的仅调试用完整 HTML 快照，不属于 AST。

### 测试

多场景测试（`apps/extension/src/__tests__/multi-scenario.test.ts`）覆盖 8 种 fixture 类型：企业官网、管理后台、H5 移动端、多导航文档页、无语义标签页、数据看板、Element UI 嵌套菜单 + iframe、复杂嵌套结构（form-item 内嵌表格/子表单、表格操作列）。**任何解析器改动都必须通过所有现有 fixture 测试。新的解析行为必须包含对应的 fixture 和测试。**

### 参考测试用例

`apps/extension/src/__tests__/fixtures/lottery-page.html` 是来自真实用户页面的完整 HTML fixture。`apps/extension/src/__tests__/fixtures/lottery-page-expected.jsonc` 是**当前（有问题的）解析器输出**，通过 `//` 和 `/* */` 注释标注了具体问题。这不是正确的期望输出——而是问题清单。新的解析器改动必须解决所有标注的问题。

## 基础设施

Docker Compose（`infra/docker/docker-compose.yml`）提供：
- **PostgreSQL 16**——主数据库
- **Redis 7.4**——缓存/队列
- **MinIO**——对象存储（端口 9000 API、9001 控制台）

将 `.env.example` 复制为仓库根目录的 `.env`。Console 有自己的 `apps/console/.env.example`。

## Worker

Worker（`apps/worker/app/`）运行一个轮询式 `JobRunner` 循环。目前是脚手架——心跳日志已实现，但作业执行逻辑尚未构建。
