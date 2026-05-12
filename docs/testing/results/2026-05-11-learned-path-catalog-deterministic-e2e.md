# LearnedPath Catalog 确定性 E2E

日期：2026-05-11

Commit：`4cfbcf7c6406bd33439b0fd4b1d7e4748209bb3f`

工作区：运行验证时包含未提交的 catalog E2E 改动。

## 范围

This report covers deterministic Playwright E2E for the LearnedPath catalog page:

- catalog list
- trust filter
- actions drawer
- replay section presence
- seeded happy path replay

This is not Agent-operated UI exploratory evidence. It is headless Playwright Test
coverage under `apps/e2e/tests/replay/catalog-ui.spec.ts`.

## 命令

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/replay/catalog-ui.spec.ts
# exit 0
# 4 passed (6.8s)
```

Full-suite result is recorded after the scoped run:

```bash
pnpm run test:e2e
# exit 0
# 19 passed (14.2s)
```

## 结果

| Case | Status | Evidence |
| --- | --- | --- |
| LP-CAT-E2E-001 · Catalog 列出 seeded paths 和 trust labels | PASS | Scoped E2E test passed; confirmed, flaky, and deprecated seeded paths are visible with trust labels. |
| LP-CAT-E2E-002 · Catalog 可按 trust 过滤 | PASS | Scoped E2E test passed; selecting `Flaky` shows the flaky seeded row and excludes confirmed/deprecated sampled rows. |
| LP-CAT-E2E-003 · Drawer 展示 replay 和 actions sections | PASS | Scoped E2E test passed; `View actions` opens drawer with replay title, target URL input, disabled replay button, actions heading, and action JSON. |
| LP-CAT-E2E-004 · Catalog 可 replay seeded happy path | PASS | Scoped E2E test passed; replay result shows `Succeeded`, `No drift`, target URL, and step logs. |

## 边界

- Autonomous endpoints called: no
- `/exploration/autonomous-runs` called: no
- `/exploration/autonomous-runs/stream` called: no
- LLM provider used: no
- Product code modified: no
- E2E spec modified: yes, extended LearnedPath catalog E2E spec
- Package scripts modified: no
- Agent-operated UI exploratory performed: no

## 备注

- The first scoped run exposed test locator issues only:
  - `LearnedPath` appeared in multiple places, so the page-ready assertion was narrowed to `.learned-path-catalog .catalog-title`.
  - Ant Design trust labels render lowercase, so trust assertions are case-insensitive.
  - The catalog trust filter must target `.learned-path-catalog .ant-select-selector` to avoid the global language select.
- No product code changes were needed.
