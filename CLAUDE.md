# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WebAgentFlow is a monorepo for an agent-driven web workflow engine with:
- Vue 3 frontend console (`apps/console`)
- FastAPI backend API (`apps/api`)
- Python worker service (`apps/worker`)
- Chrome MV3 browser extension recorder (`apps/extension`, built with WXT)
- Shared TypeScript packages (`packages/`)

## Common Commands

### Setup & Development
```bash
# Install dependencies
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'

# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
pnpm run db:migrate:api

# Run all components
pnpm run dev             # Local development
pnpm run dev:lan         # LAN accessible (binds to 0.0.0.0)

# Run individual components
pnpm run dev:console     # Vite dev server (port 5174)
pnpm run dev:api         # Uvicorn dev server (port 8001)
pnpm run dev:worker
```

### Build, Lint, Test
```bash
# Build
pnpm run build              # Build all
pnpm run build:packages     # Build shared packages (required before console)
pnpm run build:console
pnpm run build:extension

# Lint & Format
pnpm run lint               # ESLint + Ruff
pnpm run format             # Prettier + Ruff

# Frontend tests (Vitest)
pnpm run test               # Run all console tests
pnpm run test:dev           # Watch mode
pnpm run test:coverage
pnpm run test:single        # Single file via env var

# API tests (Pytest)
cd apps/api && .venv/bin/pytest                             # All tests
cd apps/api && .venv/bin/pytest tests/test_health.py -v    # Single file
cd apps/api && .venv/bin/pytest -k "test_create" -v        # Pattern match
```

## Git Safety Rules

- Any development branch whose name ends with `-local` is local-only and must never be pushed to any remote.
- Before running `git push`, always check the current branch name first. If the branch ends with `-local`, stop and do not push.
- If the work on a `-local` branch needs to be published, create or move a non-`-local` branch to the same commit first, then push that branch instead.

## API Architecture

The FastAPI backend (`apps/api/app/`) uses a strict layered architecture:
- **Routers** (`routers/`): HTTP endpoints only, action-based routes
- **Services** (`services/`): Business logic
- **Repositories** (`repos/`): SQLAlchemy data access
- **Models** (`models/`): ORM models with JSON columns for flexible payloads
- **Schemas** (`schemas/`): Pydantic request/response models
- **Core** (`core/`): Config (Pydantic BaseSettings), DB session, Redis, logging, exceptions

### Action-Based Routes
All endpoints use action suffixes instead of RESTful HTTP verbs:
- `POST /recordings/create`, `GET /recordings/list`, `GET /recordings/get?recording_id=...`
- `POST /recordings/update`, `POST /recordings/delete`
- Same pattern for `/skills/*` and `/runs/*`
- `GET /health` — DB connectivity check

### Response Format
All responses use an envelope: `{"code": 0, "msg": "ok", "data": {...}}`. Defined in `schemas/base.py` as `ApiResponse[T]`. The frontend axios interceptor unwraps `data` automatically.

### Database
- PostgreSQL via Docker Compose, SQLAlchemy 2.x, Alembic migrations
- All models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` (`id`, `created_at`, `updated_at`)
- JSON columns: `Recording.events`, `Recording.meta`; `Skill.definition`; `Run.input_payload`, `Run.result_payload`, `Run.logs`

## Frontend Architecture

The Vue 3 console (`apps/console/src/`) uses:
- **Router** (`router/index.ts`): All routes wrapped in `MainLayout`
- **Stores** (`stores/`): Pinia — `app.ts` (global state, API connectivity), plus per-resource stores for recordings, skills, runs
- **API client** (`api/`): Axios modules per resource; interceptor transparently unwraps `ApiResponse.data`
- Path alias `@` maps to `src/`

Frontend tests live in `src/__tests__/` using Vitest + `@vue/test-utils`. Tests using Pinia must call `setActivePinia(createPinia())` in `beforeEach`.

### API Proxy vs Direct Mode
Controlled by `VITE_USE_DEV_PROXY` in `apps/console/.env`:
- `true` — Vite proxies `/api` requests (avoids CORS, same-origin)
- `false` — Direct calls to `VITE_API_BASE_URL`; requires `CORS_ALLOWED_ORIGINS` set on API

## Extension Architecture

Built with WXT framework (`apps/extension/`):
- `entrypoints/background.ts` — Service worker (MV3)
- `entrypoints/content.ts` — Injected into pages for event capture
- `entrypoints/popup/` — Vue 3 recording UI (status, name input, start/stop)
- Recording state is persisted via extension storage

## 初始状态解析器 — DOM 转 AST 规则

扩展的 `initial-state.ts` 将实时 DOM 构建为简化 AST（StateNode 树）。修改或扩展解析器时，以下规则为**强制约束**。

### 核心原则：统一递归 + 回溯

解析器以统一的流程递归处理每个 DOM 节点：

```
walkNode(el):
  1. classifyNode(el)     → 统一分类（已知组件 > class/tag/id > 原生HTML > null）
  2. tryProcess(el, type) → 用对应处理器尝试提取
  3. 处理器返回空 → 回溯到 walkChildren 通用递归
  4. walkChildren 也为空 + 有可见内容 → localHtml 兜底（type: 'custom'）
```

**任何分支失败都不能静默丢弃内容**。处理器返回 `[]` 意味着"我处理不了，请回溯"，不意味着"这个元素没有内容"。

### 最高原则：DOM 保真优先

解析器不是在"理解页面后重写页面"，而是在"忠实转录页面为结构化中间表示"。

1. **DOM 原始树形关系优先** — 输出 JSON 的 children 顺序必须和原始 DOM 顺序一致
2. **sibling 顺序优先** — 不允许为了抽象语义重组 sibling 顺序
3. **节点类型优先** — 每个 DOM 节点应该按其实际类型保留
4. **hidden 节点也必须保留** — 通过 `cssState` 标注，不跳过
5. **复杂节点保留 localHtml fallback** — 语义提取不充分时必须兜底
6. **绝对不要为了形成"标题 + 内容""分组 + 明细"这类更抽象的结构，去硬重组页面原始结构**

### 分类优先级（从高到低，首次匹配生效）

1. **已知组件库元素** — 如 `el-select`、`ant-cascader`、`van-cell`、`n-date-picker`，按组件整体类型处理，**不拆解其内部 DOM 结构**（如 el-select 内部有 input，仍作为 select 处理）。组件分类器（`component-classifier.ts`）使用前缀无关检测，覆盖 12+ 组件库。

2. **class/tag/id 可识别的自定义结构** — 如 `class="xx-select"`、`role="listbox"` 等开发者命名的组件，按模式匹配分类。

3. **标准 HTML 语义元素** — `<table>`、`<input>`、`<select>`、`<button>`、`<a>` 等，按原生语义处理。

4. **无法分类的元素** — 递归 walkChildren 尝试提取子节点结构。如有可见内容但无法提取，产生 `type: 'custom'` 节点并附带 `localHtml`（最大 500 字符）。

### 各类型元素规则

**表格**：提取表头和行数据。每行的每个单元格都通过 `walkNode` 走统一的处理路径（而非纯文本提取）。`table` 节点同时有 `rows`（文本摘要，用于前端展示）和 `children`（walkNode 产出的完整结构，用于 Agent 分析）。

**Iframe**：同源 iframe 通过 `contentDocument` 递归解析（遵循相同规则），跨域静默跳过。产生 `blockType: 'iframe-content'` 的 section 节点。支持多层嵌套 iframe。

**导航区域**：通过 HTML5 语义标签（`nav`、`aside`、`header`、`footer`）和 ARIA 角色（`role="navigation"` 等）检测 main content root **外部**的导航区域。支持嵌套子菜单（如 `el-submenu` + `aria-haspopup`）。叶子节点为 `link` 或 `button` 类型，带 `href`、`active` 状态和 `selector`。**导航、菜单栏等内容不得被跳过或丢弃**，它们对跨系统操作场景有重要价值。

**表单容器**：通过已知 form-item 模式检测（`.el-form-item`、`.ant-form-item` 等），作为 label + control 对处理。如果内容区包含多个可操作元素（非简单控件 ≥2 个，或简单控件 ≥3 个），递归展开为 `group` + `children`，而非压扁成单个 leaf 节点。如果 processFormItem 返回空（如 `el-form-item__actions` 实际是按钮容器），**回溯**到通用 walkChildren。

### 多 frame 初始状态合并

页面可能包含多个 frame（顶层 + 一个或多个 iframe，iframe 可嵌套）。每个 frame 独立运行 content script，独立发送 `RECORDING_INITIAL_STATE`。background 的 `setInitialState`（`state.ts`）按以下规则处理：

- **同一 frameId 的重复发送**（如 content.ts 的两次 pass）→ 分数竞争替换（取高分的）
- **不同 frameId** → **一律合并**。iframe 的 stateTree 作为 `iframe-content` section 追加到已有状态中。不管嵌套几层、有几个 iframe，每个 frame 的内容都会被保留
- **不得用替换代替合并** — 顶层 frame 的导航/菜单 和 iframe 的业务内容同等重要，不能因为 iframe 节点多/分数高就覆盖顶层

### 可见性处理

所有 walk 逻辑统一处理可见性，**不跳过不可见元素**。`shouldSkip` 只过滤 `SKIP_TAGS`（script/style/svg 等纯技术标签），不检查 `isVisible`。不可见元素（`display:none`、`visibility:hidden`）仍然被解析，通过 `cssState` 字段标注状态。`display:none` 表示不渲染不可点击（如折叠菜单），`visibility:hidden` 表示占位但仍可接收交互。

**不得对不同类型的 walk（导航 vs 内容）做不同的可见性处理** — 所有 walk 共享同一套规则。

### 超限兜底

当 `MAX_NODES`（300）或 `MAX_NAV_ITEMS`（100）导致采集被截断时，**剩余内容不得静默丢弃**。被截断的导航区域在 section 节点上附带 `localHtml`，保存原始 HTML 以便后续扩展。

### 信息保留原则

优先保留对 Agent 理解页面功能有分析价值的信息：页面是做什么的、有哪些可操作元素、当前状态是什么。暂时无直接分析价值但后续可能需要的信息（如完整导航菜单的原始 HTML），用 `localHtml` 暂存，不进入 Agent 的主分析管线。

### 禁止事项

- **不得基于假设跳过元素** — 不设硬编码的跳过列表（`SKIP_TAGS` 除外）。所有元素均需处理（包括不可见元素）。不假设开发者遵循语义化 HTML 规范。
- **不得拆解已知复合组件** — `el-select` 是一个 `select` 节点，不是 `input` + `div` + `ul`。组件边界就是分类边界。
- **不得产生空容器** — section/group 节点如果 children 为空，丢弃该节点。
- **不得静默丢弃内容** — 任何分类失败必须回溯到通用递归，通用递归也失败且有可见内容时必须产生 localHtml 兜底。超限截断时必须保留 localHtml。
- **不得压扁复杂结构** — 如果一个容器内有多个可操作子元素，必须递归展开为子树，不能压成单个 leaf + localHtml。
- **不得添加特化逻辑** — 所有处理规则必须通用，不针对特定组件库或页面结构做 if-else 分支。不同类型的 walk 共享同一套过滤和处理规则。
- **不得为了语义整理去硬重组页面结构** — 不把多个并列 sibling 合并成"标题+内容"块，不为了"更清晰"改变节点边界，不为了"更整洁"重排节点顺序，不为了"标题+内容"格式吞掉中间的 tip/alert/button group/status text。
- **不得把复杂 cell 退化成纯文本** — 表格图片列保留 `src`，操作列保留真实按钮，input-number 保留为结构化控件。
- **不得把多个按钮拼成一个字符串** — 按钮必须作为独立节点保留。
- **不得只保留主控件忽略同容器辅助信息** — form-item 内的 tip/description/status text 必须保留。

### 输出结构

- **容器节点**（`section`、`group`）：带 `children[]`、`blockType`、`label`。**无 `selector`**。截断时可带 `localHtml`。
- **叶子节点**（`input`、`select`、`button`、`link`、`custom` 等）：带 `selector`、`value`、`label`。**无 `children`**。
- **`table` 节点**：可以是叶子（`rows[][]`）或容器（`children[]`），取决于单元格复杂度。
- **`localHtml`**：仅用于语义提取不充分的叶子节点，最大 500 字符。
- **`rawHtmlSnapshot`**：独立的调试用完整 HTML 快照，不属于 AST。

### 测试

多场景测试（`apps/extension/src/__tests__/multi-scenario.test.ts`）覆盖 8 种 fixture：企业官网、后台管理、H5 移动端、多导航文档页、无语义标签页面、数据大盘、Element UI 嵌套菜单+iframe、复杂嵌套结构（form-item 内嵌表格/子表单、表格操作列）。**任何解析器改动必须通过所有现有 fixture 测试。新增解析行为必须同时新增对应 fixture 和测试。**

### 参考测试用例

`apps/extension/src/__tests__/fixtures/lottery-page.html` 是用户实际页面的完整 HTML fixture。`apps/extension/src/__tests__/fixtures/lottery-page-expected.jsonc` 是**当前有问题的解析器输出**，其中用户通过 `//` 和 `/* */` 注释标注了具体问题点。这不是正确的预期输出，而是需要修复的问题清单。新的解析器改动必须解决所有标注的问题。

## Infrastructure

Docker Compose (`infra/docker/docker-compose.yml`) provides:
- **PostgreSQL 16** — primary database
- **Redis 7.4** — caching/queuing
- **MinIO** — object storage (ports 9000 API, 9001 console)

Copy `.env.example` to `.env` at repo root. Console has its own `apps/console/.env.example`.

## Worker

The worker (`apps/worker/app/`) runs a polling `JobRunner` loop. Currently a scaffold — heartbeat logging is implemented but job execution logic is not yet built out.
