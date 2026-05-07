# 10.2.4 Shared Action Executor

## 目标

把单步浏览器动作执行从 autonomous explorer 私有函数中抽出来，让
autonomous exploration 和 LearnedPath replay 共用同一个执行器。

## 触及模块

- `apps/api/app/services/execution/action_executor.py`
- `apps/api/app/services/learning/autonomous_explorer.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_learned_path_replay.py`

## 当前来源

当前单步执行逻辑在：

```text
apps/api/app/services/learning/autonomous_explorer.py::_execute_step
```

10.2 不直接 import 这个私有函数，也不复用整个 autonomous pipeline。

## 固定接口

```text
execute_action(action, runtime) -> dict
observe_step(runtime, step_index=...) -> dict
```

## 抽取边界

- 保持 autonomous explorer 原有 step log 字段兼容。
- 不借机重构 planner、Supervisor、pass gate 或 workbench history。
- `action_executor.py` 只负责单步动作执行和 observe。
- `action_executor.py` 不做 replay drift 判断。
- `action_executor.py` 不读取 LearnedPath。
- `action_executor.py` 不触发 autonomous run。

## 支持动作

- `fill`
- `click`
- `press`
- `observe`

unsupported action 由 replay service 在执行前拦截；executor 仍要对未知
动作保持防御性返回，不能抛出未处理异常。

执行失败语义：

- selector 存在且 action type 支持，但 `fill` / `click` / `press` /
  `observe` 执行失败时，executor 返回 step log：`ok = false` 和 error。
- replay service 将这类失败映射为 `status = failed`。
- `drift_status` 保留 drift precheck 的结果，例如 `none` 或
  `signature_changed`。
- 不把这类执行失败改写成 `target_missing`、`unsupported_action` 或
  `runtime_error`。

## 验收

- 原 autonomous 相关单测不因抽取破坏 step log 字段。
- executor 单测覆盖 fill / click / press / observe。
- selector missing 能返回结构化失败。
- action 执行 timeout / 元素不可见 / click 被遮挡时，step log 记录
  `ok = false` 和 error。
- unknown action 不造成 500。
