# 实施计划

状态：可执行。只执行 M10 `10.1.2`，不进入 `10.2`。

## 触及的文件 / 模块

- `apps/api/app/routers/exploration.py` ——
  - 把 spec-driven run 的最终 payload 改成场景相对 verdict。
  - 去掉 history list/detail 的旧数据读取兼容。
  - 新增单条 autonomous run 删除接口。
- `apps/api/app/repos/learned_paths_repo.py` —— 如当前没有删除能力，
  增加按 `source_run_id` 删除 LearnedPath 的 repo 方法。
- `apps/api/tests/test_autonomous_run_display_verdict.py` —— 覆盖 verdict
  语义和“旧数据不兼容读取”。
- `apps/api/tests/test_exploration_learned_paths_api.py` 或新增测试文件 ——
  覆盖 DELETE 接口。
- `apps/console/src/components/autonomous/VerificationBlock.vue` ——
  确认只展示接口返回的 verdict，不做负向场景转换。
- `apps/console/src/pages/AutonomousWorkbenchPage.vue` ——
  SSE 最终 `run_completed` 到达时用最终 payload 覆盖前置机械阶段的
  self-assessment / supervisor 展示。
- `apps/console/src/utils/autonomousDisplay.ts` 与对应测试 ——
  保留 legacy 工具函数仅用于 pre-gate fallback；不再把它作为当前
  spec-driven verdict 的主语义来源。

## 后端 verdict 规则

autonomous engine 仍然先生成机械结果：

- `mechanical_verdict = "success"`：页面动作结果成功。
- `mechanical_verdict = "failure"`：页面动作结果失败，例如错误登录后
  仍停留在登录页。

当本次 run 有 spec + scenario，且 comparator 产出 `pass_gate` 后，
对外主字段改成场景相对结果：

```text
pass_gate.status == pass       -> verdict = success
pass_gate.status == fail       -> verdict = failure
pass_gate.status == unverified -> verdict = uncertain
```

要求：

- `result_snapshot_json.verdict` 存场景相对 verdict。
- `result_snapshot_json.mechanical_verdict` 保留机械 verdict。
- `result_snapshot_json.supervisor.verdict` 同步为场景相对 verdict。
- `result_snapshot_json.supervisor.mechanical_verdict` 保留原 supervisor
  机械 verdict。
- `verification.scorecard.verdict_check.self_verdict` 不改；它是
  comparator 的证据链。
- `learned_paths` ingest 仍然只看 `pass_gate.status == "pass"`。

## 删除接口设计

新增：

```http
DELETE /exploration/autonomous-runs/{run_id}
```

行为：

1. 只删除 `strategy_json.kind == "autonomous"` 的 run。
2. run 不存在：404。
3. run 存在但不是 autonomous：404 或 409。本轮建议 404，避免暴露
   非 autonomous run 细节。
4. 如果存在 `learned_paths.source_run_id == run_id`：
   - 同事务删除该 LearnedPath。
   - response 返回删除的 `learned_path_id`，便于人工确认。
5. 返回：

```json
{
  "run_id": "...",
  "deleted": true,
  "deleted_learned_path_id": "..." | null
}
```

不做：

- 不提供批量删除。
- 不按 `spec_id/scenario/verdict` 条件删除。
- 不做软删除；当前 run history 是开发期数据，单条删除足够。

## 步骤

1. 文档准备：
   - 新建本目录 `intent.md` / `plan.md` / `review.md`。
   - 在 M10 README / m10-plan 中登记 `10.1.2`。
2. 收口 verdict 语义：
   - 保留写入时转换逻辑。
   - 移除 `get_autonomous_run` 对旧 snapshot 的读取时转换。
   - 移除 list 对旧 `strategy_json.verdict` 的读取时转换。
3. 新增删除能力：
   - repo 层补 LearnedPath 按 `source_run_id` 删除。
   - router 增加 `DELETE /exploration/autonomous-runs/{run_id}`。
   - 删除 run 和关联 LearnedPath 在同一 DB transaction 内完成。
4. 前端保持薄展示：
   - `VerificationBlock` 不判断负向场景。
   - workbench final event 覆盖早期机械 verdict。
5. 测试：
   - verdict 转换测试。
   - old row 不被 list/detail 兼容转换测试。
   - DELETE 接口测试。
   - console 相关测试。
6. 删除旧数据：
   - 先列出将删除的 `run_id`、`scenario`、当前主 verdict、
     `pass_gate.status`、关联 LearnedPath。
   - 删除前请求人工确认。
   - 确认后通过 DELETE 接口删除，不直接改 DB。

## 验证

至少执行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_autonomous_run_display_verdict.py \
  tests/test_exploration_learned_paths_api.py

cd apps/api && ../../.venv/bin/ruff check \
  app/routers/exploration.py \
  app/repos/learned_paths_repo.py \
  tests/test_autonomous_run_display_verdict.py \
  tests/test_exploration_learned_paths_api.py

cd apps/console && pnpm run test -- \
  AutonomousRunDetailPage AutonomousWorkbenchPage autonomousDisplay

pnpm run build:console
git diff --check
```

手动只读验证：

1. 打开旧的 `invalid_credentials` history detail。
2. 在删除旧数据前，应能看到旧 snapshot 原样返回，不再读取时修正。
3. 新数据需要通过后续真实 run 验证；本轮代码开发不主动触发 live run。

删除验证：

1. 对人工确认的旧 `run_id` 调 DELETE 接口。
2. 再打开该 history detail，应返回 404 / 页面显示加载失败。
3. 查询 learned paths，确认关联 source run 的 LearnedPath 已删除。
