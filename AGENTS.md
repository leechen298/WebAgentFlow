# AGENTS.md

Guidance for Codex and other AI coding agents when working in this repository.

> **Multi-agent sync rule**: This file is kept in sync with `CLAUDE.md`
> (English, primary) and `CLAUDE.zh.md` (Chinese). Edit all three together.

## Project Overview

WebAgentFlow — monorepo for an agent-driven web workflow engine.

- `apps/console` — Vue 3 operator console.
- `apps/api` — FastAPI backend (routes, services, schemas, LLM provider).
- `apps/worker` — async worker (currently scaffold).
- `apps/validation-site` — self-hosted page fixtures for autonomous exploration.
- `apps/cli` — Python CLI (`wagent`) + the `verify-scenario` Claude Code skill.
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
`apps/api/app/services/learning/autonomous_explorer.py::_run_supervisor`,
emitting observation atoms defined in
`apps/api/app/services/learning/supervisor_observations.py`.

The app operates. The user is the operator. The AI coding agent (Codex,
Claude Code, Cursor, …) primarily writes code. The AI MAY also trigger a
run via the project-provided **`verify-scenario` skill** — but only under
the contract below. The skill invocation is auditable (it goes through the
HTTP API, persists to `exploration_runs`, emits the raw Supervisor verdict
+ scorecard), so the verification story stays intact: the app's internal
Supervisor Agent produces the verdict, and the AI merely relays it.

Running the engine via any other means — direct `curl` to
`/exploration/autonomous-run`, an inline Playwright script, importing
`run_autonomous_exploration` directly — is NOT permitted.

### MUST NOT

- Call `POST /exploration/autonomous-run` or `.../stream` via curl, fetch,
  httpx, or any HTTP client other than the `verify-scenario` skill's CLI.
- Import `run_autonomous_exploration` and drive Playwright in-process on
  the user's behalf.
- Summarise the result as "passed" / "failed" / "works" without citing the
  run's `supervisor.verdict` and the five scorecard scores verbatim.
- Omit the `run_id` when reporting back — the user needs it to look the
  run up in the WebAgentFlow console. The CLI does NOT emit a frontend
  URL; it is a backend client and doesn't know where the console lives.
- Fabricate or reshape verdicts. If the skill exits non-zero, report
  non-zero; if it exits 0, report success *with the Supervisor's own
  confidence + summary quoted*.
- Re-invoke the skill in a loop to average or "re-check" results — each
  call is a real Playwright + LLM run.

### MAY

- Read any file; run read-only diagnostics (`ruff`, `vue-tsc`, openapi
  inspection, import checks).
- Run unit / integration tests that do NOT drive
  `autonomous_explorer.run_autonomous_exploration`.
- Edit code as requested.
- **Invoke the `verify-scenario` skill** when the user's request implies a
  live run (e.g. "verify X", "run spec Y", "check workflow Z"). Forward the
  Supervisor verdict + scorecard + `run_id` to the user verbatim, plus a
  concrete analysis / next step if the verdict is not `success`.
- Ask the user to run a flow in the workbench when the skill can't help
  (e.g. the API isn't up, or manual inspection matters).

### Authoritative verification order

1. **User** — accepting or rejecting a run in `/exploration/autonomous` or
   its history detail page.
2. **Project-internal Supervisor Agent** — `_run_supervisor` LLM call +
   `page_verification` rule-based scorecard.

The AI coding agent is a **relay**, not a verifier. It does not sit on this
list. Its job when using the skill is to faithfully surface (1) + (2).

### Reporting style

When you've invoked the skill, the structure is:

**Always lead with `pass_gate.status`** — this is the authoritative
outcome. `pass` = clean; `fail` = concrete spec deviation;
`unverified` = mechanics ok but LLM didn't cross-check (NOT a pass).

Clean pass:

> "Ran `wagent verify --spec-id login --scenario valid_credentials`.
> pass_gate: `pass`. Supervisor verdict: `success` (confidence `high`,
> source `llm`). Scorecard 5/5: …. run_id: `<uuid>`."

Unverified (LLM fallback / low confidence):

> "Ran `wagent verify ...`. **pass_gate: `unverified`** (NOT a pass).
> pass_gate.reasons: "supervisor ran in fallback mode
> (error_kind=provider_error) — LLM did not independently verify this
> run". Rule mechanics 5/5 but supervisor Agent's cross-check is
> required for a real pass. run_id: `<uuid>`."

Hard fail:

> "Ran `wagent verify ...`. **pass_gate: `fail`**. pass_gate.reasons:
> "<reason>". …"

When you haven't run anything, say what changed and hand off:

> "Changed X/Y/Z. Run D1 in the workbench (or via the skill); if you see A
> the fix worked."

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
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]' -e './apps/cli'
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
  SSE event emitter, Supervisor LLM call.
- `apps/api/app/services/learning/page_analyzer.py` — live-page element
  discovery (structural classification only).
- `apps/api/app/services/learning/action_planner.py` — rule-based multi-field
  planner; semantic-role matching.
- `apps/api/app/services/learning/supervisor_observations.py` — LLM
  observation-atom schema + code-side verdict derivation.
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
- `apps/api/app/services/execution/execution_runtime.py` — Playwright
  chromium lifecycle wrapper used by autonomous_explorer.
- `apps/api/app/schemas/` — Pydantic contracts (page_analysis,
  page_verification, llm, ast, common).

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

- `POST /exploration/autonomous-run[/stream]` — run a scenario (SSE
  streaming variant is primary).
- `GET /exploration/specs[/{id}]` — spec metadata for workbench prefill.
- `GET /exploration/autonomous-runs/list|get` — persisted run history.
- `GET /exploration/screenshots/{filename}` — screenshot file server.

### Database

- PostgreSQL 16, SQLAlchemy 2.x, Alembic migrations.
- Single table: `exploration_runs` (autonomous run history). All other
  tables from the earlier product iteration have been dropped.
- `ExplorationRun` inherits `UUIDPrimaryKeyMixin` + `TimestampMixin` and
  keeps flexible payloads in JSON columns
  (`strategy_json`, `result_snapshot_json`, …).

### Frontend

- Vue 3 + Vite + vue-router + Pinia + Ant Design Vue.
- Path alias `@` → `src/`.
- Console tests in `src/__tests__/` (Vitest + `@vue/test-utils`).
- `VITE_USE_DEV_PROXY=true` — Vite proxies `/api/*` to backend (same-origin).

## See Also

- [`docs/product-model.md`](./docs/product-model.md) — **authoritative
  product model**: three phases (autonomous learning, user-guided
  learning, actual work), seven Agents, invariants. Read first.
- [`docs/architecture.md`](./docs/architecture.md) — AST dual-track,
  services sub-package structure, iframe handling.
- [`docs/scope-boundaries.md`](./docs/scope-boundaries.md) — what's
  deliberately NOT in scope for the current phase.
- [`docs/roadmap.md`](./docs/roadmap.md) — v0.1 operational milestones.
- [`docs/dev-setup.md`](./docs/dev-setup.md) — full environment setup
  walkthrough.
- [`CLAUDE.md`](./CLAUDE.md) — primary English reference.
- [`CLAUDE.zh.md`](./CLAUDE.zh.md) — Chinese mirror.
