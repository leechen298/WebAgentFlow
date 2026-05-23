# 11.3.6.5 · Runtime Eval Program Closeout

状态：completed_after_fix_rerun（final closeout rerun pass）
里程碑：M11
类型：docs
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：
[`11.3.6.1-wagent-runtime-eval-runner-core`](../11.3.6.1-wagent-runtime-eval-runner-core/)、
[`11.3.6.2-failure-recovery-eval`](../11.3.6.2-failure-recovery-eval/)、
[`11.3.6.3-pending-choice-multi-candidate-eval`](../11.3.6.3-pending-choice-multi-candidate-eval/)、
[`11.3.6.4-planner-backed-choice-eval`](../11.3.6.4-planner-backed-choice-eval/)

## 迭代类型

- [x] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代

本包是 11.3.6 runtime eval program 的收口扫尾包。它不新增 runner case、不改
Conversation runtime、不改 TaskPathPlanner / recovery / pending choice 产品语义；它只定义如何
核对当前 runner、运行或记录 eval 结果、补齐 11.3.6.3 / 11.3.6.4 closeout evidence，并同步
11.3.6 program 与 M11 索引状态。

## 本包做什么

- 复核远端 `v0.1` 上 11.3.6.x 子包的实现、review、artifact 和结果文档状态。
- 运行或明确跳过 11.3.6.3 / 11.3.6.4 eval commands，并按实际结果生成 artifact。
- 回填 11.3.6.3 / 11.3.6.4 `review.md` 的 implementation / live eval closeout。
- 回填 11.3.6 program README / review、M11 README、`m11-plan.md` 的状态。
- 产出一份 program-level closeout result，说明 11.3.6 当前是 fully closed、non-live closed、
  partially closed，还是 blocked。

## 本包不做

- 不新增产品 runtime 能力。
- 不新增 runner case family。
- 不修 bug；如果 eval 暴露实现 bug，必须停止 closeout 并另开代码型 fix 迭代。
- 不调用 autonomous-run endpoints。
- 不默认调用 `verify-scenario`。
- 不把 fixture / blocked path / non-live pass 冒充 live Conversation eval pass。
- 不把 Codex 自然语言判断当作 pass / fail 标准。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - closeout 状态、artifact、evidence 和不允许冒充的边界契约。
- `technical-design.md` - closeout sweep 的文件范围、命令顺序和状态同步设计。
- `test-plan.md` - closeout 验证矩阵、live / non-live / blocked 记录规则。
- `plan.md` - 实施步骤、命令入口和 review 回填顺序。
- `review.md` - 设计评审、实际执行结果和最终 closeout 证据。

## 当前状态

Closeout sweep 已执行三轮。第一轮 `pnpm run eval:wagent:pending-choice` 和
`pnpm run eval:wagent:planner-choice` 均返回 exit `2`，写出 blocked artifact。第二轮在 API
和 product-test-site 可访问后重跑，两个 required eval 均返回 exit `1`，因此开启
11.3.6.6 代码型 fix 迭代。11.3.6.6 修复后，final closeout rerun 已通过：

- `pnpm run eval:wagent:items` -> exit `0`
- `pnpm run eval:wagent:failure-recovery` -> exit `0`
- `pnpm run eval:wagent:pending-choice` -> exit `0`
- `pnpm run eval:wagent:planner-choice` -> exit `0`

Program-level closeout result:
`docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md`。
M11.3.6 program 可标记为 closed / pass with documented caveats。
