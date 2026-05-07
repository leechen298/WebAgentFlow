# 10.2 实施总纲

状态：**可施工**。

本目录把原来的长计划拆成总纲 + 分步施工文档。AI 编码 Agent 开工前仍
必须阅读本文件；具体实现时按 `steps/` 顺序逐份执行。

## 快速入口

- [brief.md](./brief.md) —— 极简版，1 屏内看懂本轮要做什么。
- [simple.md](./simple.md) —— 通俗版，给非实现阅读。
- [steps/01-replay-schema.md](./steps/01-replay-schema.md)
- [steps/02-candidate-selection.md](./steps/02-candidate-selection.md)
- [steps/03-drift-checker.md](./steps/03-drift-checker.md)
- [steps/04-shared-action-executor.md](./steps/04-shared-action-executor.md)
- [steps/05-replay-api.md](./steps/05-replay-api.md)
- [steps/06-catalog-ui.md](./steps/06-catalog-ui.md)
- [steps/07-tests-and-review.md](./steps/07-tests-and-review.md)

## 主线

10.2 属于 **M10 Path Asset Foundation**。它复用已有 LearnedPath，重新
打开页面，照着已存 actions 重跑一次，并返回“还能不能用、哪里变了、
哪一步失败”的结构化结果。

10.2 会给未来 **M11.1 Task-to-Path Planning & Execution MVP** 提供
replay engine，但本轮不实现 Agent D、自然语言任务理解、slot binding
或 L3 task runner。

## 固定边界

本轮只做 LearnedPath replay execution + drift detection。

明确不做：

- task input / chat 入口。
- Runtime Conversation Surface / CLI。
- Conversation Orchestrator / Dispatcher。
- 根据用户自然语言任务检索、选择、组合 LearnedPath。
- slot binding。
- Agent D / E / F / G / H。
- recovery / abort dialogue。
- teaching mode。
- 执行前确认流。
- action risk / consent gate。
- artifact lifecycle。
- task postcondition verification。
- multi-page workflow composition。
- 目标网页 Cookie、`localStorage`、session state 或目标站点权限托管。
- 调用 `/exploration/autonomous-runs` 或
  `/exploration/autonomous-runs/stream`。
- 把 replay 结果伪装成 `pass_gate` 或 Supervisor verdict。

## 核心 Contract

### Replay API

```text
POST /exploration/learned-paths/{path_id}/replay
```

请求体固定为：

```json
{
  "url": "http://127.0.0.1:5175/users"
}
```

本轮不在 request body 加 `scenario`、`learned_path_id`、`force` 或自动
候选 replay 参数。

响应 data 至少包含：

```json
{
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
```

HTTP 行为：

- path 不存在：`404`。
- path 是 `deprecated`：`422`。
- path 是 `flaky`：允许显式 replay，但 `warnings` 必须包含 trust
  warning。
- body 缺 URL：`422`。
- Playwright 启动或导航失败：返回 `status = runtime_error`。

### ReplayStatus

- `succeeded`
- `observed`
- `drifted`
- `failed`
- `unsupported`
- `candidate_not_found`
- `runtime_error`

### ReplayDriftStatus

- `none`
- `signature_changed`
- `target_missing`
- `page_mismatch`
- `unsupported_action`
- `no_candidate`

### Action 支持范围

本轮只支持：

- `fill`
- `click`
- `press`
- `observe`

已存 action dict 的读取字段固定为：

- `step`
- `action_type`
- `target_selector`
- `target_description`
- `value`

`step` 缺失时按 action list index 从 0 补齐。unsupported action 由 service
转成 `unsupported_action`，不能炸成 500。

## Drift 规则

1. `page_mismatch`
   - current `page_template` 与 stored `page_template` 不一致。
   - 不继续执行，`status = drifted`。
2. `signature_changed`
   - `page_template` 一致，但 `query_signature` 或 `dom_fingerprint`
     不一致。
   - selector 都能定位时允许 replay。
   - 执行成功后 `status` 仍可为 `succeeded` 或 `observed`，但
     `drift_status = signature_changed`，并写入 warning。
3. `target_missing`
   - 任一 supported 非 `observe` action 的 selector 找不到。
   - 不继续执行，`status = drifted`。
4. `unsupported_action`
   - action 类型不在支持范围内。
   - 不继续执行，`status = unsupported`。
5. `none`
   - signature 一致，并且所有目标可定位。

`actions=[]` 是合法 observational LearnedPath：

- template 一致时返回 `status = observed`。
- template 不一致时返回 `status = drifted`、
  `drift_status = page_mismatch`。
- template 一致但 signature 变化时返回 `status = observed`、
  `drift_status = signature_changed`，并附带 warning。

## 施工顺序

1. **Replay schema**：定义 request / result / status / step log contract。
2. **Candidate selection**：新增 repo 候选排序能力；不做自动候选 UI。
3. **Drift checker**：实现 signature 对比、selector 检查和 drift 结果。
4. **Shared action executor**：从 autonomous explorer 抽单步执行能力。
5. **Replay API**：新增显式 path replay endpoint。
6. **Catalog UI**：在 LearnedPath catalog drawer 里加 replay 区块。
7. **Tests and review**：补后端 / 前端测试并更新 `review.md`。

## 验证命令

实现后至少执行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_learned_paths_repo.py \
  tests/test_exploration_learned_paths_api.py \
  tests/test_learned_path_replay.py

cd apps/console && pnpm run test -- \
  LearnedPathCatalogPage exploration locales

pnpm run build:console

git diff --check
```

本迭代理论上不需要 live autonomous run。replay API 自身的浏览器执行用
service / API 测试和手工 catalog 点击验证即可。

如果执行过 live autonomous run，只能通过 `verify-scenario` skill，并在
`review.md` 里按 `pass_gate.status`、Supervisor verdict、五项 scorecard、
`run_id` 原样记录。
