# 测试计划（Test Plan）

状态：accepted（implementation review passed, product-level CLI smoke passed）

## 适用条件

本轮满足以下触发条件，因此必须维护 `test-plan.md`：

- 涉及新前端测试站点。
- 涉及产品级人工测试。
- 涉及 `wagent chat` product-driven browser execution。
- 需要明确区分 validation oracle 和 product-level evidence。

## 测试范围（Test Scope）

- Unit：实现阶段覆盖 parser / learning mode 分支。
- Integration：实现阶段覆盖 `wagent chat` product-level learning 不传 `spec_id / scenario`。
- API：实现阶段覆盖 conversation dispatch product-level learning path。
- Console UI：N/A，本包不做 Console。
- E2E：已通过 `wagent chat` product-level CLI smoke。
- Agent / Reporter / Recovery：N/A，不改 internal Agent / Reporter / M12。
- Codex / AI External Operator：只能记录真实 CLI / browser 结果。
- Live autonomous run：chat learning smoke 会触发产品运行，必须记录真实 evidence。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Docs | DOC-1 文档包完整 | `find docs/iterations/m11/11.3.3-product-chat-test-site-separation -maxdepth 1 -type f` | 七件套存在 | Yes | 文档阶段 |
| Docs | DOC-2 CLI 入口不回退 | `docs/user-guide/wagent-chat.md` | 主入口仍是 `.venv/bin/wagent chat` | Yes | 不只提示 source |
| Docs | DOC-3 whitespace | `git diff --check` | clean | Yes | 文档阶段唯一必跑命令 |
| Product site | SITE-1 build | `pnpm --filter @web-agent-flow/product-test-site build` | build pass | Yes | 实现阶段已跑 |
| Product site | SITE-2 one-click dev | `pnpm run dev` | 同时启动 console / api / worker / validation-site / product-test-site | Yes | product-test-site 必须包含在一键启动里 |
| Product site | SITE-3 login page smoke | `http://localhost:5176/workspace-login` | 页面显示工作台入口 / 操作员账号 / 访问口令 / 进入工作台 | Implementation | 实现阶段 |
| Product site | SITE-4 login behavior | browser manual smoke | demo / 123456 进入工作台首页；错误输入显示错误 | Implementation | 实现阶段 |
| Chat | CHAT-1 product learning no spec | `wagent chat` | learning request 不读取 validation specs，不传 `spec_id / scenario` | Yes | accepted blocker 已通过 |
| Chat | CHAT-2 user URL only | `wagent chat` | 学习时只打开用户输入 URL，不保留 `/login` only gate | Yes | accepted blocker 已通过 |
| Chat | CHAT-3 product learning success | `wagent chat` | 学习 product-test-site 后沉淀 LearnedPath，metadata 保留 target_url / site scope | Yes | LearnedPath id 见 review |
| Chat | CHAT-4 execute learned action | `wagent chat` | “帮我进入工作台”直接执行，返回成功结果 | Yes | 不要求确认 |
| Chat | CHAT-5 unlearned target URL fallback | `wagent chat` | 指定未学习过的 URL 时返回“还没学过这个站点或页面，需要先学习。” | Yes | 不跨站点命中 |
| Chat | CHAT-6 same alias different URL | `wagent chat` | 同 alias 不同 URL 不互相覆盖；无 URL 时不能跨站点猜测 | Yes | target scope |
| Chat | CHAT-7 no path fallback | `wagent chat` | 未学过任务返回“还没学过这个操作，需要先学习。” | Implementation | 用户文案 |
| Regression | REG-1 validation build | `pnpm --filter @web-agent-flow/validation-site build` | validation-site 不受影响 | Yes | 已跑 |
| Regression | REG-2 assertions independence | modify/delete `login.assertions.json` in controlled test | product-test-site learning 不受影响 | Implementation | 不提交破坏性修改 |

## 人工验收样例（Manual Acceptance Sample）

启动服务：

```bash
pnpm run dev
.venv/bin/wagent chat
```

`pnpm run dev` 必须同时启动 product-test-site。人工验收前应能访问：

```text
http://localhost:5176/workspace-login
```

输入：

```text
学习一下这个工作台登录页怎么进入，地址是 http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456
```

期望：

```text
WAgent > 我会打开浏览器学习：进入工作台。
WAgent > 学习完成：我学会了工作台登录操作。之后你可以说“帮我进入工作台”。
```

继续输入：

```text
帮我进入工作台
```

期望：

```text
WAgent > 我会打开浏览器执行：输入操作员账号和访问口令，并点击“进入工作台”按钮。
WAgent > 进入工作台完成。
```

未知任务：

```text
帮我导出订单
```

期望：

```text
WAgent > 还没学过这个操作，需要先学习。
```

未学习过的站点或页面：

```text
帮我在 http://localhost:5176/orders 导出订单
```

期望：

```text
WAgent > 还没学过这个站点或页面，需要先学习。
```

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 没有真实打开 product-test-site，不得声称产品级 smoke 通过。
- 如果只打开 validation-site，不得声称 product-test-site 验收通过。
- 如果 `pnpm run dev` 没有启动 product-test-site，不得声称 M11.3.3 人工验收通过。
- 如果学习路径仍使用 `spec_id / scenario`，不得 accepted。
- 如果产品级学习仍限制为 `/login` 或固定站点，不得 accepted。
- 如果未学习过的 target URL 跨站点命中历史 LearnedPath，不得 accepted。
- 如果没有 LearnedPath id、CLI 输出或可复查 history，不得声称学习沉淀已验证。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 只能记录自己真实执行过的 CLI 和浏览器结果。不得编造内部 Agent verdict，
不得把 validation-site pass_gate 当成 product-test-site 产品验收结果。

## Live Run 边界（Live Run Boundary）

文档阶段不触发 live run。

实现完成后，如果通过 `wagent chat` 学习 product-test-site 页面，必须记录：

- CLI invocation。
- product-test-site URL。
- 用户输入的 target URL 和实际打开 URL 是否一致。
- 浏览器可见行为。
- LearnedPath id。
- learned action 中记录的 target_url / site scope。
- conversation session id 或 history URL（如果 11.3.2 已实现）。
- 未使用 validation spec 的证据。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| Full API suite | 本轮按 scoped risk 运行 targeted tests | 发布级大回归可补 |
| Console UI smoke | M11.3.3 不改 Console UI | 由 11.3.2 history/debug console 验收覆盖 |
