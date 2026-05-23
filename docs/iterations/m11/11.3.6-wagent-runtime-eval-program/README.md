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
| [11.3.6.1 · WAgent Runtime Eval Runner Core](../11.3.6.1-wagent-runtime-eval-runner-core/) | 实现第一版可执行 runner，覆盖 first-wave runtime regression | ready_for_implementation |
| [11.3.6.2 · Failure Recovery Eval](../11.3.6.2-failure-recovery-eval/) | 覆盖 recovery menu safety、retry / relearn / cancel 和 private payload safety | implementation_complete_non_live |
| [11.3.6.3 · Pending Choice Multi-candidate Eval](../11.3.6.3-pending-choice-multi-candidate-eval/) | 覆盖 A/B/C public choice、private map 和用户选择后执行正确 path | ready_for_implementation |
| 11.3.6.4 · Planner-backed Choice Eval | 覆盖 vague goal、planner choice path 和 single-path bypass Planner 回归 | planned |

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

总体规划已通过 review。11.3.6.1 已承接 runner v1 的可实现设计；11.3.6.2
failure recovery eval 已完成 non-live implementation checks，live Conversation eval 尚未运行；
11.3.6.3 pending choice eval 设计已通过 review，可以进入实现；
11.3.6.4 后续另开完整迭代文档。
