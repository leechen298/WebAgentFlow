# Fixture-site 确定性 E2E

日期：2026-05-11

Commit：`8ec105cc58e7800597d7ee3db5c17e5167c7fc6e`

工作区：运行验证时仅包含本任务的未提交改动。

## 范围

This report covers deterministic Playwright E2E for the fixture-site fixture pages:

- `/entry`
- `/records`

This is not Agent-operated UI exploratory evidence. It is headless Playwright Test
coverage under `apps/e2e/tests/fixture-site/browser-smoke.spec.ts`.

## 前置条件

The first sandboxed curl checks could not connect to localhost. The checks below
were re-run outside the sandbox because the local services were already listening
on their development ports.

```bash
curl -sS -i http://127.0.0.1:8001/health
# HTTP/1.1 200 OK
# {"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}

curl -sS -I https://example.invalid/entry
# HTTP/1.1 200 OK

curl -sS -I https://example.invalid/records
# HTTP/1.1 200 OK
```

## 命令

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/fixture-site/browser-smoke.spec.ts
# exit 0
# 5 passed (4.5s)
```

```bash
pnpm run test:e2e
# exit 0
# 16 passed (14.3s)
```

## 结果

| Case | Status | Evidence |
| --- | --- | --- |
| VS-E2E-001 · Login 页面渲染关键控件 | PASS | Scoped E2E test 1 passed; username, password, submit visible, no default alert. |
| VS-E2E-002 · Login 错误账号密码显示错误提示 | PASS | Scoped E2E test 2 passed; wrong/wrong shows `role=alert` and remains on `/entry`. |
| VS-E2E-003 · Users 页面渲染搜索控件和 seeded results | PASS | Scoped E2E test 3 passed; `#name-field`, `#search-status`, `#btn-apply`, result card/table, and `alice@example.com` visible. |
| VS-E2E-004 · Users 按 name 搜索会过滤结果 | PASS | Scoped E2E test 4 passed; `name=alice` updates URL and shows one-result metadata plus `alice@example.com`. |
| VS-E2E-005 · Users 无匹配搜索显示 empty state | PASS | Scoped E2E test 5 passed; `name=zzzz-no-match-9999` updates URL and shows empty-state copy. |

Full deterministic E2E also passed with the new fixture-site suite included:

```text
Running 16 tests using 5 workers
16 passed (14.3s)
```

## 边界

- Autonomous endpoints called: no
- `/exploration/autonomous-runs` called: no
- `/exploration/autonomous-runs/stream` called: no
- LLM provider used: no
- Product code modified: no
- E2E spec modified: yes, added fixture-site E2E spec
- Package scripts modified: no
- Agent-operated UI exploratory performed: no

## 备注

- API service is a prerequisite for `/entry` invalid-credential behavior and `/records` seed data.
- Fixture-site service is a prerequisite for browser navigation to `/entry` and `/records`.
- The test uses existing stable selectors (`#username`, `#password`, `#name-field`, `#search-status`, `#btn-apply`) already guarded by selector-stability smoke.
- No new `data-testid` attributes were added.
