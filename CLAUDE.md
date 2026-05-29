# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

> **Multi-agent sync rule**: This file is kept in sync with `CLAUDE.zh.md`
> (Chinese) and `AGENTS.md` (for Codex and other AI coding agents). Edit all
> three together.

## Project Overview

WebAgentFlow — monorepo for an agent-driven web workflow engine.

- `apps/console` — Vue 3 operator console.
- `apps/api` — FastAPI backend (routes, services, schemas, LLM provider).
- `apps/worker` — async worker (currently scaffold).
- `apps/cli` — Python CLI (`wagent`). It backs the `verify-scenario`
  development verification skill and now includes the M11.0 runtime
  conversation CLI (`wagent conversation`). M16 may later expose stable
  external CLI / Skill / Tool interfaces.
- `packages/` — shared TypeScript packages.

Fixture pages are external to this repository. Use `WAF_FIXTURE_SITE_URL` and
`WAF_PAGE_SPEC_ROOT` when running fixture-backed verification against the
standalone WebAgentFlow Fixture-Site.

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
- **M11.1 Task-to-Path Planning & Execution MVP** has completed its scoped
  path: retrieval / ranking, Task Path Planner, confirmation gate, replay
  execution, Task Result Reporter, and tests / evidence closure.
- **M11.2 Runtime Observation & Realistic Web Hardening** completed its current
  v0.1 scoped hardening track: 11.2.2 shipped step-level `wait_result`;
  11.2.3 shipped replay-level `observation_summary`; 11.2.4.x added realistic
  fixture planning / fixture shell / basic business fixture pages.
- **M11.3 Interactive Chat Productization** is closed through 11.3.7:
  `wagent chat` working runtime slices, 11.3.6 runtime eval program
  `pass_with_caveats`, and 11.3.7 first-wave user-facing behavior eval `pass`.
- M11 runtime final closeout is recorded at
  `docs/testing/results/m11-runtime-final-closeout-20260524.md`.
- M12 recovery / retry / abort / interruption has not started.
- Full learn-then-execute, page-wide automatic capability discovery, external
  black-box validation-site migration, L2 guided teaching, and Teaching Guide
  Agent (legacy: Agent H) remain future work unless a milestone document says
  otherwise.

Internal Agent naming:

- Use the primary role name in new docs and prompts.
- A-H labels are legacy aliases.
- Use the legacy alias only on first mention or when referencing older docs.
- First mention example: `Task Path Planner (legacy: Agent D)`.
- Later mentions should use `Task Path Planner`.
- Do not invent new Agent letters without updating `docs/product-model.md`
  first.

| Primary role name | Legacy alias | Lifecycle |
|---|---|---|
| Page Understanding Agent | Agent A | L1 |
| Attempt Evaluation Agent | Agent B | L1 |
| Learning Report Agent | Agent C | L1 |
| Task Path Planner | Agent D | L3 |
| Task Result Reporter | Agent E | L3 |
| Failure Recovery Agent | Agent F | L3 recovery |
| User Abort Handler | Agent G | L3 abort |
| Teaching Guide Agent | Agent H | L2 |

CLI terminology:

- Current `wagent verify` / `verify-scenario` is a development verification
  skill backend.
- M11.0 runtime conversation CLI is `wagent conversation`, where the user
  talks to WebAgentFlow through the Conversation API. The first version is a
  non-interactive session / message / transcript / events CLI.
- M16 may expose stable external CLI / Skill / Tool interfaces for external
  schedulers and integrations.
- Keep those three surfaces distinct.

Project-level Agent Skills:

- WebAgentFlow-specific coding-agent skills live in `.agents/skills/`.
- `.agents/skills/<skill-name>/SKILL.md` is the canonical source for
  project-scoped skills and should be committed with the repository.
- `.claude/skills/<skill-name>` may contain committed symlinks to
  `.agents/skills/<skill-name>` so Claude Code can discover the same skills
  without maintaining duplicate content.
- Do not keep a second skill source under `docs/agent-workflows/` or
  `.codex/skills/`.
- `.codex/` and non-skill `.claude/` contents are local tool configuration /
  state directories and remain ignored unless a future documented exception says
  otherwise.
- If Claude Code needs a personal local skill install, use a derived copy or
  symlink from `.agents/skills/`; edit the repository skill first, not the
  local copy.

Product direction: the early goal is CLI-first closure of the complete
functional loop. Developer-capable users should be able to integrate
WebAgentFlow into their own systems or operator consoles through CLI / API.

Deep architecture / history: [`docs/architecture.md`](./docs/architecture.md).

## Iteration Documentation and Implementation Gate

Use `docs/iterations/README.md` as the per-iteration documentation standard.
For detailed package-planning and review-depth rules, also use
`docs/iterations/AGENTS.md` and its Chinese mirror
`docs/iterations/AGENTS.zh.md`.

When generating development documentation for a code or mixed iteration, create
the full iteration document set from `docs/iterations/templates/` before
implementation: `README.md`, `intent.md`, `contract.md`,
`technical-design.md`, `test-plan.md`, `plan.md`, and `review.md`.
Documentation-only iterations may omit `technical-design.md` and
`test-plan.md` only when they do not prepare code implementation, but they must
still include `contract.md` if they change process rules, milestone semantics,
Agent boundaries, evidence semantics, iteration templates, concepts, statuses,
fields, or product boundaries.

When implementing code, read the current iteration documents first and
implement according to `contract.md`, reviewed `technical-design.md`,
`test-plan.md`, and `plan.md`. Do not bypass, reinterpret, or silently replace
those documents. If implementation reveals a design problem, stop and update
the relevant iteration documents first, then continue only after review.

Complex code iterations or live-run-related iterations must include
`test-plan.md`; do not claim E2E, UI smoke, CLI, `verify-scenario`, or
autonomous-run testing without reviewable evidence such as command output,
`run_id`, screenshot, log, or recorded product surface.

Milestone plans or umbrella package plans that contain multiple planned
sub-iterations must describe each planned package as a quasi-package
specification. Each planned package must state package name, status, type,
goal, why it exists, required reading, allowed changes, forbidden changes,
expected deliverables, expected tests / verification, compatibility
constraints, scope guardrails, exit criteria, and handoff to the next package.
A one-line package summary is not enough for implementation routing.

For Codex App `/goal` work that should run a whole campaign, the campaign
must provide a Campaign Goal Runner contract under the owning iteration
package. The runner must name the current state file, checkpoint fields, allowed child
package lifecycle, final status vocabulary, and live-run hard stops. Full
campaign goals may continue across child packages only after each child reaches
its documented checkpoint; stop immediately on P0 / P1 findings, insufficient
evidence, status conflicts, out-of-scope file changes, or missing live
validation approval. Keep the detailed standard in `docs/iterations/AGENTS.md`
and `docs/iterations/AGENTS.zh.md` rather than duplicating it here.

For `/goal` campaign work, coding-agent subagents are required by default.
The parent agent owns the campaign contract, checkpoint routing, integration,
verification, evidence quality, Git safety, and final status. Subagents are
execution or review workers for bounded parallel work such as codebase
exploration, disjoint implementation slices, test / log / CI triage,
iteration-doc review, or independent review axes. A checkpoint may stay
single-threaded only when there is no independent parallel work or delegation
would violate the iteration contract, sandbox, live-run boundary, evidence
rules, or Git safety rules; record that reason in the checkpoint.

## AI Coding Agent — Execution Boundary (HARD RULE)

WebAgentFlow IS an autonomous web-operation engine with its own internal
**Supervisor Agent** at
`apps/api/app/services/learning/autonomous_explorer.py::_run_supervisor`,
emitting observation atoms defined in
`apps/api/app/services/learning/supervisor_observations.py`.

The app operates. The user is the operator. The AI coding agent (Claude Code,
Codex, Cursor, …) primarily writes code, but may also act as an **external
test operator** when the user explicitly asks for UI smoke / browser
validation. In that role, the AI may operate the product's own Console UI and
report what the product returned. The AI must not pretend to be an internal
WebAgentFlow role Agent, fabricate an Agent verdict, or bypass the product's
runtime path by directly calling internal services.

Every Agent-operated validation, current or future, must leave an auditable
external-operator trail. If Codex / Claude / another AI runs a check, the
record must say which approved surface was used (`cli` or `ui`), what command
was run or what product control was operated, the working directory or page,
the raw product-client request / response log when a project CLI is involved,
and the resulting artifact / run id. The latest redacted record must be kept at
a stable repo path so it can be committed / pushed and reviewed by ChatGPT or
another Agent later. Timestamped archives may exist, but they do not replace the
stable latest copy.

The AI MAY trigger a run via the project-provided **`verify-scenario` skill**.
The skill invocation is auditable (it goes through the HTTP API, persists to
`exploration_runs`, emits the raw Supervisor verdict + scorecard), so the
verification story stays intact: the app's internal Supervisor Agent produces
the verdict, and the AI relays it.

When the user explicitly asks for live UI smoke, the AI MAY also click
first-party Console controls such as Workbench `Run` or Use Cases `Run
selected`. In that case, calls to `/exploration/autonomous-runs[/stream]` are
allowed only as product-initiated browser traffic caused by those UI controls,
and the report must say so clearly. Direct `curl`, fetch, httpx, inline service
imports, or scripts that call the autonomous-run endpoints outside the product
UI remain prohibited.

For documentation-only work or ordinary code edits that do not explicitly
request a live run, do not trigger `verify-scenario`. This repository treats
each live autonomous run as auditable product evidence, not as a casual test.

### MUST NOT

- Call `POST /exploration/autonomous-runs` or `.../stream` via curl, fetch,
  httpx, or any non-product UI HTTP client. Use the product UI or the
  `verify-scenario` skill instead.
- Treat a direct API call, one-off script, service import, or hidden HTTP
  client as an "Agent autonomous test". Agent-operated tests must go through an
  approved CLI or product UI surface and must keep the operator action log.
- Import `run_autonomous_exploration` and drive Playwright in-process on
  the user's behalf.
- Pretend to be an internal WebAgentFlow Agent such as Task Path Planner
  (legacy: Agent D), Task Result Reporter (legacy: Agent E), or Supervisor
  Agent, or return an invented internal-agent result without the product
  actually producing it.
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
- Submit or push raw Agent-operated evidence that has not been redacted, lacks
  a latest reviewable artifact, or omits the original CLI/UI operation record.

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
- Operate the first-party Console UI as an external test operator when the
  user explicitly asks for Agent-operated UI / live UI smoke. If this triggers
  `/exploration/autonomous-runs[/stream]`, report it as product-initiated UI
  traffic, include the run status / `run_id` when visible, and do not reshape
  the product's outcome.
- Run project-provided eval CLIs such as `pnpm run eval:wagent:*` or `wagent`
  commands when the requested validation belongs to that surface. The CLI must
  write `operator_actions`, raw product-client request records, redacted JSON /
  Markdown artifacts, and a stable `latest` copy before the result is treated as
  reviewable Agent-operated evidence.
- Ask the user to run a flow in the workbench when neither the skill nor
  external UI operation is appropriate (e.g. missing services, credentials, or
  manual judgment).

### Authoritative verification order

1. **User** — accepting or rejecting a run in `/exploration/autonomous` or
   its history detail page.
2. **Project-internal Supervisor Agent** — `_run_supervisor` LLM call +
   `page_verification` rule-based scorecard.

The AI coding agent is an **external test operator / relay**, not a
product-internal verifier. It does not sit on this list. Its job is to operate
approved surfaces when asked and faithfully surface (1) + (2).

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

# Run repo-local services (console + api + worker)
pnpm run dev
pnpm run dev:lan                # LAN-accessible (0.0.0.0)

# Individual components
pnpm run dev:console            # Vite dev server, port 5174
pnpm run dev:api                # Uvicorn dev server, port 8001
pnpm run dev:worker             # Python file changes auto-reload via watchfiles

# External Fixture-Site (outside this workspace)
cd /Users/leechen/projects/WebAgentFlow-Fixture-Site
pnpm dev
export WAF_FIXTURE_SITE_URL=http://127.0.0.1:5175
export WAF_PAGE_SPEC_ROOT=/path/to/WebAgentFlow-Fixture-Site/web/specs
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
- `apps/api/app/services/learning/page_verification.py` — loads authored
  baselines from the configured `WAF_PAGE_SPEC_ROOT`.
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
- M11.1 Task Path Planner / Task Result Reporter (legacy: Agent D/E),
  retrieval, confirmation, task execution, and evidence-bound reporting are
  implemented for the scoped happy path. Broad-domain slot binding, automatic
  recovery, and teaching remain future work.
- M11.3.7 first-wave user-facing WAgent behavior eval is `pass`; full
  learn-then-execute and page-wide automatic capability discovery remain
  follow-up work.
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
  `intent.md` / `contract.md` / `technical-design.md` / `test-plan.md` /
  `plan.md` / `review.md`). Write `intent.md` and the required design docs before
  starting non-trivial work; code iterations require reviewed
  `technical-design.md` before implementation.
- [`CLAUDE.zh.md`](./CLAUDE.zh.md) — Chinese mirror.
- [`AGENTS.md`](./AGENTS.md) — mirror for Codex and other AI coding agents.
