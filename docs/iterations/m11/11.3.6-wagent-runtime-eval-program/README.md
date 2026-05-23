# 11.3.6 · WAgent Runtime Eval Program

状态：accepted_program_plan（program review passed，docs-only）
里程碑：M11
类型：docs
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)

## 迭代类型

- [x] 文档型迭代
- [ ] 代码型迭代
- [ ] 混合型迭代

11.3.6 是 WAgent runtime eval 的总体测试规划包。它不直接实现 runner，也不新增产品
runtime 能力；它定义 11.3.6.x 子包共享的 eval 分层、artifact、exit code、redaction、
Codex 审计边界和 case roadmap。

## 子包路线

| Package | 目标 | 状态 |
|---|---|---|
| [11.3.6.1 · WAgent Runtime Eval Runner Core](../11.3.6.1-wagent-runtime-eval-runner-core/) | 实现第一版可执行 runner，覆盖 first-wave runtime regression | implemented_and_live_eval_passed |
| [11.3.6.2 · Failure Recovery Eval](../11.3.6.2-failure-recovery-eval/) | 覆盖 recovery menu safety、retry / relearn / cancel 和 private payload safety | implementation_complete_non_live |
| [11.3.6.3 · Pending Choice Multi-candidate Eval](../11.3.6.3-pending-choice-multi-candidate-eval/) | 覆盖 A/B/C public choice、private map 和用户选择后执行正确 path | implementation_review_failed |
| [11.3.6.4 · Planner-backed Choice Eval](../11.3.6.4-planner-backed-choice-eval/) | 覆盖 vague goal、planner-backed choice path 和 single-path bypass Planner 回归 | implementation_review_failed |
| [11.3.6.5 · Runtime Eval Program Closeout](../11.3.6.5-runtime-eval-program-closeout/) | 核对 11.3.6.3 / 11.3.6.4 implementation、artifact、review closeout，并同步 program 状态 | blocked |
| [11.3.6.6 · Runtime Eval Gate Failure Fixes](../11.3.6.6-runtime-eval-gate-failure-fixes/) | 修复 11.3.6.5 service-available rerun 暴露的 pending choice payload leak、planner selection execution 和 artifact redaction failures | draft_for_review |

## 本包做什么

- 把 11.3.6 从单个 runner 实现包调整为 runtime eval program 总入口。
- 定义 11.3.6.x 子包共享的评价原则。
- 明确 first wave / later wave case 切分。
- 明确 Codex 是 artifact 审计员，不是 pass / fail 裁判。
- 明确 live run、autonomous run、`verify-scenario` 和 direct replay 边界。
- 将已评审通过的 runner core 实现设计下沉到 11.3.6.1。

## 本包不做

- 不新增 runner 代码、npm script 或测试使用文档。
- 不运行 eval。
- 不修改 Conversation API、TaskResultReporter、TaskPathPlanner 或 replay runtime。
- 不创建 M15 automated evaluation / audit / hygiene 平台。

## 迭代文档

- `intent.md` - 总体目标、动机、边界和成功标准。
- `contract.md` - eval program、case family、artifact、exit code、audit 和子包边界。
- `technical-design.md` - program-level structure and child package responsibilities。
- `test-plan.md` - docs-level review checks and child-package verification standards。
- `plan.md` - 拆分步骤、索引同步和后续实施顺序。
- `review.md` - 本次拆分评审记录。

## 当前状态

总体规划已通过 review。11.3.6.1 已 live eval pass；11.3.6.2 已完成 non-live
implementation checks，live Conversation eval 尚未运行；当前 runner 代码已覆盖到 11.3.6.4。
11.3.6.5 closeout sweep 已执行两轮：第一轮因 sandbox 内 API health 不可用写出 blocked
artifact；第二轮在 API / product-test-site 可访问后运行 required eval，11.3.6.3 和
11.3.6.4 均返回 exit `1`；新增 raw planner artifact 还暴露 full private path id，因此不提交
raw rerun artifact，只提交 sanitized closeout summary。因此 11.3.6 program 当前状态为
blocked / implementation review failed，不能标 `closed_live` 或 `closed_non_live`。
11.3.6.6 已开为后续代码型 fix 迭代文档包，当前只处于 `draft_for_review`。
