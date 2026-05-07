# 10.2.1 Replay Schema

## 目标

定义 replay 的输入、输出、状态枚举和单步日志结构，让后续 service、
API、UI 都使用同一份 contract。

## 触及模块

- `apps/api/app/schemas/learned_path_replay.py`

## 固定 contract

- `ReplayRequest`
  - 字段：`url`
  - 本轮不加入 `scenario`、`learned_path_id`、`force` 或自动候选 replay
    参数。
- `ReplayAction`
  - 从 LearnedPath `actions` 中的 dict 重建。
  - 读取字段：`step`、`action_type`、`target_selector`、
    `target_description`、`value`。
  - `step` 缺失时按 action list index 从 0 补齐。
  - `action_type` 先按字符串接收；service 层再判断是否支持。
  - supported 非 `observe` action 的 selector 缺失时，由 service 返回
    `target_missing`，不要在 schema 层变成 500。
- `ReplayStepLog`
  - 字段覆盖 step index、action type、selector、ok、error、
    matched_count、URL / title before-after、screenshot ref。
- `ReplayDriftStatus`
  - `none`
  - `signature_changed`
  - `target_missing`
  - `page_mismatch`
  - `unsupported_action`
  - `no_candidate`
- `ReplayStatus`
  - `succeeded`
  - `observed`
  - `drifted`
  - `failed`
  - `unsupported`
  - `candidate_not_found`
  - `runtime_error`
- `ReplayResult`
  - 包含 selected path、stored signature、current signature、
    drift status、drift reasons、warnings、step logs、final state。

## 验收

- 合法 `fill` / `click` / `press` / `observe` 能从已存 action dict 重建。
- unsupported action 不在 schema 层炸成 500。
- selector 缺失能留给 service 转成 `target_missing`。
- 这些 status 明确是 replay 自己的状态，不是 `pass_gate.status`。
