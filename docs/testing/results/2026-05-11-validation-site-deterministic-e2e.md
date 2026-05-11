# Validation-site Deterministic E2E

Date: 2026-05-11

Commit: `8ec105cc58e7800597d7ee3db5c17e5167c7fc6e`

Working tree: uncommitted changes for this task only while running verification.

## Scope

This report covers deterministic Playwright E2E for the validation-site fixture pages:

- `/login`
- `/users`

This is not Agent-operated UI exploratory evidence. It is headless Playwright Test
coverage under `apps/e2e/tests/validation-site/browser-smoke.spec.ts`.

## Preconditions

The first sandboxed curl checks could not connect to localhost. The checks below
were re-run outside the sandbox because the local services were already listening
on their development ports.

```bash
curl -sS -i http://127.0.0.1:8001/health
# HTTP/1.1 200 OK
# {"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}

curl -sS -I http://127.0.0.1:5175/login
# HTTP/1.1 200 OK

curl -sS -I http://127.0.0.1:5175/users
# HTTP/1.1 200 OK
```

## Commands

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/validation-site/browser-smoke.spec.ts
# exit 0
# 5 passed (4.5s)
```

```bash
pnpm run test:e2e
# exit 0
# 16 passed (14.3s)
```

## Results

| Case | Status | Evidence |
| --- | --- | --- |
| VS-E2E-001 · Login page renders key controls | PASS | Scoped E2E test 1 passed; username, password, submit visible, no default alert. |
| VS-E2E-002 · Login invalid credentials shows error | PASS | Scoped E2E test 2 passed; wrong/wrong shows `role=alert` and remains on `/login`. |
| VS-E2E-003 · Users page renders search controls and seeded results | PASS | Scoped E2E test 3 passed; `#search-name`, `#search-status`, `#btn-search`, result card/table, and `alice@example.com` visible. |
| VS-E2E-004 · Users search by name filters results | PASS | Scoped E2E test 4 passed; `name=alice` updates URL and shows one-result metadata plus `alice@example.com`. |
| VS-E2E-005 · Users no-match search shows empty state | PASS | Scoped E2E test 5 passed; `name=zzzz-no-match-9999` updates URL and shows empty-state copy. |

Full deterministic E2E also passed with the new validation-site suite included:

```text
Running 16 tests using 5 workers
16 passed (14.3s)
```

## Boundaries

- Autonomous endpoints called: no
- `/exploration/autonomous-runs` called: no
- `/exploration/autonomous-runs/stream` called: no
- LLM provider used: no
- Product code modified: no
- E2E spec modified: yes, added validation-site E2E spec
- Package scripts modified: no
- Agent-operated UI exploratory performed: no

## Notes

- API service is a prerequisite for `/login` invalid-credential behavior and `/users` seed data.
- Validation-site service is a prerequisite for browser navigation to `/login` and `/users`.
- The test uses existing stable selectors (`#username`, `#password`, `#search-name`, `#search-status`, `#btn-search`) already guarded by selector-stability smoke.
- No new `data-testid` attributes were added.
