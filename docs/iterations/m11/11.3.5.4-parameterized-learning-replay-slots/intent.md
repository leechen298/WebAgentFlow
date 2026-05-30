# 意图（Intent）

状态：ready_for_implementation（design review passed，未开始实现）

## 背景

11.3.5.3 已经在 `apps/fixture-site` 新增 `/records` 页面，为 P0 working loop
提供稳定列表页。下一步不是直接做 DOM evidence 或 Reporter，而是先解决 replay
参数化缺口：如果用户学习时输入的是“测试项目A”，后续执行时说“新增测试项目B”，
系统必须填入 B，而不是重放学习阶段固定录制值 A。

当前代码事实：

- `ReplayRequest` 只有 `url`，没有 `slot_overrides`。
- `ReplayAction` 有固定 `value`，没有 `value_slot`。
- `run_replay()` 从 LearnedPath actions 构造 replay actions 后直接执行固定值。
- `InteractiveChatRuntime._fill_values_from_intake()` 当前只处理 username / password。
- `ConversationIntake` fallback 当前不抽取 `record_name`。

## 目标

本迭代要让 `/records` 新增项目路径支持最小参数化执行：

```text
用户：学习新增项目，名称叫测试项目A
系统：学到 fill value=测试项目A，并把该 fill action 绑定 value_slot=record_name

用户：帮我新增项目，名称叫测试项目B
系统：构造 slot_overrides.record_name=测试项目B
系统：replay 时把对应 fill action 的 value 替换为测试项目B
系统：step log 可证明实际填入 B，而不是 A
```

## P0 用户价值

用户要的是“学会新增项目这个操作”，不是“永远新增测试项目A”。本包把 LearnedPath
从固定值回放推进到最小可参数化回放，后续 11.3.5.5 的 evidence / reporter 才能基于
真实执行结果判断成功或失败。

## 范围

本包实现：

- `record_name` slot extraction。
- `_fill_values_from_intake()` 支持 `record_name`。
- 学习完成后对 LearnedPath fill action 写入 `value_slot=record_name`。
- `ReplayRequest.slot_overrides`。
- `ReplayAction.value_slot`。
- `_build_replay_actions()` 读取 `value_slot`。
- `run_replay()` 接收并应用 `slot_overrides`。
- replay hook / runtime execution branch 传播 `slot_overrides`。
- `execute_action()` 和 `wait_for_change_after_action()` 使用 `effective_action`。
- step log / debug trace 证明 override 是否应用。
- path 无参数绑定时 runtime 阻断，不执行固定值 replay。

## 非目标

本包不做：

- ExecutionEvidence / `capture_execution_evidence`。
- TaskResultReporter adapter 或 Reporter verified path。
- DOM text check、`[data-testid='record-list']` evidence。
- `pending_choice`。
- `active_task` / RuntimeLedger。
- Failure Recovery 菜单。
- TaskPathPlanner chat 接入。
- `learn_then_execute` 自动组合。
- 搜索 / 编辑 / 删除参数化。
- DB migration 或新增 LearnedPath column。
- live autonomous run、`verify-scenario` 或产品 UI E2E。

## 成功标准

| 编号 | 标准 | 验收方式 |
|---|---|---|
| INT-1 | “名称叫测试项目A / B” 能抽取 `record_name` | intake unit tests |
| INT-2 | `_fill_values_from_intake()` 生成 `record_name` | runtime unit tests |
| LRN-1 | 学习后 fill action 可写入 `value_slot=record_name` | learning service tests |
| REP-1 | Replay schema 支持 `slot_overrides` / `value_slot` | schema tests |
| REP-2 | replay 使用 B 替换 A | replay service tests |
| REP-3 | wait-for-change 使用 `effective_action` | replay service tests |
| RUN-1 | chat runtime execute branch 把 `record_name` 传到 replay handler | runtime integration tests |
| SAFE-1 | path 无 `value_slot=record_name` 时阻断 replay | runtime integration tests |

## 出口标准

本包完成时，只能声称参数化 replay 机制通过。不能声称 `/records` 闭环已经完成，因为
ExecutionEvidence、Reporter adapter 和完整闭环记录属于 11.3.5.5 / 11.3.5.6。
