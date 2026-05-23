# 11.3.6.4 · Planner-backed Choice Eval

状态：implementation_complete_verified（planner-backed choice eval pass）
里程碑：M11
类型：code
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：
[`11.3.6.1-wagent-runtime-eval-runner-core`](../11.3.6.1-wagent-runtime-eval-runner-core/)、
[`11.3.6.3-pending-choice-multi-candidate-eval`](../11.3.6.3-pending-choice-multi-candidate-eval/)、
[`11.3.5.9-taskpathplanner-multi-candidate-chat-integration`](../11.3.5.9-taskpathplanner-multi-candidate-chat-integration/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

11.3.6.4 是 WAgent Runtime Eval Program 的第四个执行包。它在 11.3.6 runner
之上增加 planner-backed choice eval coverage，用 hard gates 验证 11.3.5.9 已实现的
TaskPathPlanner multi-candidate chat path：

```text
当前 eval run 准备多个候选 learned actions
-> 用户输入 vague goal / URL + vague action
-> Runtime 进入 TaskPathPlanner-backed choice path
-> Runtime 生成 sanitized public A/B/C choices
-> 用户选择 planner-backed choice
-> Runtime 记录 planner_choice_selected 并执行对应 learned action
-> Reporter / DOM evidence verified
```

本包同时保护单路径回归：只有一个明确 learned action 时，Runtime 必须直接 replay，不应调用
TaskPathPlanner 或生成 planner-backed pending choice。

## 本包做什么

- 在 eval runner 中新增 `planner_backed_choice` case family。
- 校验 `planner_candidates_generated`、`planner_choice_created`、`planner_choice_selected`
  等 sanitized planner events。
- 校验 public A/B/C choices 不泄露 `learned_path_id`、selector、slot overrides、
  private planner payload 或 raw planner warnings。
- 校验用户选择后执行当前 eval run 预期 learned action。
- 校验 single-path direct replay 不进入 Planner。
- 增加 runner unit / integration tests、artifact redaction tests 和安全 grep。

## 本包不做

- 不新增 TaskPathPlanner 产品能力；只验证已有 11.3.5.9 runtime 行为。
- 不让 runner 直接调用 `TaskPathPlanner.plan()` 来冒充 runtime planner path。
- 不修改 TaskPathPlanner domain schema。
- 不验证 non-planner pending choice；该能力属于 11.3.6.3。
- 不验证 failure recovery menu；该能力属于 11.3.6.2。
- 不使用登录页或敏感输入场景。
- 不调用 autonomous-run endpoints。
- 不默认调用 `verify-scenario`。
- 不把 direct replay API 结果冒充 WAgent conversation runtime 闭环。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - case、setup、planner gate、redaction、artifact 和 exit code contract。
- `technical-design.md` - runner 扩展、planner candidate setup、evidence collector 和 gate evaluator 设计。
- `test-plan.md` - unit / integration / case / artifact / safety 测试矩阵。
- `plan.md` - 实施步骤、文件范围、验证命令和 review 收口。
- `review.md` - 本迭代设计评审和实现结果记录。

## 当前状态

实现已完成，并在 2026-05-23 final closeout rerun 中通过
`pnpm run eval:wagent:planner-choice`。结果：exit `0`，`planner_backed_choice`
required gates `17/17`，`planner_single_path_bypass_regression` required gates `8/8`。
证据：`artifacts/wagent-eval/wagent-runtime-eval-20260523T135028Z.json` 和
`docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-20260523T135028Z.md`。

Caveat：当前 setup 为 `eval_only_planner_candidate_binding`，
`planner_distinct_path_capability=false`；`planner_top_choice_observable` 仍是非 required
`not_observable` warning。
