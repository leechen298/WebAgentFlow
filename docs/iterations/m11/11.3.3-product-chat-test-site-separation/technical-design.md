# 技术设计（Technical Design）

状态：proposed

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

后续实现阶段新增：

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

后续实现阶段应：

- 将 `@web-agent-flow/product-test-site` 加入 pnpm workspace。
- 提供独立 `pnpm --filter @web-agent-flow/product-test-site dev`。
- 在根 `pnpm run dev` 中增加 product-test-site，或明确提供单独启动命令。
- 固定端口 `5176`，不得和 console `5174`、validation-site `5175`、api `8001` 冲突。

### Chat Learning Mode

后续实现阶段需要引入 product-level learning mode 或等价分支：

```text
validation-backed learning:
  spec_id/scenario present
  inputs from assertions
  pass_gate / scorecard as oracle

product-level learning:
  spec_id = None
  scenario = None
  inputs from user utterance
  no validation assertions
```

第一版 deterministic parser 可支持：

```text
地址是 <url>
操作员账号是 <value>
访问口令是 <value>
```

不引入复杂 LLM 意图理解。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
---|---|---|---|
| API routes | Future | 可能调整 conversation learning handler 分支 | 文档阶段不改 |
| API response schema | No | 不改变 envelope | N/A |
| Database schema / migration | No | 继续用 LearnedPath / conversation 现有表 | N/A |
| CLI | Future | product-level utterance parsing / smoke | 不回退 `.venv/bin/wagent` 入口 |
| Console UI | No | 本轮不做 history/debug console | 11.3.2 owns |
| Conversation events | Future | 可记录 product-level learning mode | 不发明 Agent verdict |
| Replay execution | No | 已学 path 的 replay 继续复用现有能力 | N/A |
| Reporter | No | 不接 Task Result Reporter | N/A |
| Worker / async jobs | No | 同步 dev site | N/A |
| Tests / fixtures | Yes | 新 product-test-site 页面和 smoke | validation-site 保留 |
| Docs | Yes | 本轮生成文档包和索引 | 当前交付 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

文档阶段不新增 schema。

后续实现阶段优先复用现有 LearnedPath / conversation metadata。若需要标记 learning source，
优先使用 metadata，不新增 migration。

## 服务 / 模块设计（Service / Module Design）

后续实现阶段建议把学习入口拆成两个清晰路径：

- validation-backed：继续服务 `verify-scenario`、validation smoke 和工程回归。
- product-level：服务 `wagent chat` 普通用户路径，输入来自 utterance。

不要让 product-level handler 调用 validation spec loader。

## 数据流（Data Flow）

产品级学习目标数据流：

```text
wagent chat utterance
-> parse target_url + credential-like inputs
-> open product-test-site URL
-> autonomous learning with user-provided inputs
-> persist LearnedPath
-> session learned_actions
-> user says "帮我进入工作台"
-> replay learned action
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
- `wagent verify` 继续使用 validation specs。
- `wagent chat` 主入口继续使用 `.venv/bin/wagent chat`。
- 11.3.2 history/debug console 可并行开发；它读取 conversation 历史，不依赖本包页面实现。

## 失败 / 边界情况（Failure / Edge Cases）

- 用户未提供必要输入：产品级 learning 不得回退去读 validation spec；应返回可理解的缺少输入提示或学习失败。
- product-test-site 未启动：CLI/API 返回目标页面不可访问的普通用户文案。
- product-test-site 登录失败：不标记学习完成，不沉淀 LearnedPath。
- validation assertions 被修改：不应影响 product-test-site 学习路径。

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
| Chat product smoke | 不读 validation specs 也能学习 / 执行 | `test-plan.md` CHAT |
| Validation regression | validation-site build 和 verify/smoke 能力保留 | `test-plan.md` REG |

## 验证命令入口（Validation Commands）

文档阶段：

```bash
git diff --check
```

后续实现阶段：

```bash
pnpm --filter @web-agent-flow/product-test-site build
pnpm --filter @web-agent-flow/validation-site build
```
