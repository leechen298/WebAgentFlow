# 审核与反思

## 2026-05-01 draft 初始化

- 本目录最初仅作为 `10.2` 主线草案，尚未执行。
- 草案目标是消费 LearnedPath，做 replay execution 和 drift detection。

## 2026-05-02 可执行规划修订

- 复核当前代码后，将本迭代从 draft 改为可执行计划。
- 当前基础：
  - `learned_paths` 已保存 page / query / dom signature、scenario、
    actions、trust、source run。
  - `10.1.5` 已提供 LearnedPath catalog，路径级操作入口集中在
    catalog。
  - actions 当前是裁剪后的 dict，需要在 10.2 里稳定成 replay schema。
  - 单步执行逻辑仍在 `autonomous_explorer.py::_execute_step` 私有函数里，
    需要抽成共享 executor。
- 规划修订：
  - 第一版 UI 主入口放在 LearnedPath catalog，不新开复杂 workbench。
  - 第一版主打“指定某条 LearnedPath replay”，自动候选选择先做后端
    服务 / repo 能力。
  - drift 第一版不用“轻微 / 严重”这类不可证明词，而是按 page
    mismatch、signature changed、selector missing、unsupported action
    返回可解释状态。
  - replay 不调用 autonomous run 创建接口，不触发隐藏的重新学习。

## 2026-05-02 路线图重排后的定位确认

- 全局路线改为 L1/L2/L3 生命周期阶段 + M10/M11/... 交付里程碑。
- 10.2 归属 M10 Path Asset Foundation；目录名保留历史 `m10`。
- 10.2 继续可执行，不因路线图重排而推翻。
- 10.2 明确不实现 Agent D · Path Planner Agent、用户自然语言任务入口、
  slot binding、执行前确认或 Agent E 汇报；这些属于 M11
  Task-to-Path Planning MVP。
- 10.2 的 replay engine 是 M11 后续可调用的执行底座。

## 2026-05-07 可施工细化

- 将 `plan.md` 中影响实现的“建议 / 可选”收口为固定 contract。
- 固定第一版只做显式 path replay：
  `POST /exploration/learned-paths/{path_id}/replay`，request body 只含
  `url`，不做自动候选 replay API / UI。
- 固定 replay / drift status 枚举、`flaky` / `deprecated` 行为、
  action 重建规则、UI loading / error / result 三态。
- 这次只是文档细化，尚未开始实现。

## 2026-05-07 文档拆分

- 保留 `plan.md` 作为总纲 / 索引 / 核心 contract，避免 codex-review
  上下文变弱。
- 新增 `brief.md` 和 `simple.md`，分别提供极简版和通俗版。
- 新增 `steps/01` 到 `steps/07` 分步施工文档，让实现可以按 schema、
  repo、drift、executor、API、UI、测试顺序推进。
- 这次仍然只做文档整理，尚未开始实现。

## 2026-05-07 状态语义补丁

- 将 `intent.md` 中的 Agent D 引用对齐到 M11.1。
- 明确 `ReplayStatus.failed` 表示 drift precheck 未阻断但动作执行失败。
- 明确 `candidate_not_found` / `no_candidate` 只服务 candidate helper 或
  未来 M11.1 自动候选路径，显式 path replay 的 path 不存在仍是 HTTP 404。

## 2026-05-07 实现完成

### 后端新增 / 修改

| 文件 | 说明 |
|---|---|
| `apps/api/app/schemas/learned_path_replay.py` | 新建：ReplayRequest, ReplayAction, ReplayStepLog, ReplayResult, ReplayStatus, ReplayDriftStatus |
| `apps/api/app/repos/learned_paths_repo.py` | 新增 `find_replay_candidates(page_template, scenario)`，过滤排序 confirmed/provisional |
| `apps/api/app/services/learning/learned_path_replay.py` | 新建：drift checker (`run_drift_precheck`) + full replay (`run_replay`) + step-log 转换 |
| `apps/api/app/services/execution/action_executor.py` | 新建：共享单步执行器 `execute_action` / `observe_step` / `safe_screenshot`，从 autonomous_explorer 抽取 |
| `apps/api/app/services/learning/autonomous_explorer.py` | 删除旧 `_execute_step` / `_observe_step` / `_safe_screenshot`，改为 import 共享 executor |
| `apps/api/app/routers/exploration.py` | 新增 `POST /exploration/learned-paths/{path_id}/replay`，404/422/flaky warning 行为对齐文档 |
| `apps/api/app/services/learning/page_signature.py` | 新增 `build_signature_dict()`；修复 Phase 3 → M11.1 术语残留 |

### 前端新增 / 修改

| 文件 | 说明 |
|---|---|
| `apps/console/src/api/exploration.ts` | 新增 `replayLearnedPath()` 及 `ReplayResult` / `ReplayStepLog` 类型 |
| `apps/console/src/pages/LearnedPathCatalogPage.vue` | Drawer 内新增 Replay 区块：URL 输入、Replay 按钮、loading/error/result 三态、step timeline、signatures/final state |
| `apps/console/src/i18n/locales/zh.ts` / `en.ts` / `ja.ts` | 新增 20+ replay 相关 key，中文文案按“说人话”要求编写 |
| `apps/console/.eslintrc.cjs` | 关闭 `vue/no-v-model-argument`（Vue 3 合法语法） |

### 测试覆盖

后端：
- `tests/test_learned_paths_repo.py` — 20 passed（含 `find_replay_candidates` 4 个新测例）
- `tests/test_exploration_learned_paths_api.py` — 39 passed（含 replay API 5 个新测例：404、422 deprecated、422 missing url、flaky warning、valid result）
- `tests/test_learned_path_replay.py` — 17 passed（drift precheck 14 个 + `run_replay` 3 个：runtime error、success structured result、observational path）
- `tests/test_action_executor.py` — 12 passed（fill/click/press/observe/selector missing/unknown action/no page/page closed/step log fields）

前端：
- `src/__tests__/api/exploration.test.ts` — 12 passed（含 `replayLearnedPath` endpoint 测试）
- `src/__tests__/components/LearnedPathCatalogPage.test.ts` — 15 passed（含 replay input 渲染、disabled 按钮、API 调用）
- `src/__tests__/i18n/locales.test.ts` — 4 passed

### 验证命令

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_learned_paths_repo.py \
  tests/test_exploration_learned_paths_api.py \
  tests/test_learned_path_replay.py
# 76 passed

cd apps/console && pnpm run test -- --run LearnedPathCatalogPage exploration locales
# 31 passed（AutonomousUseCasesPage 既有 2 failed 与本轮无关）

pnpm run build:console
# ✓ built in 2.57s

git diff --check
# 通过
```

### 状态对齐检查

- `ReplayStatus`：succeeded / observed / drifted / failed / unsupported / candidate_not_found / runtime_error ✅
- `ReplayDriftStatus`：none / signature_changed / target_missing / page_mismatch / unsupported_action / no_candidate ✅
- replay 不调用 autonomous run 创建接口 ✅
- replay 结果不包装成 `pass_gate` 或 Supervisor verdict ✅
- drift 不返回“轻微 / 严重”等不可证明词 ✅
- `actions=[]` 返回 `observed` ✅
- `flaky` 显式 replay 允许并注入 trust warning ✅
- `deprecated` 返回 422 ✅

### 本轮明确未做

- 自动候选 replay UI / API（`candidate_not_found` / `no_candidate` 只预留枚举值）
- Agent D · Path Planner Agent
- 用户自然语言任务入口、slot binding、执行前确认
- Runtime Conversation Surface / CLI
- teaching mode、risk gate、artifact lifecycle、multi-page workflow

### 已知后续风险

- action schema 的字段名（`target_selector`、`target_description`、`value`、`step`、`action_type`）当前与 `_ACTION_KEEP_KEYS` 和 `ReplayAction` 对齐。如果后续 planner 或 ingest hook 增加/重命名字段，需要同步更新 `_build_replay_actions` 和前端类型。
- `observe` action 在 drift checker 中跳过 selector 检查，但在 executor 中仍会尝试访问 `runtime.page`。如果未来 `observe` 需要无页面上下文执行，需要单独处理。
