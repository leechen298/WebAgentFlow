# CLAUDE.zh.md

给 Claude Code（claude.ai/code）在本仓库工作时的指引（中文版）。

> **多 Agent 同步规则**：本文件与 `CLAUDE.md`（英文）和 `AGENTS.md`（给
> Codex 等 AI 编码 Agent）保持同步。修改时三个文件一起改。

## 项目简介

WebAgentFlow —— 一个以 Agent 为驱动的 web 工作流引擎 monorepo。

- `apps/console` —— Vue 3 操作控制台。
- `apps/api` —— FastAPI 后端（routes / services / schemas / LLM provider）。
- `apps/worker` —— 异步 worker（当前是骨架）。
- `apps/cli` —— Python CLI（`wagent`）。它是 `verify-scenario` 开发验证
  skill 的后端，同时已经包含 M11.0 runtime conversation CLI（`wagent
  conversation`）。M16 后续可能开放稳定 external CLI / Skill / Tool 接口。
- `packages/` —— 共享 TypeScript 包。

Fixture 页面位于本仓库外部。需要 fixture-backed verification 时，通过
`WAF_FIXTURE_SITE_URL` 和 `WAF_PAGE_SPEC_ROOT` 指向独立的 WebAgentFlow
Fixture-Site。

**产品形态**（WebAgentFlow 到底是什么）：
[`docs/product-model.zh.md`](./docs/product-model.zh.md)。提议任何
新功能 / 新交付里程碑前**先读这份**。如果你的提议在那份文档里找不到
位置，**先停下问用户**，不要擅自发明新 Agent / 新生命周期阶段 / 新循环
再反向改代码。

当前规划术语：

- 产品生命周期阶段是 **L1 / L2 / L3**。
- 交付里程碑是 **M10 / M11 / ...**。
- 生命周期阶段写 **L<N>**，交付里程碑写 **M<N>**。
- 里程碑迭代目录使用 `docs/iterations/m<N>/`。

当前交付状态：

- **M10 Path Asset Foundation / 路径资产基础** 已完成。
- **10.1 LearnedPath persistence**、**10.1.5 LearnedPath catalog** 和
  **10.2 replay execution + drift detection** 已交付。
- **M11.0 Runtime Conversation Shell & Agent Orchestration / 运行时沟通与
  Agent 编排** 已完成到 11.0.7。
- 11.1.1 Task Planning Domain Contract 已交付：17 个 schema 定义，
  24 个测试通过（`apps/api/app/schemas/task_planning.py`）。
- **M11.1 Task-to-Path Planning & Execution MVP / 任务到路径规划与执行
  MVP** 已完成 scoped path：retrieval / ranking、Task Path Planner / 任务
  路径规划器、confirmation gate、replay execution、Task Result Reporter /
  任务结果汇报器、tests / evidence closure。
- **M11.2 Runtime Observation & Realistic Web Hardening / 运行时观察与真实
  网页稳健性增强** 已完成当前 v0.1 scoped hardening track：11.2.2 已交付
  step-level `wait_result`；11.2.3 已交付 replay-level `observation_summary`；
  11.2.4.x 已补 realistic fixture planning / fixture shell / basic business
  fixture pages。
- **M11.3 Interactive Chat Productization / 交互式 chat 产品化** 已收口到
  11.3.7：`wagent chat` working runtime slices、11.3.6 runtime eval program
  `pass_with_caveats`、11.3.7 first-wave user-facing behavior eval `pass`。
- M11 runtime final closeout 记录在
  `docs/testing/results/m11-runtime-final-closeout-20260524.md`。
- M12 recovery / retry / abort / interruption 尚未开始。
- full learn-then-execute、page-wide automatic capability discovery、外部黑盒
  validation-site migration、L2 guided teaching、Teaching Guide Agent / 教学引导器
  （legacy: Agent H）仍属后续规划，除非里程碑文档另有说明。

内部 Agent 命名规则：

- 新文档和提示词优先使用主名称。
- A-H 标签只作为 legacy alias。
- 旧别名只在首次说明或引用旧文档时使用。
- 首次出现示例：`Task Path Planner / 任务路径规划器（legacy: Agent D）`。
- 后续提及时使用 `Task Path Planner / 任务路径规划器`。
- 不要擅自新增 Agent 字母编号；如果确实需要，必须先更新
  `docs/product-model.md`。

| 主名称 | 旧别名 | 生命周期 |
|---|---|---|
| Page Understanding Agent / 页面理解器 | Agent A | L1 |
| Attempt Evaluation Agent / 尝试评估器 | Agent B | L1 |
| Learning Report Agent / 学习报告器 | Agent C | L1 |
| Task Path Planner / 任务路径规划器 | Agent D | L3 |
| Task Result Reporter / 任务结果汇报器 | Agent E | L3 |
| Failure Recovery Agent / 失败恢复助手 | Agent F | L3 recovery |
| User Abort Handler / 用户中断处理器 | Agent G | L3 abort |
| Teaching Guide Agent / 教学引导器 | Agent H | L2 |

CLI 术语：

- 当前 `wagent verify` / `verify-scenario` 是开发验证 skill 后端。
- M11.0 runtime conversation CLI 是 `wagent conversation`，用户通过
  Conversation API 和 WebAgentFlow 沟通。第一版是非交互式 session /
  message / transcript / events CLI。
- M16 未来可能开放稳定 external CLI / Skill / Tool 接口，供外部调度和集成。
- 这三类入口必须区分清楚，不要混用。

项目级 Agent Skills：

- WebAgentFlow 专用的 coding-agent skills 放在 `.agents/skills/`。
- `.agents/skills/<skill-name>/SKILL.md` 是项目级 skill 的唯一事实来源，
  应随仓库提交。
- `.claude/skills/<skill-name>` 可以提交指向 `.agents/skills/<skill-name>` 的
  symlink，让 Claude Code 能发现同一套 skill，而不维护重复内容。
- 不要在 `docs/agent-workflows/` 或 `.codex/skills/` 维护第二份 skill 源头。
- `.codex/` 和非 skill 的 `.claude/` 内容是本地工具配置 / 状态目录，默认继续
  忽略；除非未来有明确文档例外，否则不提交。
- 如果 Claude Code 需要个人本地安装 skill，应从 `.agents/skills/` 派生 copy
  或 symlink；修改时先改仓库里的项目级 skill，不要反向修改本地副本。

产品方向：早期目标是 CLI-first 跑通完整功能闭环。有开发能力的用户应能
通过 CLI / API 把 WebAgentFlow 接入自己的系统或自建操作台。

深度架构 / 演进：[`docs/architecture.zh.md`](./docs/architecture.zh.md)。

## 迭代文档与实现门禁

以 `docs/iterations/README.md` 作为每轮迭代的文档标准。详细的 package
planning 和 review-depth 规则以 `docs/iterations/AGENTS.md` 及中文镜像
`docs/iterations/AGENTS.zh.md` 为准。

当任务是为代码型或混合型迭代生成开发文档时，必须先按
`docs/iterations/templates/` 生成完整迭代文档包：`README.md`、`intent.md`、
`contract.md`、`technical-design.md`、`test-plan.md`、`plan.md`、`review.md`。
纯文档迭代只有在不准备后续代码实现时，才可以省略 `technical-design.md` 和
`test-plan.md`；但如果改变流程规则、里程碑语义、Agent 边界、证据语义、
迭代模板、概念、状态、字段或产品边界，仍必须包含 `contract.md`。

当任务是代码开发时，必须先读取当前迭代文档，并严格按照 `contract.md`、已审核的
`technical-design.md`、`test-plan.md`、`plan.md` 实现和自测。不得绕过、
重新解释或静默替换这些文档。如果实现过程中发现设计问题，必须先停止实现，
更新对应迭代文档并经过审核，再继续开发。

复杂代码迭代或涉及 live run 的迭代必须包含 `test-plan.md`；没有命令输出、
`run_id`、截图、日志或已记录的产品界面证据时，不得声称完成 E2E、UI smoke、
CLI、`verify-scenario` 或 autonomous-run 测试。

包含多个 planned sub-iterations 的 milestone plan 或 umbrella package plan
必须把每个 planned package 写成准迭代包规格。每个 planned package 必须写清
package name、status、type、goal、why this exists、required reading、
allowed changes、forbidden changes、expected deliverables、expected tests /
verification、compatibility constraints、scope guardrails、exit criteria 和
handoff to next package。只写一行 package summary 不足以指导后续实现。

当 Codex App `/goal` 需要跑完整个 campaign 时，该 campaign 必须在所属迭代包
中提供 Campaign Goal Runner 契约。runner 必须写清 current state 文件、checkpoint 字段、
child package lifecycle、final status vocabulary 和 live-run hard stop。Full
campaign goal 只有在每个 child package 到达已记录 checkpoint 后才可以继续下一包；
遇到 P0 / P1 finding、证据不足、状态冲突、越界文件变更或缺少 live validation
授权时必须立即停止。详细标准放在 `docs/iterations/AGENTS.md` 和
`docs/iterations/AGENTS.zh.md`，不要在根级文档重复大段流程。

## AI 编码 Agent —— 执行边界（硬约束）

WebAgentFlow **本身就是**一个自主 web 操作引擎，内置有项目自己的
**Supervisor Agent**，位于
`apps/api/app/services/learning/autonomous_explorer.py::_run_supervisor`，
观察原子 schema 定义在
`apps/api/app/services/learning/supervisor_observations.py`。

**应用**才是执行者。**用户**是操作者。**AI 编码 Agent**（Claude Code、
Codex 等）主要负责写代码，但当用户明确要求 UI smoke / 浏览器验证时，也
可以作为**外部测试操作员**操作产品自己的 Console UI，并如实汇报产品返回
的结果。AI 不得伪装成 WebAgentFlow 内部角色 Agent，不得编造 Agent 裁决，
也不得绕过产品运行路径直接调用内部服务。

所有当前和未来的 Agent-operated validation 都必须留下可审计的外部操作轨迹。
如果 Codex / Claude / 其他 AI 跑了一次校验，记录里必须说明使用的是哪个
被允许的入口（`cli` 或 `ui`）、执行了什么命令或操作了哪个产品控件、工作
目录或页面、项目 CLI 涉及时的原始 product-client request / response log，
以及产出的 artifact / run id。最新一份已脱敏记录必须保留在稳定的仓库路径，
方便 commit / push 后由 ChatGPT 或其他 Agent 复核。可以保留带时间戳的归档，
但它不能替代稳定的 latest 副本。

AI 可以通过项目提供的 **`verify-scenario` skill** 触发一次运行。通过
skill 调用是可审计的（走 HTTP API、持久化进 `exploration_runs`、输出原
始 Supervisor 裁决 + scorecard），所以验证逻辑依然成立：裁决由项目内
Supervisor Agent 产出，AI 负责中转原样呈现。

当用户明确要求 live UI smoke 时，AI 也可以点击产品 Console 控件，例如
Workbench 的 `Run` 或 Use Cases 的 `Run selected`。这种情况下，
`/exploration/autonomous-runs[/stream]` 调用只允许作为这些 UI 控件触发的
产品侧浏览器流量出现，报告里必须清楚写明。直接 `curl`、fetch、httpx、
内联 service import，或用脚本绕开产品 UI 调 autonomous-run endpoint，
仍然禁止。

文档更新或普通代码修改如果没有明确要求 live run，不要触发
`verify-scenario`。本仓库把每一次 live autonomous run 都当作可审计的产品
证据，不是随手跑的普通测试。

### 禁止做

- 用 curl、fetch、httpx 或任何非产品 UI 的 HTTP 客户端调用
  `POST /exploration/autonomous-runs` 或 `.../stream`。请通过产品 UI 或
  `verify-scenario` skill 触发。
- 把直接 API 调用、一次性脚本、service import 或隐藏 HTTP client 包装成
  "Agent 自主测试"。Agent-operated 测试必须通过被允许的 CLI 或产品 UI 入口，
  并保留 operator action log。
- 导入 `run_autonomous_exploration` 并在进程内直接驱动 Playwright。
- 伪装成 Task Path Planner（legacy: Agent D）、Task Result Reporter
  （legacy: Agent E）、Supervisor Agent 等 WebAgentFlow 内部 Agent，或在
  产品没有实际产出结果时编造内部 Agent 结果。
- 用"通过了"/"跑过了"/"works"之类的总结概括结果，**而不引用**这次运行
  的 `supervisor.verdict` 原值和 5 项 scorecard 得分原值。
- 汇报时省略 `run_id` —— 用户靠 `run_id` 在 WebAgentFlow 控制台里查这次
  运行。CLI **不会**输出前端 URL：它只是后端客户端，不该知道 console
  跑在哪台机器哪个端口。
- 伪造或篡改裁决。skill 退出非 0 就如实报告非 0；退出 0 就报告成功，
  **同时引用 Supervisor 的 confidence + summary 原文**。
- 在循环里反复调 skill 来"平均"或"复核"结果 —— 每次调用都是一次真实
  的 Playwright + LLM 运行。
- 提交或 push 未脱敏、没有 latest 可复核 artifact、或缺少原始 CLI/UI 操作
  记录的 Agent-operated evidence。

### 允许做

- 读任意文件；跑只读诊断（`ruff`、`vue-tsc`、openapi 检查、import 验证等）。
- 跑**不涉及** `autonomous_explorer.run_autonomous_exploration` 的单元 /
  集成测试。
- 按用户要求修改代码。
- **调用 `verify-scenario` skill**，当用户的请求暗示需要一次真实运行时
  （"verify X"、"跑一下 spec Y"、"check workflow Z"）。如实转发 Supervisor
  的裁决 + scorecard + `run_id` 给用户；如果裁决不是 `success`，再给出
  具体的分析 / 下一步建议。
- 当用户明确要求 Agent-operated UI / live UI smoke 时，作为外部测试操作
  员操作产品 Console UI。如果因此触发 `/exploration/autonomous-runs[/stream]`，
  报告时要说明这是产品 UI 触发的流量；能看到 `run_id` / run status 时要
  记录；不得重写或美化产品返回的结果。
- 当请求的校验属于项目 CLI 表面时，可以运行项目提供的 eval CLI，例如
  `pnpm run eval:wagent:*` 或 `wagent` 命令。CLI 必须写入
  `operator_actions`、原始 product-client request 记录、已脱敏 JSON /
  Markdown artifact，以及稳定的 `latest` 副本；否则不能把结果当作可复核的
  Agent-operated evidence。
- 当 skill 和外部 UI 操作都不适合时（服务未启动、缺少凭据、需要人工判断
  等），请用户去 workbench 亲自跑。

### 验证权威顺序

1. **用户** —— 在 `/exploration/autonomous` 或 history 详情页中确认或
   驳回一次运行。
2. **项目内 Supervisor Agent** —— `_run_supervisor` 的 LLM 调用 + 基于规则
   的 `page_verification` 评分卡。

AI 编码 Agent 是**外部测试操作员 / 中转**，不是产品内部验证者。它不在
这个链上。它的职责是在用户要求时操作被允许的产品表面，并把 (1) + (2)
原样转给用户。

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

# 一键启动仓库内服务（console + api + worker）
pnpm run dev
pnpm run dev:lan                # 绑到 0.0.0.0，局域网可访问

# 单独起各服务
pnpm run dev:console            # Vite，端口 5174
pnpm run dev:api                # Uvicorn，端口 8001
pnpm run dev:worker             # Python 文件改动自动 reload（走 watchfiles）

# 外部 Fixture-Site（本 workspace 外）
cd /Users/leechen/projects/WebAgentFlow-Fixture-Site
pnpm dev
export WAF_FIXTURE_SITE_URL=http://127.0.0.1:5175
export WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs
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

**当前焦点 —— 自主探索 + M10 路径资产：**

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
- `apps/api/app/models/learned_path.py` —— M10.1 LearnedPath ORM model。
- `apps/api/app/repos/learned_paths_repo.py` —— LearnedPath 持久化、catalog、
  trust 和 lookup 数据访问。
- `apps/api/app/services/learning/page_signature.py` —— LearnedPath 身份计算
  helper（`path_template`、`query_signature`、`dom_fingerprint`）。
- `apps/api/app/routers/exploration.py` ——
  `/exploration/autonomous-runs[/stream]`、
  `/exploration/specs[/{id}]`（workbench 拉 spec 做预填用）、
  `/exploration/autonomous-runs[/{run_id}]`（落库后的 run 历史），以及
  LearnedPath catalog routes。
- `apps/api/app/services/learning/page_verification.py` —— 从配置的
  `WAF_PAGE_SPEC_ROOT` 加载 authored baselines。
- `apps/console/src/pages/AutonomousWorkbenchPage.vue` —— 用户驱动的工作台。
- `apps/console/src/pages/LearnedPathCatalogPage.vue` —— M10.1.5 LearnedPath
  catalog UI。
- `apps/console/src/api/autonomousStream.ts` —— SSE 客户端（POST + fetch 流）。

**稳定基础：**

- `apps/api/app/services/html_ast_parser.py` —— HTML → Full AST（`lxml`）。
- `apps/api/app/services/execution/execution_runtime.py` ——
  autonomous_explorer 用的 Playwright chromium 生命周期封装。
- `apps/api/app/schemas/` —— Pydantic 契约（page_analysis、
  page_verification、llm、ast、common）。

**当前重点 —— M11 runtime conversation 与 task planning foundation：**

- `apps/api/app/schemas/conversation.py` —— M11.0 conversation 枚举、领域
  contract 和 API request / response schema。
- `apps/api/app/models/conversation.py` —— DB-backed conversation session /
  message / event ORM models。
- `apps/api/app/repos/conversation_repo.py` —— conversation session / message /
  event repository。
- `apps/api/app/services/conversation/commands.py` —— 纯 slash-command parser
  contract。
- `apps/api/app/services/conversation/state.py` —— 纯 conversation state
  transition contract。
- `apps/api/app/routers/conversation.py` —— Conversation API endpoints。
- `apps/api/app/services/conversation/orchestrator.py` —— M11.0.5
  Conversation Orchestrator / Dispatcher service skeleton。
- `apps/cli/wagent/conversation.py` —— `wagent conversation` runtime
  conversation CLI。
- `apps/cli/tests/test_conversation.py` —— CLI regression tests。
- `apps/api/app/schemas/task_planning.py` —— 计划中的 M11.1 task-to-path
  planning domain contract（`11.1.1`，已交付）。

**规划中 / 部分已实现的服务区域：**

- Conversation domain / store / API / CLI / Orchestrator service skeleton、
  explicit replay hook、public dispatch endpoint、CLI dispatch 接入和
  conversation runtime E2E 已通过 M11.0.7 实现。
- M11.1 Task Path Planner / 任务路径规划器和 Task Result Reporter / 任务结果汇报器
  （legacy: Agent D/E）、retrieval、confirmation、task execution 和
  evidence-bound reporting 已按 scoped happy path 实现。Broad-domain slot
  binding、automatic recovery 和 teaching 仍是后续工作。
- M11.3.7 first-wave user-facing WAgent behavior eval 是 `pass`；full
  learn-then-execute 和 page-wide automatic capability discovery 仍是后续工作。
- L2 teaching support、highlight targets 和 user action recording。
- Artifact lifecycle handling。
- Failure evidence / negative knowledge。

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
- 当前核心表至少包括 `exploration_runs` 和 `learned_paths`。
- `exploration_runs` 存 autonomous run history。
- `learned_paths` 是 M10.1 路径资产表，用于可复用 learned actions 和 trust
  state。
- `learned_paths` 保持路径资产表。除非产品模型先明确改变，否则不要新增
  ownership、scope 或路线图外字段。
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
  实际工作）、产品内部功能角色（A-H 为 legacy alias）、跨阶段不变量。
  **先看这份**。
- [`docs/architecture.zh.md`](./docs/architecture.zh.md) —— AST 双轨、
  服务子包结构、iframe 处理。
- [`docs/scope-boundaries.zh.md`](./docs/scope-boundaries.zh.md) —— 当前交付里程碑
  **明确不做**的内容。
- [`docs/roadmap.zh.md`](./docs/roadmap.zh.md) —— v0.1 阶段里程碑。
- [`docs/dev-setup.zh.md`](./docs/dev-setup.zh.md) —— 完整的开发环境
  搭建步骤（比上面的"常用命令"更详细，面向新 contributor）。
- [`docs/iterations/README.md`](./docs/iterations/README.md) ——
  **迭代文档规范**（按里程碑组织目录，每次迭代留 `intent.md` /
  `contract.md` / `technical-design.md` / `test-plan.md` / `plan.md` /
  `review.md`）。
  开始一轮非平凡工作前先写 `intent.md` 和必要设计文档；代码型迭代必须在
  `technical-design.md` 审核后才能进入实现。
- [`CLAUDE.md`](./CLAUDE.md) —— 英文原版。
- [`AGENTS.md`](./AGENTS.md) —— 给 Codex 等 AI 编码 Agent 的版本。
