# AGENTS.md

Guidance for Codex and other AI coding agents when working in this repository.

> **Multi-agent sync rule**: This file is kept in sync with `CLAUDE.md`
> (English, primary) and `CLAUDE.zh.md` (Chinese). Edit all three together.

## Project Overview

WebAgentFlow — monorepo for an agent-driven web workflow engine.

- `apps/console` — Vue 3 operator console.
- `apps/api` — FastAPI backend (routes, services, schemas, LLM provider).
- `apps/worker` — async worker (currently scaffold).
- `apps/extension` — Chrome MV3 recorder (WXT).
- `apps/validation-site` — self-hosted page fixtures for autonomous exploration.
- `packages/` — shared TypeScript packages.

**Product model** (what WebAgentFlow actually is):
[`docs/product-model.md`](./docs/product-model.md). Read this before
proposing any new feature or phase of work. If a proposal isn't in
that document, pause and ask — don't invent a new Agent, phase, or
loop and retrofit code to it.

Deep architecture / history: [`docs/architecture.md`](./docs/architecture.md).

## AI Coding Agent — Execution Boundary (HARD RULE)

WebAgentFlow IS an autonomous web-operation engine with its own internal
**Supervisor Agent** at
`apps/api/app/services/learning/exploration_supervisor.py` +
`autonomous_explorer._run_supervisor`.

The app operates. The user is the operator. The AI coding agent (Codex,
Claude Code, Cursor, …) writes code only.

If the AI coding agent runs the app on the user's behalf and reports results,
the user cannot distinguish "the app works" from "the AI agent faked it with
scaffolding". That collapses the verification story.

### MUST NOT

- Invoke `POST /exploration/autonomous-run` or `.../stream` via curl or any
  HTTP client on the user's behalf.
- Parse the app's output and present it as evidence the app works.
- Stand in for the Supervisor Agent or the user's final review.
- Use phrasings like "I ran D1 and it passed 5/5" or "I verified end-to-end".

### MAY

- Read any file; run read-only diagnostics (`ruff`, `vue-tsc`, openapi
  inspection, import checks).
- Run unit / integration tests that do NOT drive
  `autonomous_explorer.run_autonomous_exploration`.
- Edit code as requested.
- Ask the user to run a specific flow in the workbench and report back.
- Run an autonomous exploration **only** when explicitly asked; then report
  raw observations without impersonating the app's verdict.

### Authoritative verification order

1. **User** — running the flow in `/exploration/autonomous` and accepting
   or rejecting.
2. **Project-internal Supervisor Agent** — `_run_supervisor` LLM call +
   `page_verification` rule-based scorecard.

No external AI coding tool sits on this list.

### Reporting style

Say what changed and hand off:

> "Changed X/Y/Z. Run D1 in the workbench; if you see A the fix worked."

Do NOT say:

> "I ran it, works."

## Git Safety Rules

- Branches ending in `-local` are local-only. **Never push** them.
- Before `git push`, check the current branch name. If it ends in `-local`,
  stop; if the work should be published, create or move a non-`-local`
  branch to the same commit first.

## Common Commands

### Setup & Development

```bash
# Install dependencies
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'
.venv/bin/python -m playwright install chromium   # autonomous exploration needs this

# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
pnpm run db:migrate:api

# Run everything (console + api + worker + validation-site)
pnpm run dev
pnpm run dev:lan                # LAN-accessible (0.0.0.0)

# Individual components
pnpm run dev:console            # Vite dev server, port 5174
pnpm run dev:api                # Uvicorn dev server, port 8001
pnpm run dev:worker
pnpm run dev:validation         # Validation-site fixtures, port 5175
```

### Build, Lint, Test

```bash
pnpm run build                  # all
pnpm run build:packages         # required before console build
pnpm run build:console
pnpm run build:extension

pnpm run lint                   # ESLint + Ruff
pnpm run format                 # Prettier + Ruff

pnpm run test                   # Vitest (console)
pnpm run test:dev               # watch mode
pnpm run test:coverage

cd apps/api && .venv/bin/pytest
cd apps/api && .venv/bin/pytest tests/test_health.py -v
cd apps/api && .venv/bin/pytest -k "test_create" -v
```

## Key File Locations

**Current focus — autonomous exploration subsystem:**

- `apps/api/app/services/learning/autonomous_explorer.py` — orchestrator,
  SSE event emitter.
- `apps/api/app/services/learning/page_analyzer.py` — live-page element
  discovery (structural classification only).
- `apps/api/app/services/learning/action_planner.py` — rule-based multi-field
  planner; semantic-role matching.
- `apps/api/app/services/learning/exploration_supervisor.py` —
  project-internal LLM Agent.
- `apps/api/app/services/learning/page_verification.py` — spec-baseline
  comparator; 5-score scorecard.
- `apps/api/app/routers/exploration.py` — `/exploration/autonomous-run[/stream]`
  plus `/exploration/specs[/{id}]` (spec metadata for workbench prefill)
  and `/exploration/autonomous-runs/list|get` (persisted run history).
- `apps/api/app/routers/validation_api.py` — validation-site mock backend.
- `apps/validation-site/specs/<page>.{md,assertions.json}` — authored baselines.
- `apps/validation-site/src/pages/IndexPage.vue` — fixture catalogue at `/`.
- `apps/console/src/pages/AutonomousWorkbenchPage.vue` — user-driven workbench.
- `apps/console/src/api/autonomousStream.ts` — SSE client (POST + fetch stream).

**Stable foundations:**

- `apps/api/app/services/html_ast_parser.py` — HTML → Full AST (`lxml`).
- `apps/api/app/services/execution/` — Playwright runtime, locator, action,
  observer.
- `apps/api/app/schemas/` — Pydantic contracts.

## Architecture Summary

- **Routers** (`routers/`) — HTTP endpoints only.
- **Services** (`services/`) — business logic, sub-packaged into `execution/`
  and `learning/`.
- **Repositories** (`repos/`) — SQLAlchemy data access.
- **Models** (`models/`) — ORM with JSON columns for flexible payloads.
- **Schemas** (`schemas/`) — Pydantic request / response models.
- **Core** (`core/`) — config, DB session, Redis, logging, exceptions.

### Response envelope

All responses: `{"code": 0, "msg": "ok", "data": {...}}` via
`ApiResponse[T]`. Frontend axios interceptor unwraps `data` automatically.

### Route conventions

- Action-based for CRUD: `POST /recordings/create`, `POST /recordings/update`,
  `GET /recordings/list`, `GET /recordings/get?recording_id=…`.
- REST-style for exploration: `GET /exploration/tasks`,
  `POST /exploration/run`, `POST /exploration/autonomous-run[/stream]`.

### Database

- PostgreSQL 16, SQLAlchemy 2.x, Alembic migrations.
- All models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin`.
- Flexible payloads via JSON columns (`Recording.events`, `Skill.definition`,
  `Run.result_payload`, …).

### Frontend

- Vue 3 + Vite + vue-router + Pinia + Ant Design Vue.
- Path alias `@` → `src/`.
- Console tests in `src/__tests__/` (Vitest + `@vue/test-utils`).
- `VITE_USE_DEV_PROXY=true` — Vite proxies `/api/*` to backend (same-origin).

### Extension

- WXT framework. MV3. Background + content + popup + Vue 3 popup UI.
- MutationObserver on top-level + same-origin iframes, batching at ~500ms.
- Details: [`docs/parser-rules.md`](./docs/parser-rules.md).

## See Also

- [`docs/product-model.md`](./docs/product-model.md) — **authoritative
  product model**: three phases (autonomous learning, user-guided
  learning, actual work), seven Agents, invariants. Read first.
- [`docs/architecture.md`](./docs/architecture.md) — 12-phase timeline,
  AST dual-track, services sub-package structure, iframe handling.
- [`docs/parser-rules.md`](./docs/parser-rules.md) — Initial State Parser
  (client-side DOM → StateNode) mandatory constraints.
- [`docs/scope-boundaries.md`](./docs/scope-boundaries.md) — what's
  deliberately NOT in scope for the current phase.
- [`docs/roadmap.md`](./docs/roadmap.md) — v0.1 operational milestones.
- [`docs/dev-setup.md`](./docs/dev-setup.md) — full environment setup
  walkthrough.
- [`CLAUDE.md`](./CLAUDE.md) — primary English reference.
- [`CLAUDE.zh.md`](./CLAUDE.zh.md) — Chinese mirror.
