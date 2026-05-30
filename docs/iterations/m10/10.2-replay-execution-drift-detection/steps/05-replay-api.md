# 10.2.5 Replay API

## 目标

给前端一个明确入口，让用户指定某条 LearnedPath 进行 replay。

## 触及模块

- `apps/api/app/routers/exploration.py`
- `apps/api/app/schemas/learned_path_replay.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/tests/test_exploration_learned_paths_api.py`
- `apps/api/tests/test_learned_path_replay.py`

## 路由

```text
POST /exploration/learned-paths/{path_id}/replay
```

## 请求体

```json
{
  "url": "https://example.invalid/records"
}
```

本轮 request body 不包含 `scenario`、`learned_path_id`、`force` 或自动候选
replay 参数。

## 响应体

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "learned_path_id": "...",
    "source_run_id": "...",
    "trust": "confirmed",
    "status": "succeeded",
    "drift_status": "none",
    "drift_reasons": [],
    "warnings": [],
    "stored_signature": {},
    "current_signature": {},
    "steps": [],
    "final_url": "...",
    "final_title": "..."
  }
}
```

## HTTP 行为

- path 不存在：`404`。
- path 是 `deprecated`：`422`。
- path 是 `flaky`：允许显式 replay，但 `warnings` 必须包含 trust warning。
- body 缺 URL：`422`。
- Playwright 启动或导航失败：返回 `status = runtime_error`，不要吞掉错误。
- 本轮显式 path replay 中，path id 不存在始终是 HTTP `404`，不是
  `candidate_not_found`。

`candidate_not_found` / `no_candidate` 只服务 repo / service candidate
helper 或未来 M11.1 自动候选路径。本轮不做自动候选 replay API / UI。

## 禁止事项

- 不新增或调用 `/exploration/autonomous-runs`。
- 不新增或调用 `/exploration/autonomous-runs/stream`。
- 不把 replay 结果包装成 `pass_gate`。
- 不返回 Supervisor verdict。

## 验收

- valid path 返回 `ReplayResult`。
- path 不存在返回 `404`。
- deprecated path 返回 `422`。
- flaky path 返回 trust warning。
- runtime error 返回结构化 `runtime_error`。
