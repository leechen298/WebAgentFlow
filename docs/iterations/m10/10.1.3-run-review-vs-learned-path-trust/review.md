# 审核与反思

## 2026-05-02 实现完成

### 实际做了什么

1. **数据库模型与迁移**
   - 新增迁移 `20260502_0001_add_run_operator_review.py`，为 `exploration_runs` 表增加三列：
     - `operator_review_status` (`unreviewed` | `accepted` | `rejected`)
     - `operator_review_note`
     - `operator_reviewed_at`
   - `ExplorationRun` ORM 新增 `OperatorReviewStatus` StrEnum 和对应字段。

2. **后端 API**
   - `GET /exploration/autonomous-runs/{run_id}` 现在返回：
     - `operator_review_status` / `operator_review_note` / `operator_reviewed_at`
     - `learned_path` 对象（含 `id`, `trust`, `source_run_id`, `hit_count`, `relation`）
     - 保留旧的 `learned_path_id` / `learned_path_trust` 作为过渡期兼容
   - 新增 `PATCH /exploration/autonomous-runs/{run_id}/review`
     - 只允许 `autonomous` kind 的 run
     - 只修改当前 run，不触碰 `learned_paths`
   - 修改 `DELETE /exploration/autonomous-runs/{run_id}`
     - 不再隐式删除关联的 LearnedPath（即使它是 `source_run_id`）
     - 返回的 `deleted_learned_path_ids` 始终为空列表
   - 新增内部辅助 `_learned_path_relation_for_run`，区分 `source` / `dedup_hit` / `none`。

3. **前端**
   - `AutonomousRunDetailPage.vue` 拆分为两个独立区块：
     - **Run review**（主操作）：`确认这次运行` / `标记这次运行错误`，只改 run review
     - **LearnedPath**（关联信息）：只读展示 path id、trust、relation、hit_count、source_run_id；路径级操作 `确认路径` / `废弃路径` 保留在单独区域
   - `exploration.ts` 新增 `patchRunReview` 和 `RunLearnedPathProjection` / `OperatorReviewStatus` 类型。
   - i18n（en / zh / ja）同步更新所有新键和修改的文案。

4. **测试**
   - 后端新增 8 个测试：
     - review accept / reject / 不修改 LearnedPath / 404 / non-autonomous 404 / 非法 status 422
     - detail 返回 `relation=source` 和 `relation=dedup_hit`
     - detail 返回 operator review 字段
   - 更新 delete 测试：验证 run 被删但 LearnedPath 保留。
   - 前端测试全面重写：
     - Run review block：渲染、accept、reject、disabled 状态
     - LearnedPath block：按钮文案改为 "Confirm path" / "Deprecate path"、promote / deprecate、disabled 状态、absence copy

### 和 plan 的偏离点

- plan 建议保留旧字段 `learned_path_id` / `learned_path_trust`；实际保留了。
- plan 提到 "如果保留 LearnedPath trust 修改入口，必须放在单独的'路径级操作'区域"；实际保留了，且文案已更新为明确区分。
- 没有新增 run-to-LearnedPath 关系表；继续采用 read-time `_learned_path_relation_for_run` 投影，符合 plan 的短期方案。

### 验证命令与结果

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_exploration_learned_paths_api.py \
  tests/test_autonomous_run_display_verdict.py
# 38 passed

cd apps/api && ../../.venv/bin/ruff check \
  app/models/exploration_run.py \
  app/routers/exploration.py \
  app/repos/learned_paths_repo.py \
  tests/test_exploration_learned_paths_api.py \
  tests/test_autonomous_run_display_verdict.py
# All checks passed

cd apps/console && pnpm run test -- \
  AutonomousRunDetailPage AutonomousRunHistoryPage autonomousDisplay
# 72 passed

pnpm run build:console
# built successfully

git diff --check
# clean
```

### Codex 复核后的收尾修复

1. **文档索引同步**
   - `docs/iterations/m10/README.md` 主线清单和执行包索引补充了
     `10.1.2` / `10.1.3` / `10.1.4`，标记为已完成。
   - `docs/iterations/m10/m10-plan.md` 硬边界中的旧路径
     `/exploration/autonomous-run` 改为 `/exploration/autonomous-runs`，
     避免后续 Agent 引用已废弃接口。

2. **API 语义细化**
   - `PATCH /exploration/autonomous-runs/{run_id}/review` 当
     `status == "unreviewed"` 时，现在会清空 `operator_reviewed_at`
     为 `None`，而不是继续写入当前时间。
   - 新增测试 `test_patch_run_review_to_unreviewed_clears_reviewed_at`
     覆盖此行为。

### 是否触发 live autonomous run

否。本轮只涉及数据模型、API 契约和前端 UI 调整，没有修改浏览器执行策略，也没有触发 autonomous run。
