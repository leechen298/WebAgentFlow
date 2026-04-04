# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WebAgentFlow is a monorepo for an agent-driven web workflow engine with:
- Vue 3 frontend console (`apps/console`)
- FastAPI backend API (`apps/api`)
- Python worker service (`apps/worker`)
- Chrome MV3 browser extension recorder (`apps/extension`, built with WXT)
- Shared TypeScript packages (`packages/`)

## Common Commands

### Setup & Development
```bash
# Install dependencies
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'

# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
pnpm run db:migrate:api

# Run all components
pnpm run dev             # Local development
pnpm run dev:lan         # LAN accessible (binds to 0.0.0.0)

# Run individual components
pnpm run dev:console     # Vite dev server (port 5174)
pnpm run dev:api         # Uvicorn dev server (port 8001)
pnpm run dev:worker
```

### Build, Lint, Test
```bash
# Build
pnpm run build              # Build all
pnpm run build:packages     # Build shared packages (required before console)
pnpm run build:console
pnpm run build:extension

# Lint & Format
pnpm run lint               # ESLint + Ruff
pnpm run format             # Prettier + Ruff

# Frontend tests (Vitest)
pnpm run test               # Run all console tests
pnpm run test:dev           # Watch mode
pnpm run test:coverage
pnpm run test:single        # Single file via env var

# API tests (Pytest)
cd apps/api && .venv/bin/pytest                             # All tests
cd apps/api && .venv/bin/pytest tests/test_health.py -v    # Single file
cd apps/api && .venv/bin/pytest -k "test_create" -v        # Pattern match
```

## API Architecture

The FastAPI backend (`apps/api/app/`) uses a strict layered architecture:
- **Routers** (`routers/`): HTTP endpoints only, action-based routes
- **Services** (`services/`): Business logic
- **Repositories** (`repos/`): SQLAlchemy data access
- **Models** (`models/`): ORM models with JSON columns for flexible payloads
- **Schemas** (`schemas/`): Pydantic request/response models
- **Core** (`core/`): Config (Pydantic BaseSettings), DB session, Redis, logging, exceptions

### Action-Based Routes
All endpoints use action suffixes instead of RESTful HTTP verbs:
- `POST /recordings/create`, `GET /recordings/list`, `GET /recordings/get?recording_id=...`
- `POST /recordings/update`, `POST /recordings/delete`
- Same pattern for `/skills/*` and `/runs/*`
- `GET /health` — DB connectivity check

### Response Format
All responses use an envelope: `{"code": 0, "msg": "ok", "data": {...}}`. Defined in `schemas/base.py` as `ApiResponse[T]`. The frontend axios interceptor unwraps `data` automatically.

### Database
- PostgreSQL via Docker Compose, SQLAlchemy 2.x, Alembic migrations
- All models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` (`id`, `created_at`, `updated_at`)
- JSON columns: `Recording.events`, `Recording.meta`; `Skill.definition`; `Run.input_payload`, `Run.result_payload`, `Run.logs`

## Frontend Architecture

The Vue 3 console (`apps/console/src/`) uses:
- **Router** (`router/index.ts`): All routes wrapped in `MainLayout`
- **Stores** (`stores/`): Pinia — `app.ts` (global state, API connectivity), plus per-resource stores for recordings, skills, runs
- **API client** (`api/`): Axios modules per resource; interceptor transparently unwraps `ApiResponse.data`
- Path alias `@` maps to `src/`

Frontend tests live in `src/__tests__/` using Vitest + `@vue/test-utils`. Tests using Pinia must call `setActivePinia(createPinia())` in `beforeEach`.

### API Proxy vs Direct Mode
Controlled by `VITE_USE_DEV_PROXY` in `apps/console/.env`:
- `true` — Vite proxies `/api` requests (avoids CORS, same-origin)
- `false` — Direct calls to `VITE_API_BASE_URL`; requires `CORS_ALLOWED_ORIGINS` set on API

## Extension Architecture

Built with WXT framework (`apps/extension/`):
- `entrypoints/background.ts` — Service worker (MV3)
- `entrypoints/content.ts` — Injected into pages for event capture
- `entrypoints/popup/` — Vue 3 recording UI (status, name input, start/stop)
- Recording state is persisted via extension storage

## Infrastructure

Docker Compose (`infra/docker/docker-compose.yml`) provides:
- **PostgreSQL 16** — primary database
- **Redis 7.4** — caching/queuing
- **MinIO** — object storage (ports 9000 API, 9001 console)

Copy `.env.example` to `.env` at repo root. Console has its own `apps/console/.env.example`.

## Worker

The worker (`apps/worker/app/`) runs a polling `JobRunner` loop. Currently a scaffold — heartbeat logging is implemented but job execution logic is not yet built out.
