# <迭代标题>

状态：proposed
里程碑：M<N>
类型：docs | code | mixed

## 迭代类型

- [ ] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - 概念、状态、schema、evidence、边界契约。
- `technical-design.md` - 非平凡代码型 / 混合型迭代必填，定义实现设计。
- `test-plan.md` - 强触发时必填，定义当前迭代的详细测试方案。
- `plan.md` - 实施步骤和验证命令。
- `review.md` - 评审记录、用户反馈、最终差异、实际验证证据。
- `GOAL_RUNNER.md` - campaign / umbrella `/goal` 自动路由契约。
- `CURRENT_STATE.md` - campaign / umbrella 当前 checkpoint 和下一步路由快照。

## /plan 风格文档生成入口

生成或修改迭代文档前，先完成这些决策；无法判断时停为 `NEEDS_USER_INPUT`：

- [ ] 目标 package path 和 package type 已确定。
- [ ] parent / child 关系和下一步 route 已确定，或明确 N/A。
- [ ] 必需文件集合已确定。
- [ ] source-of-truth 输入已阅读并记录。
- [ ] contract / concept / status / evidence 变化已识别。
- [ ] design-review gate 和 `test-plan.md` 触发状态已识别。
- [ ] code / mixed package 的 implementation authorization boundary 已写明。
- [ ] umbrella / campaign package 已判断是否需要 `GOAL_RUNNER.md` 和 `CURRENT_STATE.md`。
- [ ] stop conditions 和 handoff / checkpoint 已写明。

## 文档型迭代门禁

必需：

- [ ] `intent.md` 已存在。
- [ ] 如果改变概念、状态、schema、evidence、边界、流程规则、里程碑语义、Agent 边界或迭代模板，`contract.md` 已存在。
- [ ] 如果没有契约变化，`contract.md` 明确写出 `N/A` 和原因。
- [ ] `plan.md` 已存在。
- [ ] `review.md` 已存在。

## 代码型迭代门禁

- [ ] `intent.md` 已存在。
- [ ] `contract.md` 已存在。
- [ ] `technical-design.md` 已存在。
- [ ] 技术设计在实现前已经审核。
- [ ] 技术设计包含明确的 contract alignment。
- [ ] 如果触发 `test-plan.md` 条件，`test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [ ] `plan.md` 与已审核的 contract / technical design 一致。
- [ ] `review.md` 在收尾前记录验证证据。

## test-plan.md 触发条件

满足任意一条就必须创建 `test-plan.md`：

- 涉及前后端协同。
- 涉及 Agent / Reporter / recovery / abort / replay。
- 涉及 E2E。
- 涉及 `verify-scenario`、autonomous run、Codex / AI 作为外部测试操作员。
- 测试矩阵超过 5 个 case。
- 涉及人工测试、UI smoke、product-driven browser execution。
- 需要区分 unit / integration / E2E / live product evidence。

没有真实浏览器、CLI、`run_id`、截图、日志、exit code 或可复查输出时，不得声称已完成
E2E、UI smoke、CLI、`verify-scenario` 或 autonomous-run 测试；必须写成 `not run` /
`unverified`。

## 当前状态

<给下一位 Agent 的短交接说明。>

## Campaign / Goal Runner（如适用）

当本迭代是 umbrella package 或需要 Codex App `/goal` 连续跑多个 child package 时：

- [ ] `GOAL_RUNNER.md` 已存在，并定义 execution modes、child lifecycle、hard stops 和 final status vocabulary。
- [ ] `CURRENT_STATE.md` 已存在，并定义 active child package、route status、next action 和 package queue。
- [ ] 每个 child package closeout 后都会更新 parent checkpoint。
