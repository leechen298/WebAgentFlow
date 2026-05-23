# 11.3.6.1 · WAgent Runtime Eval Runner Core

状态：implemented_and_live_eval_passed（final closeout rerun pass）
里程碑：M11
类型：code
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：

- [`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
- [`11.3.5.6-wagent-chat-items-closed-loop-evaluation`](../11.3.5.6-wagent-chat-items-closed-loop-evaluation/)
- [`11.3.5.7-pending-choice-active-task-ledger`](../11.3.5.7-pending-choice-active-task-ledger/)
- [`11.3.5.8-basic-failure-recovery`](../11.3.5.8-basic-failure-recovery/)
- [`11.3.5.9-taskpathplanner-multi-candidate-chat-integration`](../11.3.5.9-taskpathplanner-multi-candidate-chat-integration/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包把 11.3.5 working runtime 的人工闭环验收沉淀成可重复运行的
WAgent Runtime Eval Runner。它不是新的产品 Agent 能力，也不是 M15 全量 automated
evaluation 平台；它是 11.3.6 eval program 的第一条可执行 runner 包。

## 迭代定位

11.3.5.6 已经用人工方式证明 `/items` 可以完成：

```text
创建 session
-> 提供 /items URL
-> 学习新增项目 A
-> 执行新增项目 B
-> LearnedPath value_slot=item_name
-> slot_overrides.item_name=B
-> DOM evidence verified B
-> TaskResultReporter outcome=verified
-> WAgent evidence-based final response
```

11.3.6 总体规划把 runtime eval 拆成可逐步扩展的 11.3.6.x 子包。11.3.6.1 只负责
先把 `/items` 闭环和单路径 direct replay regression 变成可由开发者或 Codex 外部测试
操作员反复执行的 eval runner：

```text
one command
-> cases run through Conversation API
-> raw records collected
-> hard gates evaluated
-> JSON artifact + Markdown report written
-> exit code reflects required gate result
```

## 本包做什么

- 新增本地 eval runner：`scripts/evals/wagent_runtime_eval.py`。
- 新增根脚本：`pnpm run eval:wagent:items`，可选别名 `pnpm run eval:wagent`。
- 新增使用文档：`docs/testing/wagent-runtime-eval.md`。
- 第一版运行两个 required cases：
  - `items_closed_loop`
  - `single_path_direct_replay_regression`
- 直接调用 Conversation API，而不是依赖交互式 `wagent chat`。
- 自定义较长 HTTP timeout，避免 CLI 默认 timeout 污染 eval 结果。
- 采集 session、messages、events、history、LearnedPath detail 和 raw API responses。
- 对每个 case 生成独立 gate results。
- 输出 JSON 原始记录和 Markdown 结果文件。
- 用 exit code 区分 pass、gate fail、environment blocked、timeout 和 runner error。

## 本包不做

- 不新增产品 runtime 能力。
- 不新增内部 Agent 角色。
- 不改变 L1 / L2 / L3 产品生命周期。
- 不启用 `learn_then_execute`。
- 不调用 `verify-scenario`。
- 不调用 autonomous-run endpoints。
- 不把 direct replay API 冒充为 WAgent chat 闭环。
- 不使用登录页作为第一批验收用例。
- 不在第一版强行加入 failure recovery fault injection。
- 不把 Codex 自然语言判断作为 pass 标准。
- 不扩大到 M15 automated evaluation / audit / hygiene 平台。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - Eval Runner、case、gate、artifact、exit code 和越界契约。
- `technical-design.md` - runner 结构、API driver、evidence collector、gate evaluator、
  artifact writer 和最小只读可观测性扩展策略。
- `test-plan.md` - runner 自测、API preflight、case gate、artifact、exit code 和安全边界。
- `plan.md` - 实施步骤、文件清单、验证命令和收口流程。
- `review.md` - 文档生成、设计评审、实现证据、最终重跑证据和未运行项记录。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录设计评审结论、实现证据和最终重跑证据。

## 当前状态

runner core 已实现并在 2026-05-23 最终收口重跑中通过 live Conversation eval：

- Command: `pnpm run eval:wagent:items`
- Exit code: `0`
- Cases: `items_closed_loop`, `single_path_direct_replay_regression`
- Required gates: `10/10` and `9/9`
- JSON artifact:
  `artifacts/wagent-eval/wagent-runtime-eval-20260523T134338Z.json`
- Markdown result:
  `docs/testing/results/m11-11.3.6.1-wagent-runtime-eval-core-20260523T134338Z.md`

保留 caveats：`effective_value_B` 和 `evidence_target_item_list` 仍为 non-required
`not_observable` warning；当前 public history/events 未暴露 replay step effective value
或 request-side `evidence_targets` selector。
