# 12.3 · Recovery Proposal MVP

状态：implemented
里程碑：M12
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

12.3 是代码型迭代。已实现 recovery proposal schema、
deterministic proposal generator 和 focused unit tests。

## 当前状态

- 12.1 Failure Classification and Recovery Boundary 已实现并交付。
- 12.2 User Abort / Stop Handling 已实现并交付。
- 12.3 Recovery Proposal MVP 已实现并交付（commit `b139aab`）。

实现 Agent 不得跳过本设计包临时发明方案。用户明确发起 12.3 implementation
时，应读取并遵守：

- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - proposal 概念、状态、schema、evidence、兼容性和不变契约。
- `technical-design.md` - schema / service / data flow / compatibility 设计。
- `test-plan.md` - unit matrix 和未运行的 API / UI / E2E / live run 边界。
- `plan.md` - 实施步骤和验证命令。
- `review.md` - 实际验证证据、未运行项和 follow-ups。

## 代码型迭代准备状态

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录设计包对齐的验证证据和未运行项。

Design package alignment 和代码实现均已完成（commit `b139aab`，后续
schema-polish review fix 加固 `non_executable` 契约）。
74 tests passed, ruff clean。API / CLI / E2E / live run 不在本轮范围。

## 核心原则

```text
Proposal is not execution.
Proposal is not command.
Proposal option is non-executable by default.
Recommended option is not selected option.
```

12.3 生成或格式化的是用户可见的恢复选项，不是执行命令。它不能触发 retry、
replan、browser continuation、conversation dispatch、LearnedPath write-back、
teaching flow 或 takeover flow。

## 和 12.1 / 12.2 的关系

- 12.1 输出 `RecoveryBoundary`：classification、recommendation、reason 和
  evidence references。
- 12.2 输出 `AbortAcknowledgement`：stop decision、abort evidence、
  `no_new_actions_after` 和 `inflight_caveat`。
- 12.3 只消费这些结构化输出，生成 proposal options。它不重新分类 failure，
  不重新处理 abort，不绕过 12.2 的 no-new-browser-action boundary。

## Proposal Option 边界

所有 proposal option 默认 `non_executable=true`。未来实现不应设计
`selected_option_id` 或等价 selected-state 字段。可以使用
`recommended_option_ids`、`rank` 或 `priority` 表达展示顺序和推荐程度，但不能
暗示系统已经替用户选中了下一步。

## Live Run 边界

本轮不触发 live run、`verify-scenario`、autonomous run、UI smoke 或 E2E。
若未来需要 live run，必须按仓库根 `AGENTS.md` 记录 `pass_gate.status`、
Supervisor verdict、scorecard 和 `run_id`。
