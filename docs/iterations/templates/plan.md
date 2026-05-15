# 实施计划（Implementation Plan）

状态：proposed

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`（代码型 / 混合型迭代）
- `test-plan.md`（触发条件满足时）

## 文件 / 模块

- `<path>` - <计划改动>
- `<path>` - <计划改动>

## 步骤

1. <步骤和预期产出。>
2. <步骤和预期产出。>
3. <步骤和预期产出。>

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
