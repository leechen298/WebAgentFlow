# Roadmap

Operational view of what's shipped, what's current, and what's next.

- For what the product **is** (three phases, seven Agents, invariants),
  see [`product-model.md`](./product-model.md). That's the authoritative
  product reference.
- For the 12-phase architectural timeline, see
  [`architecture.md`](./architecture.md) §E.

## Shipped (Phases 1–7 + exploration scaffolding)

- Page fact foundation (HTML → Full AST on server via `lxml`).
- User event recording in the extension (click, input, change, navigate,
  richtext-input), with AST association and DOM mutation tracking.
- Step building from primary event + mutations.
- Agent input contract + page / step / combined understanding (6C / 6D / 6E).
- Full execution layer (Phase 7): Playwright runtime, 6-level locator
  resolver, action executor, post-action observer.
- Task-driven exploration: TaskDefinition JSON → `run_exploration` →
  success criteria → supervisor assessment → Exploration Workbench UI
  (`/exploration`).

## Current — Phase 9: Autonomous exploration, user-driven verification

Infrastructure shipped:

- **Autonomous exploration pipeline** end-to-end
  - `page_analyzer.py` — live-page element discovery (structural only)
  - `action_planner.py` — rule-based multi-field planner, semantic-role
    matching (username / password / email / search / text)
  - `autonomous_explorer.py` — orchestrator with SSE event emitter
  - `exploration_supervisor.py` — project-internal LLM Agent (MiniMax
    M2.7, `<think>` trace preserved for transparency)
  - `page_verification.py` — spec-baseline comparator, 5 independent scores
- **Self-hosted validation-site** (`apps/validation-site/`) — index page
  cataloguing fixtures + first fixture (login) + mock `/validation-api`
  backend
- **Authored spec for login** (`specs/login.{md,assertions.json}`)
  with `valid_credentials` + `invalid_credentials` scenarios
- **Autonomous Workbench** (`/exploration/autonomous`) — user-driven UI
  with 7 blocks: run config, live SSE status, page analysis, execution
  timeline, verification (self + supervisor + scorecard), source-origin
  legend, raw SSE event audit (with copy)
- **Transparency features**: Supervisor thinking trace surfaced to UI,
  every SSE event captured in raw audit panel with copy buttons,
  click-to-preview screenshots
- **Locale-aware supervisor**: UI locale passed through to the LLM prompt
- **Docs** split into compact `CLAUDE.md` + `docs/architecture.md` +
  `docs/parser-rules.md` + `docs/scope-boundaries.md`

Closed in Phase 9 (design debts):

- [x] **Run persistence** — every autonomous run is written to
  `exploration_runs` with `strategy_json.kind = "autonomous"` plus
  `spec_id / scenario / verdict`. List + detail at
  `GET /exploration/autonomous-runs/list|get`.
- [x] **Spec-driven form prefill** — the workbench reads
  `GET /exploration/specs` on mount, populates the scenario dropdown
  from the selected spec, and replaces `fill_values` with
  `scenarios[scenario].inputs` on scenario change.
- [x] **Scenario-name de-coupling** — login scenarios renamed to
  `valid_credentials / invalid_credentials`; `VisibleOn` relaxed from a
  2-value `Literal` to free-form scenario keys.

Pending in Phase 9:

- [ ] **User verification** of the autonomous workbench on the login page
  (D1 = `valid_credentials` / D2 = `invalid_credentials`) — user drives,
  not Claude Code
- [ ] **Second fixture page** — a list / query page under
  `apps/validation-site/` with its own `specs/<page>.assertions.json`,
  so the workbench is exercised on a page that isn't login-shaped

## Next — Phase 10: Path abstraction & experience accumulation

Only after Phase 9 closes out (at least one non-login fixture passing
user review):

- **LearnedPath persistence** — approved exploration runs become
  LearnedPath rows, keyed by page signature + scenario, with provenance
  tracking.
- **Cross-page pattern mining** — detect when distinct pages share an
  action shape (login, search, CRUD).
- **Replay execution against stored paths** with drift detection
  against current page analysis.

## Further (Phases 11–12)

- Phase 11 — User correction & behavior teaching (the user edits a
  LearnedPath; the system learns what the user changed and why).
- Phase 12 — Automated evaluation & continuous optimization system
  (regression runs against the full fixture catalogue, drift alerts).

## Explicit non-goals (for current phase)

See [`scope-boundaries.md`](./scope-boundaries.md) for the canonical
list. Highlights: no CLI, no skill registry, no real-time per-step LLM
supervision, no cross-device sync.
