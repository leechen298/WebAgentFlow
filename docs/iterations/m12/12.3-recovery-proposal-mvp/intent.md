# 12.3 Recovery Proposal MVP Intent

Status: documentation initialized.

## Goal

初始化 12.3 文档边界：定义一个未来可实现的 recovery proposal MVP，用于把
12.1 `RecoveryBoundary` 和 12.2 `AbortAcknowledgement` 转成可展示给用户的
恢复选项。

12.3 只定义 proposal 语义、option shape、evidence requirement 和
non-execution contract，不执行 proposal。

## Motivation

M12 已经有两个前置边界：

- 12.1 判断 failed / blocked / uncertain / needs_review 后的 recovery boundary。
- 12.2 判断 user abort / stop 后的 stop acknowledgement。

下一步不能直接 retry、replan 或继续浏览器。原因是 failure / abort 后的恢复动作
会影响网页状态，也可能重复不可逆副作用。系统必须先把“可向用户展示的选项”和
“真正执行动作”拆开。

如果 proposal 和 execution 混在一起，会出现这些风险：

- 用户看到的是建议，但系统已经开始执行；
- `consider_retry_later` 被误解成 retry command；
- `suggest_reteach` 变成 hidden relearning；
- abort 后绕过 no-new-browser-action boundary；
- 推荐选项被自动选择，变成隐式 recovery。

12.3 的意义是让 WebAgentFlow 能解释下一步选择，同时保留用户确认和后续 policy
边界。

## Boundary / Non-goals

12.3 做：

- recovery proposal semantics；
- proposal input sources；
- proposal option types；
- proposal safety wording；
- proposal evidence references；
- proposal non-execution contract；
- proposal confirmation requirement marker；
- proposal display boundary；
- handoff to 12.4 retry policy；
- handoff to 12.5 conversation flow；
- future test plan。

12.3 不做：

- retry / re-run policy；
- retry execution；
- replan execution；
- browser continuation；
- conversation recovery flow；
- API endpoint；
- CLI command；
- frontend UI；
- DB / migration；
- M11.2 Runtime Observation / Wait-for-change；
- teaching mode；
- takeover implementation；
- LearnedPath write-back；
- autonomous exploration；
- hidden relearning；
- `verify-scenario`。

## Success Criteria

- 文档目录包含 `README.md`、`intent.md`、`plan.md`、`review.md`。
- 文档明确 `Proposal is not execution`。
- 文档明确 proposal 基于 12.1 `RecoveryBoundary` 和 12.2
  `AbortAcknowledgement`。
- 文档定义 proposal source、option kinds、option shape 和 next owner。
- 文档明确所有 proposal options 默认 `non_executable=true`。
- 文档明确 12.3 可以排序或标记推荐，但不能自动选择 proposal。
- 文档明确 `consider_retry_later` 不是 retry，12.4 才处理 retry policy。
- 文档明确 `handoff_to_takeover_later` 不是 takeover implementation。
- 文档明确 `wait_for_runtime_observation_later` 不是 M11.2 实现。
- 文档明确 `suggest_reteach` 不是 hidden relearning 或 LearnedPath write-back。
- 文档明确本轮不写代码、不跑 API / CLI / E2E / `verify-scenario`。
