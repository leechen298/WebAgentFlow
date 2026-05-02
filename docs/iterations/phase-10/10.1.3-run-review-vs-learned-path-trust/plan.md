# 实施计划

状态：**可执行**。

开工前必须重新核对当前代码、10.1.2 的最终实现和数据库迁移状态；
如果发现 10.1.2 的实现已和本文假设不一致，先更新本计划再施工。

## 模型调整

### ExplorationRun：增加 run 级人工审核

建议给 `exploration_runs` 增加字段：

```text
operator_review_status: unreviewed | accepted | rejected
operator_review_note: string | null
operator_reviewed_at: datetime | null
```

语义：

- `unreviewed`：用户尚未人工判断这次 run。
- `accepted`：用户认可这次 run 的结果和证据链。
- `rejected`：用户认为这次 run 本身有问题，例如执行路径错、页面观
  察错、Supervisor 解释错、或该 run 不应作为学习证据。

约束：

- 该状态是人工 overlay，不改 `pass_gate`、`verdict`、Supervisor
  verdict 或 scorecard。
- 该状态只属于当前 `ExplorationRun`。
- 不因为 `rejected` 自动修改 `LearnedPath.trust`。

### LearnedPath：保留路径级 trust

`LearnedPath.trust` 继续表示“这条路径未来是否值得 planner 复用”：

- `provisional`
- `confirmed`
- `flaky`
- `deprecated`

但它不再承载“某一条 run 是否被用户标错”的语义。

### Run 与 LearnedPath 的关联语义

短期不强制新增关系表。详情接口可以按当前逻辑解析：

1. 如果 `learned_paths.source_run_id == run.id`，关系为 `source`。
2. 如果 run 的 page/scenario 身份命中已有 dedup key，关系为
   `dedup_hit`。
3. 如果两者都不存在，关系为 `none`。

接口需要把这个关系显式返回给前端，而不是只返回
`learned_path_id`。

建议字段：

```json
{
  "operator_review_status": "unreviewed",
  "operator_review_note": null,
  "operator_reviewed_at": null,
  "learned_path": {
    "id": "...",
    "trust": "deprecated",
    "source_run_id": "...",
    "hit_count": 3,
    "relation": "source" | "dedup_hit"
  }
}
```

为了兼容现有前端，可以暂时保留旧字段
`learned_path_id` / `learned_path_trust`，但新 UI 应优先读
`learned_path` 对象。

## 后端 API

### 详情接口

更新：

```http
GET /exploration/autonomous-runs/get?run_id=...
```

增加：

- `operator_review_status`
- `operator_review_note`
- `operator_reviewed_at`
- `learned_path` 对象

保留：

- `pass_gate_status`
- `result`
- `strategy`
- 现有 legacy learned_path 字段（过渡期）

### Run review 接口

新增：

```http
PATCH /exploration/autonomous-runs/{run_id}/review
```

请求：

```json
{
  "status": "accepted" | "rejected" | "unreviewed",
  "note": "optional short reason"
}
```

行为：

1. 只允许操作 `strategy_json.kind == "autonomous"` 的 run。
2. run 不存在：404。
3. 更新当前 run 的 review 字段。
4. 不修改 `learned_paths`。
5. 返回更新后的 review 状态；也可以返回完整 detail projection。

### LearnedPath trust 接口

现有：

```http
PATCH /exploration/learned-paths/{path_id}/trust
```

本迭代不删除这个接口，但需要调整使用入口：

- 不再作为 history detail 的主操作。
- 如果在 history detail 保留入口，必须归入“路径级操作”区。
- 文案必须说明：这是改 LearnedPath 的未来复用信任度，不是改当前
  run review。

### 删除接口语义复核

10.1.2 新增的 run 删除接口如果仍然“删除 run 时同步删除
source LearnedPath”，本迭代需要复核这个行为。

建议新规则：

- 删除 history run 默认只删除 `ExplorationRun`。
- 如果该 run 是某条 LearnedPath 的 `source_run_id`：
  - 首选让 LearnedPath 保留，`source_run_id` 置空或保持 DB 的
    `ON DELETE SET NULL` 语义。
  - 不默认删除 LearnedPath，尤其当 `hit_count > 1` 时。
- 如果确实要删除 LearnedPath，必须通过明确的路径级删除 / 废弃操
  作完成，不由 run 删除隐式触发。

原因：LearnedPath 可能已被多个 run 命中；删除某条 history run 不
应误删共享路径数据。

## 前端调整

### History detail 主按钮

把 LearnedPath trust 操作从主按钮中移出。

主操作改为当前 run 的 review：

- `确认这次运行`
- `标记这次运行错误`

状态展示：

- `未审核`
- `已确认`
- `已标记错误`

这些状态只来自 `ExplorationRun.operator_review_status`。

### LearnedPath 区块

改成“关联 LearnedPath”信息区：

- path id
- trust tag
- source run id
- hit_count
- relation：
  - `source`：这次运行创建了这条路径
  - `dedup_hit`：这次运行命中了已有路径

文案示例：

```text
这次运行关联到一条 LearnedPath。下面显示的是未来复用路径的数据，
不是当前运行的人工审核状态。
```

路径级操作如果保留：

- 按钮文案使用 `确认路径` / `废弃路径`，不要用单独的 `确认` /
  `标记错误`。
- 弹窗必须说明“会影响未来复用，也会影响其他命中同一 LearnedPath
  的 run 页面展示”。
- disabled 状态不能再由 `a-popconfirm` 包住后仍可触发弹窗；不可操作
  时应直接渲染 disabled button，不渲染 popconfirm。

## 测试计划

### 后端

新增或更新测试：

1. `PATCH /exploration/autonomous-runs/{run_id}/review` happy path。
2. review 更新只影响当前 run，不修改 LearnedPath。
3. 两条 run 命中同一 LearnedPath：
   - 标记 `16ec...` 对应 run 为 `rejected`。
   - `ec69...` 对应 run 仍为 `unreviewed`。
   - LearnedPath trust 不变。
4. detail 接口返回 `learned_path.relation = source`。
5. detail 接口返回 `learned_path.relation = dedup_hit`。
6. 删除接口语义复核后，覆盖“删除 source run 不误删 shared
   LearnedPath”。

### 前端

新增或更新测试：

1. history detail 渲染 run review 状态。
2. 点击“确认这次运行”调用 run review API，不调用
   `patchLearnedPathTrust`。
3. 点击“标记这次运行错误”只更新当前 run review 状态。
4. LearnedPath 区块显示 relation / hit_count / source run id。
5. 路径级按钮文案与 run 级按钮不同。
6. disabled 的路径级按钮不会弹出 popconfirm。

## 验证命令

真正施工后至少执行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_exploration_learned_paths_api.py \
  tests/test_autonomous_run_display_verdict.py

cd apps/api && ../../.venv/bin/ruff check \
  app/models/exploration_run.py \
  app/routers/exploration.py \
  app/repos/learned_paths_repo.py \
  tests/test_exploration_learned_paths_api.py \
  tests/test_autonomous_run_display_verdict.py

cd apps/console && pnpm run test -- \
  AutonomousRunDetailPage AutonomousRunHistoryPage autonomousDisplay

pnpm run build:console
git diff --check
```

手动验收：

1. 打开 `16ecbcd3-ab1f-436d-9917-3645dfe011a9`。
2. 标记这次运行错误。
3. 打开 `ec69ddb7-efff-4e61-af98-d1226614d2ae`。
4. 确认 `ec69...` 没有被标记错误。
5. 确认两条 run 可以显示同一个 LearnedPath，但 run review 状态彼
   此独立。
6. 如果执行路径级废弃，确认页面文案明确说明它影响未来复用，而不
   是当前 run review。
