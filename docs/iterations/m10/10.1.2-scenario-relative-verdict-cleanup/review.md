# 审核与反思

## 2026-05-02 文档准备

- 用户明确调整 verdict 语义：如果是预期失败场景，且失败方式符合
  spec，那么对外主 verdict 应为 `success`；只有与预期不符才是
  `failure`。
- 用户要求去掉旧数据读取兼容，新增删除接口，然后通过接口清理旧
  数据。
- 本迭代先补 `intent.md` 和 `plan.md`，作为 `10.1` 后的 supporting
  cleanup，不进入 `10.2`。

## 收尾反思

### 实际做了什么

- 后端保留写入时的场景相对 verdict 规则：spec-driven run 的主
  `verdict` 由 `pass_gate.status` 映射，机械页面结果保存到
  `mechanical_verdict`。
- 去掉旧数据读取兼容：
  - `GET /exploration/autonomous-runs/get` 不再读取时改写旧
    `result_snapshot_json.verdict`。
  - `GET /exploration/autonomous-runs/list` 不再读取时按
    `pass_gate.status` 改写旧 `strategy_json.verdict`。
- 新增 `DELETE /exploration/autonomous-runs/{run_id}`，只删除
  autonomous run；如果该 run 已沉淀 LearnedPath，则同事务删除对应
  LearnedPath。
- 前端 `VerificationBlock` 去掉负向场景特殊判断，只展示接口返回的
  verdict。
- workbench 在最终 `run_completed` 事件到达时，用 final payload
  覆盖前面 SSE 阶段的机械 verdict，避免运行结束后仍显示早期值。

### 待删除旧数据

只读查询确认当前旧数据为：

- `run_id`: `16ecbcd3-ab1f-436d-9917-3645dfe011a9`
- `spec_id`: `login`
- `scenario`: `invalid_credentials`
- `strategy_verdict`: `failure`
- `result_verdict`: `failure`
- `pass_gate_status`: `pass`
- `learned_path_id`: `fa51d9aa-0c86-4932-94eb-019f222228fd`
- `learned_path_trust`: `provisional`

删除尚未执行；需要人工确认后通过新增 DELETE 接口删除。

### 验证命令与结果

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_autonomous_run_display_verdict.py \
  tests/test_exploration_learned_paths_api.py
# 23 passed

cd apps/api && ../../.venv/bin/ruff check \
  app/routers/exploration.py \
  app/repos/learned_paths_repo.py \
  tests/test_autonomous_run_display_verdict.py \
  tests/test_exploration_learned_paths_api.py
# All checks passed

cd apps/console && pnpm run test -- \
  AutonomousRunDetailPage AutonomousWorkbenchPage autonomousDisplay
# 15 files / 67 tests passed

pnpm run build:console
# vue-tsc --noEmit + vite build passed

git diff --check
# clean
```

### 是否触发 live autonomous run

否。本轮只改接口语义、删除接口和前端展示逻辑；未触发新的
autonomous run。
