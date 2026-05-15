# 测试计划（Test Plan）

状态：proposed

## 适用条件

满足任意一条就必须维护本文件：

- 涉及前后端协同。
- 涉及 Agent / Reporter / recovery / abort / replay。
- 涉及 E2E。
- 涉及 `verify-scenario`、autonomous run、Codex / AI 作为外部测试操作员。
- 测试矩阵超过 5 个 case。
- 涉及人工测试、UI smoke、product-driven browser execution。
- 需要区分 unit / integration / E2E / live product evidence。

## 测试范围（Test Scope）

- Unit：<范围，或 `N/A` + 原因>
- Integration：<范围，或 `N/A` + 原因>
- API：<范围，或 `N/A` + 原因>
- Console UI：<范围，或 `N/A` + 原因>
- E2E：<范围，或 `N/A` + 原因>
- Agent / Reporter / Recovery：<范围，或 `N/A` + 原因>
- Codex / AI External Operator：<范围，或 `N/A` + 原因>
- Live autonomous run：<范围，或 `N/A` + 原因>

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| <unit / integration / API / UI / E2E / live> | <scenario> | <command or product surface> | <expected evidence> | Yes / No | <notes> |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 如果没有真实打开浏览器或产品 UI，不得声称已经完成 UI smoke / E2E。
- 如果只运行了单元测试、API 测试或静态检查，必须明确写成“未进行浏览器验证”。
- 使用浏览器验证时，必须记录入口 URL / 页面、操作路径、截图或可复查的观察结果。
- 如果浏览器验证由用户执行，必须标记为 user acceptance，不得写成 Codex 已执行。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 只能作为外部测试操作员记录自己真实执行过的动作。不得编造内部 Agent 结论，
不得把代码审查、静态推理或未执行的命令写成测试通过。

每次声称“已测试”时必须能回答：

- 实际打开了什么页面或调用了什么 CLI / command？
- 命令或页面操作的原始结果是什么？
- 是否有 run_id、截图、日志、exit code、pass / fail count 或可复查输出？
- 如果没有这些证据，结论必须写成 `not run` / `unverified`。

## Live Run 边界（Live Run Boundary）

除非用户明确要求 live run，不得运行 `verify-scenario`、autonomous run 或 product-driven
browser execution。

如果用户明确要求 live run，必须记录：

- invocation surface；
- run_id；
- pass_gate.status；
- supervisor verdict；
- scorecard；
- 是 product UI traffic 还是 skill invocation；
- 原始输出或可复查路径。

`pass_gate.status` 是权威结果；`unverified` 不是通过。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| <test item> | <why not run> | <risk / follow-up> |
