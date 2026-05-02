# 10.2 · Replay execution + drift detection

## 执行前必读

本包当前是 draft only，不能直接施工。后续修订为可
执行状态前，请先阅读 `AGENTS.md`、`docs/product-model.md`、
`docs/iterations/phase-10/phase-plan.md`，再读本目录的 `intent.md`
和 `plan.md`。

状态：Draft only，不可直接施工。开工前必须重新核对当前代码、
`10.1` 和 `10.1.1` 的最终结果，并把 `plan.md` 修订成可执行状态。

## 目标

让系统能消费已沉淀的 LearnedPath，在当前页面上做可解释的 replay
尝试，并在 DOM / URL / action 关键面发生变化时给出 drift 状态。

## 动机

- `10.1` 已经把 `pass_gate = pass` 的探索结果持久化为
  LearnedPath，但当前系统还不会消费这些记录。
- 产品阶段 3 的实际工作不能继续依赖探索式试错；它需要优先复用已学
  路径，并在路径过期时明确告诉用户或后续 planner。

## 边界（本轮不做）

- 不扩展 popup / click-toggle 新控件能力；这些属于 `10.3` /
  `10.4`。
- 不做跨页面模式归纳；这是 `10.6`。
- 不引入静默重试或自动循环优化。replay 失败必须产出明确状态。

## 成功标准

1. 能按当前页面 signature 查询候选 LearnedPath。
2. 能区分可 replay、轻微 drift、严重 drift、无可用路径。
3. replay 返回逐步日志和最终状态，不伪装成 autonomous learning
   的 pass/fail。
4. 单测覆盖 path 命中、无命中、drift、不可执行 action。
5. 如需 live run，只能通过 `verify-scenario` skill，并按
   `pass_gate.status`、Supervisor verdict、5 项 scorecard、`run_id`
   原样记录。
