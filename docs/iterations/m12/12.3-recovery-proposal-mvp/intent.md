# 12.3 Recovery Proposal MVP Intent

状态：proposed

## Goal

12.3 的目标是定义 Recovery Proposal MVP：把 12.1 `RecoveryBoundary` 和
12.2 `AbortAcknowledgement` 转成可展示给用户的恢复选项，同时保持 proposal 与
execution 完全分离。

本轮只完成实现前设计包，不写代码。

## Motivation

M12 已经形成两个安全边界：

- 12.1 负责 failure / blocked / uncertain / needs_review 的 deterministic
  recovery boundary classification。
- 12.2 负责 user abort / stop 的 deterministic acknowledgement 和 stop boundary。

下一步不能直接 retry、replan 或继续浏览器。原因是 failure / abort 后的恢复动作
可能改变网页状态、重复不可逆副作用，或绕过用户控制权。WebAgentFlow 必须先把
“可展示给用户的选项”和“真实执行动作”拆开。

12.3 存在的理由是：

- 让用户看到可解释、可审计的下一步选项；
- 让每个选项携带 evidence refs、confirmation markers 和 policy-check markers；
- 把 retry / replan / takeover / teaching 等动作交给后续包；
- 防止推荐选项被误读成系统已经替用户选择。

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
- deterministic proposal generator design；
- future unit test matrix；
- handoff to 12.4 retry policy；
- handoff to 12.5 conversation flow。

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
- `verify-scenario`；
- E2E。

## Success Criteria

- 12.3 文档目录包含完整代码型迭代包：
  `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
  `test-plan.md`、`plan.md`、`review.md`。
- 文档明确 `Proposal is not execution` 和 `Proposal is not command`。
- 文档明确所有 proposal options 默认 `non_executable=true`。
- 文档明确 recommended option 不是 selected option。
- 文档明确未来 schema 不设计 `selected_option_id`。
- 文档明确 `consider_retry_later` 不是 retry，12.4 才定义 retry policy。
- 文档明确 `suggest_reteach` 不是 hidden relearning 或 LearnedPath write-back。
- 文档明确 `wait_for_runtime_observation_later` 不是 M11.2 实现。
- `technical-design.md` 只设计未来实现，不创建代码。
- `test-plan.md` 覆盖 recovery proposal future unit matrix，并明确 API / UI / E2E /
  live run 不在本轮执行。
- `plan.md` 的验证表格引用 `technical-design.md` 和 `test-plan.md`。
- `review.md` 按实际运行结果记录 validation evidence 和未运行项。
