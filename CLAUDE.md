# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WebAgentFlow is a monorepo for an agent-driven web workflow engine with:
- Vue 3 frontend console
- FastAPI backend API
- Python worker service
- Chrome MV3 browser extension recorder
- Shared TypeScript packages

The current phase (Task Pack 2) focuses on backend CRUD foundation with action-based API routes for `recordings`, `skills`, and `runs`.

## Repository Structure

```
web-agent-flow/
├── apps/
│   ├── api/          # FastAPI backend (SQLAlchemy + Alembic)
│   ├── console/      # Vue 3 frontend
│   ├── extension/    # Chrome MV3 extension (WXT)
│   └── worker/       # Python worker service
├── packages/
│   ├── sdk-js/
│   ├── shared-types/
│   └── skill-schema/
├── docs/
├── infra/docker/     # Docker Compose setup
└── .github/workflows/
```

## Common Commands

### Setup & Development
```bash
# Install dependencies
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'

# Start infrastructure
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
pnpm run db:migrate:api

# Run all components
pnpm run dev             # Local development
pnpm run dev:lan         # LAN accessible development

# Run individual components
pnpm run dev:console
pnpm run dev:api
pnpm run dev:worker
```

### Build, Lint, Test
```bash
# Build
pnpm run build              # Build all
pnpm run build:packages    # Build shared packages
pnpm run build:console     # Build Vue console
pnpm run build:extension   # Build Chrome extension

# Lint & Format
pnpm run lint              # Lint all
pnpm run format            # Format all

# API Tests
cd apps/api && pytest                     # Run all API tests
cd apps/api && pytest tests/test_health.py -v  # Run single test file
```

## API Architecture

The FastAPI backend uses a layered architecture:
- **Routers** (`apps/api/app/routers/`): Action-based endpoints (`/list`, `/create`, `/get`, `/update`, `/delete`)
- **Services** (`apps/api/app/services/`): Business logic
- **Repositories** (`apps/api/app/repos/`): Data access
- **Models** (`apps/api/app/models/`): SQLAlchemy models with UUID primary keys and timestamp mixins
- **Schemas** (`apps/api/app/schemas/`): Pydantic models for request/response validation

### API Endpoints
- `GET /health` - Health check with database connectivity
- `/recordings/*` - CRUD for recordings
- `/skills/*` - CRUD for skills
- `/runs/*` - CRUD for runs

### Database
- PostgreSQL via Docker Compose
- SQLAlchemy 2.x ORM
- Alembic migrations

## Key Patterns

### Action-Based Routes
Endpoints use `/list`, `/create`, `/get`, `/update`, `/delete` suffixes instead of RESTful HTTP verbs for all operations. Example:
- `POST /recordings/create` (not `POST /recordings`)
- `POST /recordings/update` (not `PUT /recordings/{id}`)
- `POST /recordings/delete` (not `DELETE /recordings/{id}`)

### Service-Repository Pattern
Routers depend on Services, which depend on Repositories for data access.

### Base Models
All SQLAlchemy models inherit from `UUIDPrimaryKeyMixin` and `TimestampMixin` for consistent `id`, `created_at`, and `updated_at` fields.
