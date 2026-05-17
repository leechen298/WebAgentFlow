# 契约（Contract）

状态：accepted（implementation review passed, product-level CLI smoke passed）

## 概念 / 边界契约

### validation-site

`apps/validation-site` 是工程验证靶场。它继续用于 deterministic regression：

- specs / assertions
- fixed `spec_id`
- fixed `scenario`
- pass_gate / scorecard
- `verify-scenario`
- M10 / M11 底层能力 smoke
- runtime observation fixtures

本轮不得删除、弱化、迁移或重写 validation-site。

### product-test-site

`apps/product-test-site` 是产品级聊天验收站。它用于验证普通用户通过
`wagent chat` 教 WebAgentFlow 操作网页，而不是验证工程 oracle。

推荐包名和端口：

```text
package: @web-agent-flow/product-test-site
dev port: 5176
base URL: http://localhost:5176
```

product-test-site 必须接入项目一键启动：

```bash
pnpm run dev
```

一键启动应同时启动 console、api、worker、validation-site 和 product-test-site。
`pnpm --filter @web-agent-flow/product-test-site dev` 可以保留为单独调试入口，但不能替代
根目录 `pnpm run dev` 的普通用户启动路径。

### Product-level chat learning

`product-level chat learning` 指产品级 `wagent chat` 学习路径：

```text
用户自然语言提供 URL 和必要输入
-> WebAgentFlow 观察页面
-> 学习并沉淀 LearnedPath
```

该路径不得依赖 validation-site oracle：

- 不读取 `apps/validation-site/specs/*.assertions.json`。
- 不传 `spec_id / scenario`。
- 不从 assertions 取 inputs。
- 不硬编码 `/login` 或 `valid_credentials`。
- 不硬编码目标测试站点、host、path 或 route。学习目标必须来自用户输入的 URL。

### Product-level target site boundary

产品级 `wagent chat` 必须把“要学习 / 要操作哪个站点”作为用户输入的一部分处理。

学习时：

- 用户必须提供目标 URL。
- 系统只能打开并学习用户输入的 URL。
- 不得在用户未提供 URL 时默认跳到 validation-site、product-test-site 或任何固定站点。
- 不得因为 path 不是 `/login` 就拒绝产品级学习；产品级路径不应保留 `/login` 特化。

执行时：

- 系统只能执行当前 conversation session 中已经学习过的 target URL / target site 上的操作。
- 如果用户执行指令里包含 URL，必须优先按该 URL 匹配已学操作。
- 如果用户执行指令没有包含 URL，只能在当前 session 内存在单一清晰匹配时直接执行。
- 如果目标站点 / 页面没有学过，必须返回普通用户可理解的反馈，例如：

```text
还没学过这个站点或页面，需要先学习。
```

- 不得因为存在 validation-site 的历史 LearnedPath，就跨站点执行。
- 不得把同一 alias（例如“登录”）在不同 target URL 上混成同一个 learned action。

## 状态 / 结果契约

本轮不新增 conversation status，不改变 replay status semantics。

acceptance 状态依赖以下红线：

- 如果产品级学习仍通过 `spec_id=login / scenario=valid_credentials` 完成，不得 accepted。
- 如果用户没有在聊天中提供必要输入，而系统从 validation spec 自动拿到输入，不得 accepted。
- 如果修改或删除 `login.assertions.json` 会影响 product-test-site 学习，不得 accepted。
- 如果根目录 `pnpm run dev` 不启动 product-test-site，不得 accepted。
- 如果产品级学习仍限制为 `/login`，或仍返回“当前只支持学习登录页”，不得 accepted。
- 如果执行未学习过的 target site 时跨站点命中历史 LearnedPath，不得 accepted。

## Schema / API 契约

已完成的文档阶段不修改 schema / API。

实现阶段允许：

- 新增 product-test-site 前端 package。
- 调整 `wagent chat` 产品级学习入口，使其支持从用户自然语言解析 target URL 和必要输入。
- 增加 product-level learning mode 或等价内部分支，用来和 validation-backed learning 区分。
- 调整 session `learned_actions` 匹配策略，使 learned action 至少按 alias + target URL / site scope
  区分。

实现阶段不得：

- 改变 API response envelope。
- 为 product-test-site 引入 validation `spec_id / scenario` requirement。
- 把 product-test-site 注册为 validation specs 的消费者。
- 在 product-level chat learning 中保留 `/login` only gate。
- 对未学习过的 target URL 使用其他站点的 LearnedPath 自动执行。

## Evidence / Observation 契约

产品级 chat 验收 evidence 来自：

- CLI 原始输出。
- 用户实际看到的 product-test-site 页面和浏览器行为。
- LearnedPath 是否真实沉淀。
- 后续可选的 chat history / debug surface。

validation evidence 继续来自：

- pass_gate / scorecard。
- `verify-scenario`。
- validation-site assertions。

这两类 evidence 不得混写。没有真实 product-test-site smoke 时，不得声称产品级 chat
验收通过。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：仍然是用户通过 WebAgentFlow 操作网页，不新增 internal Agent role。
- Scope boundary 对齐：只拆分测试站和产品级 learning 输入边界，不进入 M12 recovery。
- Roadmap / milestone 对齐：属于 M11.3 interactive chat 的产品级验收隔离增强。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- `validation-site` 原有 routes、specs、fixtures、verify / smoke 能力必须保留。
- 根目录 `pnpm run dev` 必须继续保留现有 console / api / worker / validation-site，并新增
  product-test-site；不能为了新增产品验收站移除原有一键启动成员。
- `11.2.4.2-single-page-basic-business-pages` 继续属于 M11.2，不迁移。
- `11.3.2-chat-history-debug-console` 继续使用已有编号和目录。
- `wagent chat` CLI 入口文档不得回退到只依赖 `source .venv/bin/activate`。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：文档阶段不变。
- Database schema：文档阶段不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不实现真实业务系统接入。
- 不实现完整订单查询执行闭环。
- 不做 Chat History 看板实现。
- 不做 Visible browser 实现。
- 不做 validation-site 重构。

## 未决问题

- 无。新站点命名为 `apps/product-test-site`，端口 `5176`。
