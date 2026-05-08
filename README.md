# WebAgentFlow

WebAgentFlow is a monorepo for an agent-driven web workflow engine. It
learns reusable web-operation paths, stores them as LearnedPaths, replays
them deterministically, and reports verification / drift evidence through a
Vue console, FastAPI backend, Python CLI, worker scaffold, and Playwright
runtime.

## Current Status

The product model uses three lifecycle stages:

- **L1 Autonomous Learning** — learn page behavior from authored scenarios.
- **L2 User-Guided Learning** — planned user demonstration and guided teaching.
- **L3 Actual Work** — planned task-to-path execution from learned paths.

**M10 Path Asset Foundation** has completed. The next planned delivery
package is **M11.0 Runtime Conversation Shell & Agent Orchestration**.

- **10.1 LearnedPath persistence** — shipped.
- **10.1.5 LearnedPath catalog** — shipped.
- **10.2 Replay execution + drift detection** — shipped, with replay API,
  catalog replay UI, deterministic E2E, and a first Codex exploratory
  evidence report.

Not yet implemented:

- L2 guided teaching and Agent H Teaching Guide Agent.
- L3 task-to-path execution.
- Runtime conversation shell and Conversation Orchestrator.
- Multi-page workflow composition and full artifact lifecycle.

See [product-model.md](./docs/product-model.md), [roadmap.md](./docs/roadmap.md),
and [scope-boundaries.md](./docs/scope-boundaries.md) for the authoritative
product shape and milestone boundaries.

## Current Product Surfaces

- **Autonomous Workbench** — user-driven autonomous scenario runs with live SSE
  status, page analysis, execution timeline, Supervisor verdict, scorecard, and
  raw audit events.
- **Autonomous run history** — persisted run list and detail pages for reviewing
  previous autonomous runs.
- **LearnedPath catalog** — asset-level view of learned paths, actions, source
  runs, and trust state.
- **Validation-site fixtures** — self-hosted pages and authored specs used for
  controlled learning / verification scenarios.
- **`wagent` verify-scenario backend** — Python CLI support used by the
  `verify-scenario` skill for auditable development verification.

## CLI-First Direction

The near-term goal is to make the complete runtime loop work through CLI/API
before polishing richer operator surfaces. Developer-capable users should be
able to connect WebAgentFlow to their own systems or operator consoles through
stable CLI/API contracts.

The current `wagent verify` path is a development verification backend. The
future runtime conversation CLI belongs to M11.0, and the stable external
CLI/API surface belongs to M16.

## Roadmap Snapshot

- **M10** — Path Asset Foundation: persistence, catalog, replay, drift detection.
- **M11.0** — Runtime Conversation Shell & Agent Orchestration.
- **M11.1** — Task-to-Path Planning & Execution MVP.
- **M12** — Recovery / Abort Dialogue.
- **M13** — User-guided learning, guided teaching, and Agent H.
- **M14** — Learning quality, coverage, and negative knowledge.
- **M15** — Automated evaluation, audit, and hygiene.
- **M16** — External interfaces.
- **M17** — Multi-page workflow composition.
- **M18** — CLI distribution and integration readiness.

## Tech Stack

- **Monorepo**: pnpm workspace
- **Frontend**: Vue 3 + Vite + Pinia + Ant Design Vue
- **Backend**: FastAPI + SQLAlchemy 2.x + Alembic
- **Worker**: Python polling runner scaffold
- **CLI**: Python package (`wagent`)
- **Validation site**: Vue fixtures for controlled scenario runs
- **Browser runtime**: Playwright Chromium
- **AST pipeline**: Server-side HTML -> Full AST (`lxml`) -> verification /
  learning consumers
- **Infra**: PostgreSQL 16, Redis 7.4, MinIO (Docker Compose)
- **Python deps**: plain venv + pip

## Repository Layout

```text
web-agent-flow/
├─ apps/
│  ├─ api/
│  ├─ cli/
│  ├─ console/
│  ├─ data/
│  ├─ validation-site/
│  └─ worker/
├─ docs/
├─ examples/
├─ infra/
│  ├─ docker/
│  └─ scripts/
├─ packages/
│  ├─ sdk-js/
│  ├─ shared-types/
│  └─ skill-schema/
└─ .github/workflows/
```

## Prerequisites

- Node.js `>=20`
- pnpm `>=10`
- Python `>=3.11`
- Docker with Compose support

## Local Setup

1. Copy environment variables:

   ```bash
   cp .env.example .env
   ```

2. Install JavaScript dependencies:

   ```bash
   pnpm install
   ```

3. Create a Python virtual environment and install API / worker / CLI
   dependencies:

   ```bash
   python3.11 -m venv .venv
   .venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'
   ```

4. Install Playwright Chromium:

   ```bash
   .venv/bin/python -m playwright install chromium
   ```

5. Start local infrastructure:

   ```bash
   docker compose -f infra/docker/docker-compose.yml up -d
   ```

6. Apply API migrations:

   ```bash
   pnpm run db:migrate:api
   ```

## Configuration

### Frontend-Backend Communication

WebAgentFlow is designed to support separate frontend/backend deployment by
default:

- **Frontend** sends requests directly to the backend via `VITE_API_BASE_URL`
- **Backend** allows frontend origins via `CORS_ALLOWED_ORIGINS`

Recommended local development variables in `.env`:

```bash
# Frontend: Keep API on localhost and let Vite proxy requests
VITE_API_BASE_URL=http://localhost:8001
VITE_USE_DEV_PROXY=true

# Backend: Only needed if you disable the proxy and call API directly
CORS_ALLOWED_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
```

With this setup:

- Your Mac opens the console at `http://localhost:5174`
- Your iPad opens the console at `http://<current-mac-lan-ip>:5174`
- Both clients call `/api/*` on the console origin
- Vite proxies those requests to `http://localhost:8001` on the Mac

Optional direct API mode:

```bash
VITE_USE_DEV_PROXY=false
VITE_API_BASE_URL=http://<your-current-lan-ip>:8001
CORS_ALLOWED_ORIGINS=http://<your-current-lan-ip>:5174,http://localhost:5174,http://127.0.0.1:5174
```

## Run Apps

- Console:

  ```bash
  pnpm run dev:console
  ```

- API:

  ```bash
  pnpm run dev:api
  ```

  `GET /health` should return:

  ```json
  {
    "code": 0,
    "data": {
      "status": "ok",
      "database": "ok"
    },
    "msg": "ok"
  }
  ```

- Worker:

  ```bash
  pnpm run dev:worker
  ```

- Validation site:

  ```bash
  pnpm run dev:validation
  ```

- All services together:

  ```bash
  pnpm run dev
  ```

- All services together, LAN-accessible:

  ```bash
  pnpm run dev:lan
  ```

## Common Commands

- `pnpm run build`
- `pnpm run lint`
- `pnpm run format`
- `pnpm run test`
- `pnpm run docker:up`
- `pnpm run docker:down`

## Additional Docs

- [Product model](./docs/product-model.md)
- [Roadmap](./docs/roadmap.md)
- [Scope boundaries](./docs/scope-boundaries.md)
- [Architecture overview](./docs/architecture.md)
- [Development setup](./docs/dev-setup.md)
