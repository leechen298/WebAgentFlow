# 审核与反思

## 2026-05-02 文档准备

- 用户指出当前接口混用两种风格：
  - `GET /exploration/autonomous-runs/get?run_id=...`
  - `DELETE /exploration/autonomous-runs/{run_id}`
- 本迭代目标是把 exploration API 统一成更通行的 REST-ish 资源风格。
- 用户明确项目当前只有自己使用，不需要保留旧接口兼容。

## 收尾反思

### 实际做了什么

按 plan.md 的路由迁移表，完成了以下迁移：

| 旧路径 | 新路径 |
|---|---|
| `POST /exploration/autonomous-run` | `POST /exploration/autonomous-runs` |
| `POST /exploration/autonomous-run/stream` | `POST /exploration/autonomous-runs/stream` |
| `GET /exploration/autonomous-runs/list` | `GET /exploration/autonomous-runs` |
| `GET /exploration/autonomous-runs/get?run_id=...` | `GET /exploration/autonomous-runs/{run_id}` |
| `GET /exploration/learned-paths/list` | `GET /exploration/learned-paths` |

涉及文件：

- **后端**: `apps/api/app/routers/exploration.py` — 5 个路由装饰器改路径，
  `get_autonomous_run` 的 `run_id` 从 `Query(...)` 改为 path 参数。
- **前端 API**: `apps/console/src/api/exploration.ts` — `listAutonomousRuns`、
  `getAutonomousRun`、`listLearnedPaths` 三个函数改路径。
- **前端 SSE**: `apps/console/src/api/autonomousStream.ts` — stream URL 改路径。
- **前端 i18n**: `en.ts`、`ja.ts`、`zh.ts` — SSE raw note 文案中的旧路径。
- **前端页面**: `AutonomousRunHistoryPage.vue` — 注释中的旧路径。
- **CLI**: `apps/cli/wagent/verify.py` — POST 路径和 docstring 中的旧路径。
- **后端测试**: `test_exploration_learned_paths_api.py`、
  `test_autonomous_run_display_verdict.py` — 改为新路径，并新增 5 个旧路径 404 测试。
- **前端测试**: `exploration.test.ts` — `learned-paths/list` → `learned-paths`。
- **文档**: `CLAUDE.md`、`CLAUDE.zh.md`、`AGENTS.md`、`docs/roadmap.md`、
  `docs/roadmap.zh.md`、`docs/scope-boundaries.md`、`docs/scope-boundaries.zh.md`。

### 和 plan 的偏离点

无偏离。plan 中列出的每一项都已实现。

### 验证命令与结果

- `pytest apps/api/` — 446 passed, 65 skipped
- `ruff check` — All checks passed
- `pnpm run test` (console) — 67 passed (15 test files)
- `pnpm -w run build:console` — built in 2.59s
- `rg` 检查旧路径 — 除历史迭代文档和 404 测试外，无残留
- `git diff --check` — 无 whitespace 问题

### 是否触发 live autonomous run

未触发。

