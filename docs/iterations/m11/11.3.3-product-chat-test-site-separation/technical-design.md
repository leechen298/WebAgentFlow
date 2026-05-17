# 技术设计（Technical Design）

状态：accepted（implementation review passed, product-level CLI smoke passed）

## 当前状态（Current State）

当前仓库已有：

- `apps/validation-site`：工程验证靶场，包含 `/login`、`/users`、runtime observation fixtures
  和 `specs/*.assertions.json`。
- `wagent chat`：interactive chat 产品入口，已经能学习 `/login` 并执行已学操作。
- 早期 M11.3 `/login` happy path：仍可能通过 `spec_id=login`、
  `scenario=valid_credentials` 和 validation assertions 完成学习验证。
- `11.3.2-chat-history-debug-console`：已占用 11.3.2 编号，本包不能覆盖。
- `11.2.4.2-single-page-basic-business-pages`：属于 M11.2 validation fixture 体系，
  不迁移到 11.3。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| product-test-site 独立 | 新增 `apps/product-test-site`，不放在 validation-site specs 体系里 | `test-plan.md` SITE-1 / SITE-2 | 后续代码阶段 |
| 产品级 chat learning 不读 assertions | learning mode 不传 `spec_id / scenario`，inputs 来自用户 utterance | `test-plan.md` CHAT-1 / CHAT-2 | acceptance blocker |
| validation-site 保留 | 不删除 specs / routes / verify-scenario | `test-plan.md` REG-1 | 工程回归继续可用 |
| 11.3.2 不动 | 新包编号 11.3.3，仅索引追加 | 文档 review | 避免编号冲突 |
| CLI 入口修复不回退 | 用户指南继续以 `.venv/bin/wagent chat` 为主入口 | `test-plan.md` DOC-2 | 不只提示 source |

## 实现方案（Proposed Implementation）

### Product Test Site

实现阶段新增：

```text
apps/product-test-site/
  package.json
  index.html
  src/
    main.ts
    router/
    pages/
      WorkspaceLoginPage.vue
      WorkspaceHomePage.vue
      OrdersPage.vue
```

推荐 dev script：

```text
vite --port 5176 --strictPort
```

第一阶段只实现产品级登录闭环；订单查询页可先作为后续扩展页面规划。

### Page Semantics

产品级登录页不复制 validation `/login`：

```text
route: /workspace-login
title: 工作台入口
field: 操作员账号
field: 访问口令
button: 进入工作台
success: 工作台首页 / 已进入工作台
```

登录数据可以 deterministic，但不能通过 validation spec 暴露给 chat learning：

```text
操作员账号: demo
访问口令: 123456
```

用户必须在聊天里提供这些输入。

### Monorepo Integration

实现阶段应：

- 将 `@web-agent-flow/product-test-site` 加入 pnpm workspace。
- 提供独立 `pnpm --filter @web-agent-flow/product-test-site dev`。
- 在根 `pnpm run dev` 中增加 product-test-site，作为普通用户和人工验收的一键启动路径。
- 固定端口 `5176`，不得和 console `5174`、validation-site `5175`、api `8001` 冲突。

根目录一键启动的目标进程应变为：

```text
console      -> http://localhost:5174
api          -> http://localhost:8001
worker       -> async worker
validation   -> http://localhost:5175
product      -> http://localhost:5176
```

独立 filter dev 只作为开发调试入口，不作为 M11.3.3 人工验收主路径。

### Chat Learning Mode

实现阶段需要引入 product-level learning mode 或等价分支：

```text
validation-backed learning:
  spec_id/scenario present
  inputs from assertions
  pass_gate / scorecard as oracle

product-level learning:
  spec_id = None
  scenario = None
  target_url = parsed from user utterance
  inputs from user utterance
  no validation assertions
  no fixed /login gate
```

第一版 deterministic parser 可支持：

```text
地址是 <url>
操作员账号是 <value>
访问口令是 <value>
```

学习请求必须以用户输入的 URL 为唯一目标页面来源。实现阶段需要移除当前
`/login` only gate，不能再对 product-level learning 返回“当前只支持学习登录页”。

不引入复杂 LLM 意图理解。

### Target URL / Site Scope Matching

实现阶段需要让当前 session 的 `learned_actions` 具备明确 target scope。
最小结构继续复用 metadata，但每条 action 必须包含：

```json
{
  "alias": "进入工作台",
  "utterances": ["帮我进入工作台"],
  "learned_path_id": "...",
  "target_url": "http://localhost:5176/workspace-login",
  "site_origin": "http://localhost:5176",
  "page_template": "/workspace-login"
}
```

匹配策略：

- learn：只打开用户输入的 `target_url`。
- execute with URL：如果用户执行指令包含 URL，必须按该 URL 优先匹配当前 session 已学 action。
- execute without URL：只能在当前 session 存在单一 alias / utterance match 且 target scope
  清晰时自动执行。
- no learned target：如果目标 URL / site 没有学过，返回
  `还没学过这个站点或页面，需要先学习。`。
- same alias across sites：同一 alias 在不同 target URL 上不能互相覆盖；需要按
  alias + target URL / site scope 区分。

第一版不做全局 LearnedPath fallback，避免历史 validation-site path 污染 product-level smoke。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | Implementation | 可能调整 conversation learning handler 分支 | 实现阶段按需调整 |
| API response schema | No | 不改变 envelope | N/A |
| Database schema / migration | No | 继续用 LearnedPath / conversation 现有表 | N/A |
| CLI | Implementation | product-level utterance parsing / smoke / target URL feedback | 不回退 `.venv/bin/wagent` 入口 |
| Console UI | No | 本轮不做 history/debug console | 11.3.2 owns |
| Conversation events | Implementation | 可记录 product-level learning mode | 不发明 Agent verdict |
| Replay execution | No | 已学 path 的 replay 继续复用现有能力 | N/A |
| Reporter | No | 不接 Task Result Reporter | N/A |
| Worker / async jobs | No | 同步 dev site | N/A |
| Tests / fixtures | Yes | 新 product-test-site 页面和 smoke | validation-site 保留 |
| Docs | Yes | 本轮生成文档包和索引 | 当前交付 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

文档阶段不新增 schema。

实现阶段优先复用现有 LearnedPath / conversation metadata。若需要标记 learning source，
优先使用 metadata，不新增 migration。

## 服务 / 模块设计（Service / Module Design）

实现阶段建议把学习入口拆成两个清晰路径：

- validation-backed：继续服务 `verify-scenario`、validation smoke 和工程回归。
- product-level：服务 `wagent chat` 普通用户路径，输入来自 utterance。

不要让 product-level handler 调用 validation spec loader。
不要让 product-level handler 检查 path 必须等于 `/login`。
不要让 execute path 在未学习目标 URL 时 fallback 到其他站点的 LearnedPath。

## 数据流（Data Flow）

产品级学习目标数据流：

```text
wagent chat utterance
-> parse target_url + credential-like inputs
-> open product-test-site URL
-> autonomous learning with user-provided inputs
-> persist LearnedPath
-> session learned_actions with target_url / site_origin
-> user says "帮我进入工作台"
-> match current-session learned action by alias + target scope
-> replay learned action on learned target_url
```

## 状态推导（Status / State Derivation）

本轮不改变 conversation status。后续实现仍应保持 interactive chat happy path：

```text
learn_page -> task_intake
execute_task -> task_intake
no path -> task_intake
```

## 兼容性（Compatibility）

- validation-site regression 不受 product-test-site 影响。
- `pnpm run dev` 一键启动后 product-test-site 可访问。
- `wagent verify` 继续使用 validation specs。
- `wagent chat` 主入口继续使用 `.venv/bin/wagent chat`。
- 11.3.2 history/debug console 可并行开发；它读取 conversation 历史，不依赖本包页面实现。

## 失败 / 边界情况（Failure / Edge Cases）

- 用户未提供必要输入：产品级 learning 不得回退去读 validation spec；应返回可理解的缺少输入提示或学习失败。
- 用户未提供学习 URL：不默认跳到任何固定站点，提示需要提供页面地址。
- product-test-site 未启动：CLI/API 返回目标页面不可访问的普通用户文案。
- product-test-site 登录失败：不标记学习完成，不沉淀 LearnedPath。
- validation assertions 被修改：不应影响 product-test-site 学习路径。
- 用户要求操作未学习过的 URL / site：返回 `还没学过这个站点或页面，需要先学习。`。
- 同一 alias 在多个 target URL 上都存在：没有 URL 时不应跨站点猜测，需返回需要更明确目标的用户级反馈。
- 用户执行已学 alias 但指定另一个 URL：不得用已学 URL 的 path 去操作指定 URL，除非该 URL 已在当前 session 学过。

## 非目标（Non-goals）

- 不做真实账号体系。
- 不做复杂订单查询闭环。
- 不做用户接管、retry、recovery、abort。
- 不做 LLM 复杂 slot binding。
- 不做 Chat History 看板。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Docs | 文档包完整、索引一致、CLI 入口不回退 | `test-plan.md` DOC |
| Product site build | product-test-site 可构建 | `test-plan.md` SITE |
| Product page smoke | `/workspace-login` 页面可手动操作 | `test-plan.md` SITE |
| Chat product smoke | 不读 validation specs，也只学习 / 执行用户指定或已学习的目标站点 | `test-plan.md` CHAT |
| Validation regression | validation-site build 和 verify/smoke 能力保留 | `test-plan.md` REG |

## 验证命令入口（Validation Commands）

文档阶段：

```bash
git diff --check
```

实现阶段：

```bash
pnpm --filter @web-agent-flow/product-test-site build
pnpm --filter @web-agent-flow/validation-site build
pnpm run dev
```
