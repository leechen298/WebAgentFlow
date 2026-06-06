# 技术设计（Technical Design）

状态：PACKAGE_COMPLETE

## Current State

`GET /exploration/autonomous-runs/{run_id}` already returns `result_snapshot_json` as `result`.
Console `AutonomousRunDetailPage.vue` already renders page analysis, steps, verification, review,
LearnedPath association and raw JSON.

## Implementation

- Add a compact `Evidence Summary` card to `AutonomousRunDetailPage.vue`.
- Read values directly from `detail.result.terminal_state_verdict` and
  `detail.result.attempt_ingest_evaluation`.
- Add i18n keys in `en.ts`, `zh.ts`, `ja.ts`.
- Extend component tests to cover evidence present and legacy evidence absent.
- Add or rely on API tests proving full run detail returns result evidence.

## Non-goals

- No new backend route.
- No DB migration.
- No live validation.
- No runtime ingest changes beyond child 5.

## Validation Commands

```bash
pnpm test -- AutonomousRunDetailPage
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_exploration_learned_paths_api.py apps/api/tests/test_learning_run_service.py -q
git diff --check
```
