# 实施计划（Implementation Plan）

状态：proposed

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`（代码型 / 混合型迭代）
- `test-plan.md`（触发条件满足时）

## 文档生成计划（如适用）

如果本计划是在生成或修订迭代文档时创建，先填写本节；无法安全判断时停为
`NEEDS_USER_INPUT`。

| Decision | Value |
|---|---|
| Target package path | `<path>` |
| Package type | `docs / code / mixed / validation / umbrella / campaign` |
| Parent / child route | `<parent, child, next route, or N/A>` |
| Required docs | `<README / intent / contract / technical-design / test-plan / plan / review / GOAL_RUNNER / CURRENT_STATE>` |
| Source inputs read | `<files>` |
| Contract / status / evidence changes | `<summary or N/A>` |
| Design-review gate | `<required / not required + why>` |
| Test-plan trigger | `<required / not required + why>` |
| Implementation authorization boundary | `<implementation_authorized required? where recorded?>` |
| Stop conditions | `<P0/P1, missing docs, state conflict, authorization missing, etc.>` |
| Handoff / checkpoint | `<next action>` |

## 文件 / 模块

- `<path>` - <计划改动>
- `<path>` - <计划改动>

## 步骤

1. <步骤和预期产出。>
2. <步骤和预期产出。>
3. <步骤和预期产出。>

## Checkpoints

每个阶段结束时必须更新 `review.md`；campaign / umbrella package 还必须同步
`CURRENT_STATE.md`。

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| docs / design | <review.md design entry> | <what allows implementation> | <P0/P1 / missing docs / conflict> |
| implementation | <changed files + test evidence> | <tests pass + no P0/P1> | <test fail / scope drift> |
| closeout | <FINAL_STATUS + next_action> | <PACKAGE_COMPLETE or next eligible child> | <NEEDS_USER_INPUT / BLOCKED> |

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。
如果本轮触发 `test-plan.md` 条件，不能只在这里写零散命令。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `<command>` | <它证明什么> | Yes / No | <如果包含或排除 live run，说明原因> |

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] 文档型迭代没有强制要求 `technical-design.md`。
- [ ] 代码型迭代实现匹配 `technical-design.md`。
- [ ] 混合型迭代按代码型迭代门禁处理。
- [ ] 如果触发条件满足，`test-plan.md` 已存在并与验证步骤一致。
- [ ] 验证命令已执行并记录到 `review.md`，或写明 not run / unverified 和原因。
- [ ] Campaign / umbrella package 已更新 `CURRENT_STATE.md`，或写明 N/A 和原因。
