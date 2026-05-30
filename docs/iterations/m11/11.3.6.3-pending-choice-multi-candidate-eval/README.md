# 11.3.6.3 · Pending Choice Multi-candidate Eval

状态：implementation_complete_verified（pending-choice eval pass）
里程碑：M11
类型：code
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：
[`11.3.6.1-wagent-runtime-eval-runner-core`](../11.3.6.1-wagent-runtime-eval-runner-core/)、
[`11.3.5.7-pending-choice-active-task-ledger`](../11.3.5.7-pending-choice-active-task-ledger/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

11.3.6.3 是 WAgent Runtime Eval Program 的第三个执行包。它在 11.3.6.1 runner
core 之上增加 pending choice multi-candidate eval coverage，用 hard gates 验证
11.3.5.7 已实现的多候选澄清边界：

```text
当前 eval run 准备多个候选 learned actions
-> 用户输入模糊但可执行的目标
-> Runtime 生成 public A/B/C choices
-> public payload 不泄露 learned_path_id / private map
-> 用户选择 A
-> Runtime 执行 A 对应的 learned action
-> pending_choice / private map 被清理
```

本包不验证 planner-backed choice。Planner-backed choice 属于 11.3.6.4。

## 本包做什么

- 在 eval runner 中新增 `pending_choice_multi_candidate` case family。
- 定义多候选 setup 的稳定来源和污染隔离规则。
- 校验 public choice visible payload、sanitized events 和 private map 不外泄。
- 校验用户选择 A 后执行当前 eval run 中 A 对应的 learned action。
- 校验 choice selection 后清理 pending choice state。
- 增加 runner unit / integration tests 和安全回归检查。

## 本包不做

- 不新增产品级 pending choice 能力；只验证已有 11.3.5.7 runtime 行为。
- 不接 TaskPathPlanner；planner-backed choice 留到 11.3.6.4。
- 不验证 failure recovery menu；failure recovery eval 属于 11.3.6.2。
- 不使用登录页或敏感输入场景。
- 不调用 autonomous-run endpoints。
- 不默认调用 `verify-scenario`。
- 不把 direct replay API 结果冒充 WAgent conversation runtime 闭环。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - case、setup、gate、redaction、artifact 和 exit code contract。
- `technical-design.md` - runner 扩展、multi-candidate setup、evidence collector 和 gate evaluator 设计。
- `test-plan.md` - unit / integration / case / artifact / safety 测试矩阵。
- `plan.md` - 实施步骤、文件范围、验证命令和 review 收口。
- `review.md` - 本迭代设计评审和实现结果记录。

## 当前状态

实现已完成，并在 2026-05-23 final closeout rerun 中通过
`pnpm run eval:wagent:pending-choice`。结果：exit `0`，`pending_choice_multi_candidate`
required gates `15/15`。证据：
`artifacts/wagent-eval/wagent-runtime-eval-20260523T134741Z.json` 和
`docs/testing/results/m11-11.3.6.3-pending-choice-multi-candidate-eval-20260523T134741Z.md`。

Caveat：当前 setup 为 `eval_only_candidate_binding`，
`live_multi_action_capability=false`，不证明 `/records` 已有三个真实 distinct product actions。
