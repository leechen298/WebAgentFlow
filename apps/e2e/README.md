# WebAgentFlow E2E

This workspace contains deterministic Playwright Test coverage for
WebAgentFlow. The first suite targets M10.2 LearnedPath replay API and catalog
UI behavior.

It does not depend on an LLM provider, does not call autonomous-run endpoints,
and does not create live autonomous runs.

## One-time Setup

Install workspace dependencies and the Playwright Test Chromium browser:

```bash
pnpm install
pnpm run test:e2e:install
```

The replay API itself uses the Python Playwright runtime. If that browser is
not installed in the API environment yet, also run:

```bash
.venv/bin/python -m playwright install chromium
```

## Start Dependencies

Run infrastructure and migrations:

```bash
pnpm run docker:up
pnpm run db:migrate:api
```

Start the three app services in separate terminals:

```bash
API_PORT=8001 pnpm run dev:api
pnpm run dev:validation
VITE_USE_DEV_PROXY=true API_PORT=8001 CONSOLE_PORT=5174 pnpm run dev:console
```

The first E2E version assumes these services are already running. It does not
use Playwright `webServer` orchestration yet.

## Seed Replay Fixtures

Seed deterministic LearnedPath fixtures:

```bash
.venv/bin/python apps/e2e/scripts/seed-replay-fixtures.py
```

The seed script:

- Deletes only rows whose `dedup_key` starts with `e2e:replay:`.
- Inserts fixed LearnedPath replay fixtures.
- Writes generated ids to `apps/e2e/.tmp/replay-fixtures.json`.
- Uses the API-side page analyzer to compute the current `/users` signature.
- Does not call `/exploration/autonomous-runs`.

Reset the E2E rows when needed:

```bash
.venv/bin/python apps/e2e/scripts/reset-e2e-db.py
```

## Run E2E

```bash
pnpm run test:e2e
pnpm run test:e2e:headed
pnpm run test:e2e:ui
```

Default service URLs:

- API: `http://127.0.0.1:8001`
- Console: `http://127.0.0.1:5174`
- Validation site: `http://127.0.0.1:5175`

Override with:

```bash
E2E_API_BASE_URL=http://127.0.0.1:8001 \
E2E_CONSOLE_BASE_URL=http://127.0.0.1:5174 \
E2E_VALIDATION_BASE_URL=http://127.0.0.1:5175 \
pnpm run test:e2e
```

## Trace Output

Traces are enabled on the first retry. On failure, inspect:

```bash
pnpm --filter @web-agent-flow/e2e exec playwright show-report
```
