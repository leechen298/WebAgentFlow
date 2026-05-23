# 11.3.6.6 · Runtime Eval Gate Failure Fixes

状态：implementation_complete_verified（fixes implemented，final eval rerun pass）
里程碑：M11
类型：code
父迭代：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)
前置迭代：
[`11.3.6.3-pending-choice-multi-candidate-eval`](../11.3.6.3-pending-choice-multi-candidate-eval/)、
[`11.3.6.4-planner-backed-choice-eval`](../11.3.6.4-planner-backed-choice-eval/)、
[`11.3.6.5-runtime-eval-program-closeout`](../11.3.6.5-runtime-eval-program-closeout/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

11.3.6.6 是 11.3.6.5 closeout 暴露的代码修复包。它不新增 eval case，也不扩大产品能力；
它只修复 service-available rerun 中已经定位的 required gate failures：

- 11.3.6.3 pending choice public payload 泄漏 private `learned_path_id` token。
- 11.3.6.4 planner-backed choice 选择 A 后没有启动 execution。
- runner raw artifact / result redaction 未覆盖 full private path id。

## 本包做什么

- 修 pending choice public surfaces，只暴露 A/B/C、label、description、intent、choice group 等安全字段。
- 保留 private choice map 的内部执行能力，但不让 private path id / private map 出现在 public session、
  public event、history、messages 或 committed artifacts。
- 修 planner-backed choice selection，使选择 A 后进入 selected learned action execution，并产生
  `chat_execution_started`、execution verified、final response verified。
- 补强 runner artifact redaction，确保 raw response text / planner payload / gate evidence 不提交 full
  private path id。
- 增加 targeted tests 和 rerun `pnpm run eval:wagent:pending-choice` /
  `pnpm run eval:wagent:planner-choice`。

## 本包不做

- 不新增新的 WAgent eval case family。
- 不改变 TaskPathPlanner ranking / planning algorithm。
- 不把 eval-only candidate binding 升级为真实 live multi-action product capability。
- 不改数据库 schema。
- 不调用 autonomous-run endpoints。
- 不调用 `verify-scenario`。
- 不用 direct replay API 冒充 Conversation runtime closed loop。
- 不关闭 11.3.6 program；本包 pass 后仍需回到 11.3.6.5 closeout 重新收口。

## 迭代文档

- `intent.md` - 目标、动机、边界和成功标准。
- `contract.md` - public / private payload、planner selection execution、artifact redaction 和状态契约。
- `technical-design.md` - runtime、runner、tests 的最小修复设计。
- `test-plan.md` - unit / integration / live eval / safety 测试矩阵。
- `plan.md` - 实施步骤、文件范围、验证命令和后续 closeout。
- `review.md` - 设计评审、实现评审和实际验证证据。

## 当前状态

11.3.6.5 service-available rerun 已证明问题不再是环境 blocked，而是 required gates fail。本包
设计已通过 review 并完成实现；final closeout rerun 中 pending-choice 和 planner-choice
均 exit `0`，并额外重跑了 items / failure-recovery。实现过程中 final items rerun 暴露
LLM provider 在完整 intake 上误置 `should_ask_user=true` 的缺口，已通过
`fix: normalize complete intake ask state` (`f2d7d55`) 修复。

最终证据见：
`docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md`。
