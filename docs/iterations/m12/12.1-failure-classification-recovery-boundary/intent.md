# 12.1 Failure Classification and Recovery Boundary Intent

Status: documentation initialized.

## Goal

初始化 12.1 文档边界：设计一个未来可实现的 evidence-bound classifier，用于
从 M11.1 structured execution / result reporting evidence 中分类
`failure`、`blocked`、`uncertain`、`needs_review`，并给出 recovery boundary
recommendation。

12.1 是分类器和边界建议层，不是恢复执行器。

## Motivation

M12 不能一开始就做 retry、proposal 或 conversation flow。原因是这些动作都会
影响用户对运行时结果的理解：如果系统没有先把 failure、blocked、uncertain、
needs_review 分清楚，就直接生成 recovery proposal 或 retry suggestion，
recovery 很容易变成隐式行为。

M11.1 已经刻意保持保守：

- replay completed 不等于 task succeeded；
- blocked execution 明确记录为 blocked；
- failed replay 不自动修复；
- successful replay + no postcondition evidence 会得到 `uncertain`；
- Task Result Reporter payload 带有 `no_recovery`、`no_autonomous`、`no_llm`
  markers。

12.1 的意义是把这些证据转成清晰、稳定、可审计的 M12 边界判断。后续 12.3
可以基于它生成 proposal，12.4 可以基于它判断 retry policy，但 12.1 自己不
进入 proposal 或 retry。

## Boundary / Non-goals

12.1 做：

- failure classification；
- blocked classification；
- uncertain classification；
- needs_review classification；
- recovery boundary recommendation；
- evidence source mapping；
- classifier non-execution contract；
- 未来测试计划设计。

12.1 不做：

- user abort handling；
- runtime stop / pause implementation；
- recovery proposal generation；
- retry command；
- retry execution；
- conversation recovery flow；
- LLM-based recovery planning；
- autonomous exploration；
- hidden relearning；
- teaching mode；
- LearnedPath write-back；
- slot binding expansion；
- multi-page workflow；
- artifact lifecycle expansion；
- M11.2 Runtime Observation / Wait-for-change。

如果发现 `docs/iterations/m12/**` 之外有 stale reference，本轮只记录为
follow-up，不修改全局文档。

## Success Criteria

- 12.1 文档目录包含 `README.md`、`intent.md`、`plan.md`、`review.md`。
- 文档明确 12.1 的输入来自 M11.1 structured execution / result reporting
  evidence。
- 文档定义 `FailureClassification`、`RecoveryBoundary`、
  `ClassificationReason`、`EvidenceReference`、`BoundaryRecommendation`。
- 文档定义分类值：`success_no_recovery_needed`、`failure`、`blocked`、
  `uncertain`、`needs_review`。
- 文档定义 boundary recommendation：`stop`、`ask_user`、`needs_review`、
  `suggest_reteach`、`retry_possible_requires_confirmation`、
  `no_recovery_needed`。
- 文档明确 `retry_possible_requires_confirmation` is not retry execution。
- 文档明确 classifier 不执行 recovery、retry、replan、browser continuation、
  hidden relearning 或 user-facing recovery dialogue。
- 文档明确 user abort 属于 12.2，不属于 12.1。
- 文档明确 12.1 不读取 raw HTML 做自由规划，不依赖默认 LLM provider。
