# CLAUDE.zh.md

给 Claude Code（claude.ai/code）在本仓库工作时的指引（中文版）。

> **多 Agent 同步规则**：本文件与 `CLAUDE.md`（英文）和 `AGENTS.md`（给
> Codex 等 AI 编码 Agent）保持同步。修改时三个文件一起改。

## 项目简介

WebAgentFlow —— 一个以 Agent 为驱动的 web 工作流引擎 monorepo。

- `apps/console` —— Vue 3 操作控制台。
- `apps/api` —— FastAPI 后端（routes / services / schemas / LLM provider）。
- `apps/worker` —— 异步 worker（当前是骨架）。
- `apps/validation-site` —— 自主探索的自建验证站点。
- `apps/cli` —— Python CLI（`wagent`）与 `verify-scenario` Claude Code skill。
- `packages/` —— 共享 TypeScript 包。

**产品形态**（WebAgentFlow 到底是什么）：
[`docs/product-model.zh.md`](./docs/product-model.zh.md)。提议任何
新功能 / 新阶段前**先读这份**。如果你的提议在那份文档里找不到位置，
**先停下问用户**，不要擅自发明新 Agent / 新阶段 / 新循环再反向改代码。

深度架构 / 演进：[`docs/architecture.zh.md`](./docs/architecture.zh.md)。

## AI 编码 Agent —— 执行边界（硬约束）

WebAgentFlow **本身就是**一个自主 web 操作引擎，内置有项目自己的
**Supervisor Agent**，位于
`apps/api/app/services/learning/autonomous_explorer.py::_run_supervisor`，
观察原子 schema 定义在
`apps/api/app/services/learning/supervisor_observations.py`。

**应用**才是执行者。**用户**是操作者。**AI 编码 Agent**（Claude Code、
Codex 等）主要负责写代码。AI 也可以通过项目提供的
**`verify-scenario` skill** 触发一次运行 —— 但必须遵守下面的契约。
通过 skill 调用是可审计的（走 HTTP API、持久化进 `exploration_runs`、
输出原始 Supervisor 裁决 + scorecard），所以验证逻辑依然成立：裁决由项
目内 Supervisor Agent 产出，AI 只是中转原样呈现。

**不得**通过其他任何方式驱动引擎 —— 直接 `curl`
`/exploration/autonomous-runs`、内联 Playwright 脚本、直接导入
`run_autonomous_exploration` 都在禁止范围内。

### 禁止做

- 用 curl、fetch、httpx 或除 `verify-scenario` skill 的 CLI 以外的任何
  HTTP 客户端调用 `POST /exploration/autonomous-runs` 或 `.../stream`。
- 导入 `run_autonomous_exploration` 并在进程内直接驱动 Playwright。
- 用"通过了"/"跑过了"/"works"之类的总结概括结果，**而不引用**这次运行
  的 `supervisor.verdict` 原值和 5 项 scorecard 得分原值。
- 汇报时省略 `run_id` —— 用户靠 `run_id` 在 WebAgentFlow 控制台里查这次
  运行。CLI **不会**输出前端 URL：它只是后端客户端，不该知道 console
  跑在哪台机器哪个端口。
- 伪造或篡改裁决。skill 退出非 0 就如实报告非 0；退出 0 就报告成功，
  **同时引用 Supervisor 的 confidence + summary 原文**。
- 在循环里反复调 skill 来"平均"或"复核"结果 —— 每次调用都是一次真实
  的 Playwright + LLM 运行。

### 允许做

- 读任意文件；跑只读诊断（`ruff`、`vue-tsc`、openapi 检查、import 验证等）。
- 跑**不涉及** `autonomous_explorer.run_autonomous_exploration` 的单元 /
  集成测试。
- 按用户要求修改代码。
- **调用 `verify-scenario` skill**，当用户的请求暗示需要一次真实运行时
  （"verify X"、"跑一下 spec Y"、"check workflow Z"）。如实转发 Supervisor
  的裁决 + scorecard + `run_id` 给用户；如果裁决不是 `success`，再给出
  具体的分析 / 下一步建议。
- 当 skill 无法使用时（API 没起、或需要手动检查），请用户去 workbench
  亲自跑。

### 验证权威顺序

1. **用户** —— 在 `/exploration/autonomous` 或 history 详情页中确认或
   驳回一次运行。
2. **项目内 Supervisor Agent** —— `_run_supervisor` 的 LLM 调用 + 基于规则
   的 `page_verification` 评分卡。

AI 编码 Agent 是**中转**，不是验证者。它不在这个链上。使用 skill 时的
职责是把 (1) + (2) 原样转给用户。

### 汇报方式

用了 skill 之后，结构应该是：

**永远先报 `pass_gate.status`** —— 这是权威结果。只有 `pass` 才算真
通过；`unverified` **不是**通过。

干净通过：

> "跑了 `verify-scenario` skill
> （`wagent verify --spec-id login --scenario valid_credentials`）。
> pass_gate：`pass`。Supervisor 裁决：`success`（置信度 `high`，
> 来源 `llm`）。Scorecard 5/5：……。Supervisor summary：……引用原文……。
> run_id：`<uuid>`。"

未完成验证（MiniMax 过载 / LLM fallback）：

> "跑了 `wagent verify ...`。**pass_gate：`unverified`（不是通过）**。
> pass_gate.reasons：'supervisor ran in fallback mode
> (error_kind=provider_error) — LLM did not independently verify this
> run'。规则侧 5/5 机械通过，但要真通过必须 LLM 独立复核。
> run_id：`<uuid>`。"

未完成验证（LLM 低置信度）：

> "跑了 `wagent verify --spec-id login --scenario invalid_credentials`。
> **pass_gate：`unverified`**。pass_gate.reasons：'supervisor
> confidence=medium — scenario requires high-confidence LLM
> agreement'。Supervisor 没法确认 role=alert 是否真展示，提示 prompt
> 信号不够。……"

硬失败（偏离规格）：

> "跑了 `wagent verify ...`。**pass_gate：`fail`**。pass_gate.reasons：
> '……'。……"

没跑任何东西时，说你改了什么、交给用户跑：

> "改了 X/Y/Z。你去 workbench（或用 skill）跑 D1，如果看到 A 就说明修好了。"

不要这样说：

> "我跑了一下，工作正常。"

## Git 安全规则

- 以 `-local` 结尾的分支是本地专用的，**不得 push**。
- `git push` 前先看当前分支名。若以 `-local` 结尾，停下；如果要公开该分支
  的工作，先在同一 commit 上建立或移动一个非 `-local` 分支，再 push 那个。

## 常用命令

### 初始化 & 开发

```bash
# 安装依赖
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'
.venv/bin/python -m playwright install chromium   # 自主探索需要

# 启动基础设施（PostgreSQL / Redis / MinIO）
docker compose -f infra/docker/docker-compose.yml up -d

# 应用数据库迁移
pnpm run db:migrate:api

# 一键起全部（console + api + worker + validation-site）
pnpm run dev
pnpm run dev:lan                # 绑到 0.0.0.0，局域网可访问

# 单独起各服务
pnpm run dev:console            # Vite，端口 5174
pnpm run dev:api                # Uvicorn，端口 8001
pnpm run dev:worker             # Python 文件改动自动 reload（走 watchfiles）
pnpm run dev:validation         # 验证站点，端口 5175
```

### 构建 / Lint / 测试

```bash
pnpm run build                  # 全部
pnpm run build:packages         # 构建 console 前要先构建共享包
pnpm run build:console

pnpm run lint                   # ESLint + Ruff
pnpm run format                 # Prettier + Ruff

pnpm run test                   # Vitest（console）
pnpm run test:dev               # watch
pnpm run test:coverage

cd apps/api && .venv/bin/pytest
cd apps/api && .venv/bin/pytest tests/test_health.py -v
cd apps/api && .venv/bin/pytest -k "test_create" -v
```

## 关键文件位置

**当前焦点 —— 自主探索子系统：**

- `apps/api/app/services/learning/autonomous_explorer.py` —— 编排器 +
  SSE 事件分发 + Supervisor LLM 调用。
- `apps/api/app/services/learning/page_analyzer.py` —— 实时页面元素发现
  （纯结构分类）。
- `apps/api/app/services/learning/action_planner.py` —— 多字段规划器，按
  semantic_role 匹配。
- `apps/api/app/services/learning/supervisor_observations.py` ——
  LLM 观察原子 schema + 代码侧裁决推导。
- `apps/api/app/services/learning/page_verification.py` —— 基线对照器，输出
  5 项评分。
- `apps/api/app/routers/exploration.py` ——
  `/exploration/autonomous-runs[/stream]`、
  `/exploration/specs[/{id}]`（workbench 拉 spec 做预填用）、
  `/exploration/autonomous-runs[/{run_id}]`（落库后的 run 历史）。
- `apps/api/app/routers/validation_api.py` —— 验证站点 mock 后端。
- `apps/validation-site/specs/<page>.{md,assertions.json}` —— 基线定义。
- `apps/validation-site/src/pages/IndexPage.vue` —— `/` 下的测试页目录。
- `apps/console/src/pages/AutonomousWorkbenchPage.vue` —— 用户驱动的工作台。
- `apps/console/src/api/autonomousStream.ts` —— SSE 客户端（POST + fetch 流）。

**稳定基础：**

- `apps/api/app/services/html_ast_parser.py` —— HTML → Full AST（`lxml`）。
- `apps/api/app/services/execution/execution_runtime.py` ——
  autonomous_explorer 用的 Playwright chromium 生命周期封装。
- `apps/api/app/schemas/` —— Pydantic 契约（page_analysis、
  page_verification、llm、ast、common）。

## 架构总览

- **Routers**（`routers/`）—— 只放 HTTP 端点。
- **Services**（`services/`）—— 业务逻辑，分包成 `execution/` 和 `learning/`。
- **Repositories**（`repos/`）—— SQLAlchemy 数据访问。
- **Models**（`models/`）—— ORM，用 JSON 列存放灵活字段。
- **Schemas**（`schemas/`）—— Pydantic 请求 / 响应模型。
- **Core**（`core/`）—— 配置、DB 会话、Redis、日志、异常。

### 响应外壳

所有接口统一为 `{"code": 0, "msg": "ok", "data": {...}}`，由
`ApiResponse[T]` 定义。前端 axios 拦截器自动解包 `data`。

### 路由规范

- `POST /exploration/autonomous-runs[/stream]` —— 跑一次场景（SSE
  流式版为主）。
- `GET /exploration/specs[/{id}]` —— workbench 拉 spec 做预填。
- `GET /exploration/autonomous-runs[/{run_id}]` —— 落库后的 run 历史。
- `GET /exploration/screenshots/{filename}` —— 截图文件服务。

### 数据库

- PostgreSQL 16 + SQLAlchemy 2.x + Alembic。
- 仅一张表：`exploration_runs`（autonomous 运行历史）。旧产品形态
  留下的其他表已全部删除。
- `ExplorationRun` 继承 `UUIDPrimaryKeyMixin` + `TimestampMixin`，灵活
  字段走 JSON 列（`strategy_json`、`result_snapshot_json` 等）。

### 前端

- Vue 3 + Vite + vue-router + Pinia + Ant Design Vue。
- 路径别名 `@` → `src/`。
- 测试在 `src/__tests__/`（Vitest + `@vue/test-utils`）。
- `VITE_USE_DEV_PROXY=true` 时 Vite 把 `/api/*` 代理到后端。

## 另见

- [`docs/product-model.zh.md`](./docs/product-model.zh.md) —— **产品形态
  权威文档**：L1/L2/L3 生命周期阶段（自主学习 / 用户引导学习 /
  实际工作）、七个 Agent、跨阶段不变量。**先看这份**。
- [`docs/architecture.zh.md`](./docs/architecture.zh.md) —— AST 双轨、
  服务子包结构、iframe 处理。
- [`docs/scope-boundaries.zh.md`](./docs/scope-boundaries.zh.md) —— 当前交付里程碑
  **明确不做**的内容。
- [`docs/roadmap.zh.md`](./docs/roadmap.zh.md) —— v0.1 阶段里程碑。
- [`docs/dev-setup.zh.md`](./docs/dev-setup.zh.md) —— 完整的开发环境
  搭建步骤（比上面的"常用命令"更详细，面向新 contributor）。
- [`docs/iterations/README.md`](./docs/iterations/README.md) ——
  **迭代文档规范**（按 Phase 组织的目录，每次迭代留 `intent.md` /
  `plan.md` / `review.md` 三件套）。开始一轮非平凡工作前先写 `intent.md`；
  `codex-review` skill 会自动把这些作为上下文喂给 Codex。
- [`CLAUDE.md`](./CLAUDE.md) —— 英文原版。
- [`AGENTS.md`](./AGENTS.md) —— 给 Codex 等 AI 编码 Agent 的版本。
