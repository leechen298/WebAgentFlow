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
- `apps/cli` — Python CLI (`wagent`). It backs the `verify-scenario`
  development verification skill and now includes the M11.0 runtime
  conversation CLI (`wagent conversation`). M16 may later expose stable
  external CLI / Skill / Tool interfaces.
- `packages/` — shared TypeScript packages.

**Product model** (what WebAgentFlow actually is):
[`docs/product-model.md`](./docs/product-model.md). Read this before
proposing any new feature or delivery milestone. If a proposal isn't in
that document, pause and ask — don't invent a new Agent, lifecycle stage,
or loop and retrofit code to it.

Current planning vocabulary:

- Product lifecycle stages are **L1 / L2 / L3**.
- Delivery milestones are **M10 / M11 / ...**.
- Use **L<N>** for lifecycle stages and **M<N>** for delivery milestones.
- Milestone iteration folders use `docs/iterations/m<N>/`.

Current delivery status:

- **M10 Path Asset Foundation** has completed.
- **10.1 LearnedPath persistence**, **10.1.5 LearnedPath catalog**, and
  **10.2 replay execution + drift detection** have shipped.
- **M11.0 Runtime Conversation Shell & Agent Orchestration** has completed
  through 11.0.7.
- 11.1.1 Task Planning Domain Contract shipped: 17 schema definitions,
  24 tests passed (`apps/api/app/schemas/task_planning.py`).
- Current delivery package: **11.1.2 LearnedPath Retrieval and Ranking**
  within **M11.1 Task-to-Path Planning & Execution MVP**.
- M11.1 planning continues. 11.1.1 defined task / candidate / route / binding /
  verification contracts; 11.1.2 implements retrieval. Task Path Planner /
  Task Result Reporter (legacy: Agent D/E), slot binding, replay execution,
  and result verification remain future work.
- Agent routing, L3 task runner, L2 guided teaching, and Teaching Guide Agent
  (legacy: Agent H) are planned future work, not current implementation.

Internal Agent naming:

- Prefer functional role names in new docs.
- A-H labels are legacy aliases.
- First mention example: `Task Path Planner (legacy: Agent D)`.
- Later mentions should use `Task Path Planner`.

CLI terminology:

- Current `wagent verify` / `verify-scenario` is a development verification
  skill backend.
- M11.0 runtime conversation CLI is `wagent conversation`, where the user
  talks to WebAgentFlow through the Conversation API. The first version is a
  non-interactive session / message / transcript / events CLI.
- M16 may expose stable external CLI / Skill / Tool interfaces for external
  schedulers and integrations.
- Keep those three surfaces distinct.

Product direction: the early goal is CLI-first closure of the complete
functional loop. Developer-capable users should be able to integrate
WebAgentFlow into their own systems or operator consoles through CLI / API.

Deep architecture / history: [`docs/architecture.md`](./docs/architecture.md).

## AI Coding Agent — Execution Boundary (HARD RULE)

WebAgentFlow IS an autonomous web-operation engine with its own internal
**Supervisor Agent** at
`apps/api/app/services/learning/autonomous_explorer.py::_run_supervisor`,
emitting observation atoms defined in
`apps/api/app/services/learning/supervisor_observations.py`.

The app operates. The user is the operator. The AI coding agent (Claude Code,
Codex, Cursor, …) primarily writes code. The AI MAY also trigger a run via the
project-provided **`verify-scenario` skill** — but only under the contract
below. The skill invocation is auditable (it goes through the HTTP API,
persists to `exploration_runs`, emits the raw Supervisor verdict +
scorecard), so the verification story stays intact: the app's internal
Supervisor Agent produces the verdict, and the AI merely relays it.

Running the engine via any other means — direct `curl` to
`/exploration/autonomous-runs`, an inline Playwright script, importing
`run_autonomous_exploration` directly — is NOT permitted.

For documentation-only work or ordinary code edits that do not explicitly
request a live run, do not trigger `verify-scenario`. This repository treats
each live autonomous run as auditable product evidence, not as a casual test.

### MUST NOT

- Call `POST /exploration/autonomous-runs` or `.../stream` via curl, fetch,
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

**Always lead with `pass_gate.status`** — this is the authoritative
outcome. A spec run is a "pass" only when the gate says `pass`.
`unverified` is NOT a pass.

Clean pass:

> "Ran the `verify-scenario` skill
> (`wagent verify --spec-id login --scenario valid_credentials`).
> pass_gate: `pass`. Supervisor verdict: `success` (confidence `high`,
> source `llm`). Scorecard 5/5: element_recognition 1.0,
> action_coverage 1.0, verdict_accuracy 1.0, distraction_avoidance 1.0,
> supervisor_agreement 1.0. Supervisor summary: …quoted…. run_id:
> `<uuid>` — open at `/exploration/autonomous/history/<run_id>`."

Unverified (e.g. MiniMax overloaded, LLM fallback fired):

> "Ran `wagent verify --spec-id users --scenario filter_by_status`.
> **pass_gate: `unverified`** (NOT a pass). pass_gate.reasons:
> "supervisor ran in fallback mode (error_kind=provider_error) — LLM
> did not independently verify this run". The rule side saw
> scenario_matched=true and 5/5 mechanics clean, but the supervisor
> Agent's cross-check is required for a real pass. run_id: `<uuid>`."

Unverified (LLM low confidence):

> "Ran `wagent verify --spec-id login --scenario invalid_credentials`.
> **pass_gate: `unverified`**. pass_gate.reasons: "supervisor
> confidence=medium — scenario requires high-confidence LLM agreement".
> Supervisor could not verify that `role=alert` surfaced because the
> prompt didn't carry enough signal. …"

Hard fail (spec deviation):

> "Ran `wagent verify --spec-id X --scenario Y`. **pass_gate: `fail`**.
> pass_gate.reasons: "element recognition score 0.67 < 1.0 — one or
> more critical elements missing or mis-classified". …"

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
pnpm run dev:worker             # Python file changes auto-reload via watchfiles
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

**Current focus — M11 runtime conversation and task planning foundation:**

- `apps/api/app/schemas/conversation.py` — M11.0 conversation enums,
  domain contracts, and API request / response schemas.
- `apps/api/app/models/conversation.py` — DB-backed conversation session,
  message, and event ORM models.
- `apps/api/app/repos/conversation_repo.py` — conversation session / message /
  event repository.
- `apps/api/app/services/conversation/commands.py` — pure slash-command
  parser contract.
- `apps/api/app/services/conversation/state.py` — pure conversation state
  transition contract.
- `apps/api/app/routers/conversation.py` — Conversation API endpoints.
- `apps/api/app/services/conversation/orchestrator.py` — M11.0.5
  Conversation Orchestrator / Dispatcher service skeleton.
- `apps/cli/wagent/conversation.py` — `wagent conversation` runtime
  conversation CLI.
- `apps/cli/tests/test_conversation.py` — CLI regression tests.
- `apps/api/app/schemas/task_planning.py` — planned M11.1 task-to-path
  planning domain contract (`11.1.1`; shipped).

**Autonomous exploration + M10 path assets:**

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
- `apps/api/app/models/learned_path.py` — M10.1 LearnedPath ORM model.
- `apps/api/app/repos/learned_paths_repo.py` — LearnedPath persistence,
  catalog, trust, and lookup data access.
- `apps/api/app/services/learning/page_signature.py` — LearnedPath identity
  helpers (`path_template`, `query_signature`, `dom_fingerprint`).
- `apps/api/app/routers/exploration.py` — `/exploration/autonomous-runs[/stream]`
  plus `/exploration/specs[/{id}]` (spec metadata for workbench prefill)
  and `/exploration/autonomous-runs[/{run_id}]` (persisted run history), plus
  LearnedPath catalog routes.
- `apps/api/app/routers/validation_api.py` — validation-site mock backend.
- `apps/validation-site/specs/<page>.{md,assertions.json}` — authored baselines.
- `apps/validation-site/src/pages/IndexPage.vue` — fixture catalogue at `/`.
- `apps/console/src/pages/AutonomousWorkbenchPage.vue` — user-driven workbench.
- `apps/console/src/pages/LearnedPathCatalogPage.vue` — M10.1.5 LearnedPath
  catalog UI.
- `apps/console/src/api/autonomousStream.ts` — SSE client (POST + fetch stream).

**Stable foundations:**

- `apps/api/app/services/html_ast_parser.py` — HTML → Full AST (`lxml`).
- `apps/api/app/services/execution/execution_runtime.py` — Playwright
  chromium lifecycle wrapper used by autonomous_explorer.
- `apps/api/app/schemas/` — Pydantic contracts (page_analysis,
  page_verification, llm, ast, common).

**Planned / partially implemented service areas:**

- Conversation domain / store / API / CLI / Orchestrator service skeleton,
  explicit replay hook, public dispatch endpoint, CLI dispatch integration,
  and conversation runtime E2E are implemented through M11.0.7.
- M11.1 task planning domain schemas shipped in 11.1.1 (24 tests). Task Path
  Planner / Task Result Reporter (legacy: Agent D/E), retrieval, slot
  binding, task execution, result verification, confirmation, recovery, and
  teaching remain future work.
- L2 teaching support, highlight targets, and user action recording.
- Artifact lifecycle handling.
- Failure evidence / negative knowledge.

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

- `POST /exploration/autonomous-runs[/stream]` — run a scenario (SSE
  streaming variant is primary).
- `GET /exploration/specs[/{id}]` — spec metadata for workbench prefill.
- `GET /exploration/autonomous-runs[/{run_id}]` — persisted run history.
- `GET /exploration/screenshots/{filename}` — screenshot file server.

### Database

- PostgreSQL 16, SQLAlchemy 2.x, Alembic migrations.
- Core tables currently include at least `exploration_runs` and
  `learned_paths`.
- `exploration_runs` stores autonomous run history.
- `learned_paths` is the M10.1 path asset table for reusable learned actions
  and trust state.
- Keep `learned_paths` as a path-asset table. Do not add new ownership,
  scope, or roadmap-external columns unless the product model changes first.
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
  product model**: L1/L2/L3 lifecycle stages (autonomous learning,
  user-guided learning, actual work), internal role Agents with A-H legacy
  aliases, invariants. Read first.
- [`docs/architecture.md`](./docs/architecture.md) — AST dual-track,
  services sub-package structure, iframe handling.
- [`docs/scope-boundaries.md`](./docs/scope-boundaries.md) — what's
  deliberately NOT in scope for the current delivery milestone.
- [`docs/roadmap.md`](./docs/roadmap.md) — v0.1 operational milestones.
- [`docs/dev-setup.md`](./docs/dev-setup.md) — full environment setup
  walkthrough (more detailed than the Common Commands above, useful
  for new contributors).
- [`docs/iterations/README.md`](./docs/iterations/README.md) —
  **per-iteration doc convention** (milestone-scoped folders with
  `intent.md` / `plan.md` / `review.md`). Write `intent.md` before
  starting non-trivial work; the `codex-review` skill reads these as
  context.
- [`CLAUDE.md`](./CLAUDE.md) — primary English reference.
- [`CLAUDE.zh.md`](./CLAUDE.zh.md) — Chinese mirror.
