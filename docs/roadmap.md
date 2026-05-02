# Roadmap

Operational view of what's shipped, what's current, and what's next.

- For what the product **is** (L1/L2/L3 lifecycle stages, seven
  internal Agents, invariants),
  see [`product-model.md`](./product-model.md). That's the authoritative
  product reference.
- Historical iteration folders may still be named `phase-N`, but new
  roadmap language uses **Delivery Milestone M<N>** to avoid confusing
  delivery planning with lifecycle stage L1/L2/L3.
- For the historical 12-step architectural timeline, see
  [`architecture.md`](./architecture.md) §E.

## Shipped (foundation + autonomous exploration subsystem)

Post-2026-04-20 cleanup, the only product surface in the repo is the
autonomous-Playwright pipeline. Earlier iterations (recording, Chrome
extension, task-driven exploration, skills / runs / learning-debug UI)
have been removed from the code — see
`memory/project_legacy_stack_removed.md`. For the historical 12-step
timeline, see [`architecture.md`](./architecture.md) §E.

Foundation:

- HTML → Full AST on server via `lxml` (`html_ast_parser.py`,
  `ast_simplifier.py`)
- Playwright chromium lifecycle wrapper
  (`services/execution/execution_runtime.py`)
- Self-hosted validation-site (`apps/validation-site/`) with mock
  `/validation-api` backend

Autonomous exploration pipeline (end-to-end):

- `page_analyzer.py` — live-page element discovery (structural only;
  Ant Design 5 `css-dev-only-do-not-override-<hash>` skipped in
  fallback selector)
- `action_planner.py` — rule-based multi-field planner, semantic-role
  matching (username / password / email / search / text / name / role
  / status)
- `autonomous_explorer.py` — orchestrator + SSE event emitter +
  `_run_supervisor` LLM call
- `supervisor_observations.py` — LLM observation-atom schema +
  code-side verdict derivation + `pass_gate` (`pass` / `fail` /
  `unverified`)
- `page_verification.py` — spec-baseline comparator, 5 independent
  scores
- `routers/exploration.py` — `/autonomous-runs[/stream]`,
  `/specs[/{id}]`, `/autonomous-runs[/{run_id}]`, `/screenshots/{file}`
- Persistence: every run lands in the `exploration_runs` table with
  `strategy_json.kind = "autonomous"` + `spec_id / scenario / verdict`

Operator surface:

- Autonomous Workbench (`/exploration/autonomous`) — 7 blocks:
  config / live SSE status / page analysis / execution timeline /
  verification (self + supervisor + 5-score scorecard) / origin
  legend / raw SSE audit with copy
- Run history (`/exploration/autonomous/history`) — list + per-run
  detail page reusing the workbench blocks
- Transparency: Supervisor `<think>` trace surfaced, every SSE event
  captured in raw audit, click-to-preview screenshots
- Locale-aware supervisor (UI locale forwarded to LLM prompt)
- Tri-state outcome surfaced as `pass_gate` — `pass` requires
  high-confidence LLM agreement AND clean rubric; everything else is
  `unverified` or `fail`

External entry:

- `wagent` CLI (`apps/cli/`) + `verify-scenario` Claude Code skill —
  one-shot runs against the API, supervisor verdict + scorecard +
  `run_id` returned as structured JSON

Authored specs:

- `login.{valid_credentials, invalid_credentials}`
- `users.{filter_by_name, filter_by_status, no_match}`

## Legacy delivery Phase 9 — closed 2026-04-21

Autonomous exploration, user-driven verification. Closure gate: all 5
authored scenarios re-ran on 2026-04-21 via the `verify-scenario`
skill, every one `pass_gate = pass` with supervisor source `llm` and
5/5 across the scorecard (element_recognition, action_coverage,
verdict_accuracy, distraction_avoidance, supervisor_agreement). Run
IDs live in `exploration_runs`.

Notable closures during Phase 9:

- [x] Run persistence + spec-driven workbench prefill + free-form
  scenario keys.
- [x] User verification on the login page — `valid_credentials` and
  `invalid_credentials` both green (2026-04-18).
- [x] Second fixture — `users` (user directory):
  - UI uses the full Ant Design search-form palette (text inputs,
    select, radio group, date inputs, Cascader, DatePicker,
    RangePicker, MonthPicker, TimePicker, Tag-as-filter) + Ant
    Design Table with column sort / filter.
  - Spec covers `filter_by_name`, `no_match`, `filter_by_status` —
    text input + Search plus one native inline non-text control
    (radio group) to prove the planner isn't text-only.
  - Popup-based controls (Cascader, all Picker variants, Tag filter,
    column sort / filter) are intentionally on the page but **not**
    asserted on — their scenarios moved into the M14 coverage backlog.
- [x] Tier-A polish: selector builder now skips Ant Design 5's
  `css-dev-only-do-not-override-<hash>` class; `no_match` re-verified
  after the empty-state placeholder fix.
- [x] Tier-B polish: run history page (list + detail); semantic-role
  classifier extended with `name` / `role` / `status` buckets.
- [x] Supervisor observation-atom redesign — LLM emits only
  observation atoms, verdict derived in code; `pass_gate` tri-state
  (`pass` / `fail` / `unverified`) surfaced in UI + CLI.
- [x] Legacy stack removal (2026-04-20) — recordings / skills / runs
  / Chrome extension / task-driven exploration deleted from code,
  DB, and docs; `exploration_runs` is the only surviving table.

No remaining Phase 9 items. The active delivery milestone is M10.

## M10 — Path Asset Foundation (in progress)

M10 focuses on making LearnedPath a reusable asset. It does **not**
implement L3 Actual Work yet: no user-task chat, no Agent D Path
Planner, no task-to-path execution loop. It builds the deterministic
substrate that M11 will call.

- **LearnedPath persistence — SHIPPED 2026-04-25 (10.1)**.
  `pass_gate = pass` runs auto-ingest as `learned_paths` rows keyed
  by `(page_template, query_signature, dom_fingerprint, scenario)`,
  with a four-state trust lifecycle (`provisional` / `confirmed` /
  `flaky` / `deprecated`) the operator drives via the run-detail
  page. Iteration record:
  [`docs/iterations/phase-10/10.1-learned-path-persistence/`](./iterations/phase-10/10.1-learned-path-persistence/).
  End-to-end evidence: `run_id=6c97c030-5aae-4f93-8abd-91c4446df9d7`
  → `learned_path_id=31d3cf58-65a8-4298-bafc-9feee1ed6a90`,
  scorecard 5/5, supervisor source `llm`. The product framing for
  this — engine data is instance-local, no multi-tenant columns,
  shell concerns stay outside the engine — was made explicit in
  [`product-model.md` §10.7](./product-model.md) at the same time.
- **Replay execution + drift detection — CURRENT (10.2)**.
  A user can pick one LearnedPath from the catalog, provide a URL, and
  ask the engine to replay the stored actions. The result is a replay
  status plus drift reasons such as page mismatch, signature changed,
  target missing, or unsupported action. This is not `pass_gate`, not a
  Supervisor verdict, and not task planning.

M10 closes when LearnedPath can be persisted, inspected, trusted /
deprecated, and deterministically replayed with explainable drift.

## M11 — Task-to-Path Planning & Execution MVP

M11 is the first L3 Actual Work milestone. The user describes a task in
natural language; WebAgentFlow selects and parameterizes learned paths,
executes them, and reports the result.

Internal Agents introduced / made concrete:

- **Agent D · Path Planner Agent** — reads the user task plus learned
  data, selects / composes a route, binds task parameters into
  replaceable action values, and never reads raw HTML.
- **Agent E · Result Reporter Agent** — reads the execution outcome and
  returns a user-facing result with structured fields the UI can render.

Expected delivery:

- Task input / chat-style entry for one target page or known page set.
- LearnedPath retrieval and ranking for the task.
- Slot binding: map task terms such as names, dates, statuses, export
  formats, or search terms into learned action values.
- Pre-execution confirmation when the planner's route or bound values
  are ambiguous.
- Execution through the M10 replay engine, not through autonomous
  exploration.
- User-facing result report with artifacts / final state references
  where available.

Explicit non-goals for M11: no hidden autonomous relearning, no
per-step LLM browser control, no full recovery dialogue beyond
returning a clear failure state.

## M12 — Recovery & Handoff

M12 turns failures and user aborts into first-class product flows.

Internal Agents introduced / made concrete:

- **Agent F · Recovery Dialogue Agent** — explains a failed step, offers
  re-plan / re-run / handoff options, and produces the next action.
- **Agent G · Abort Dialogue Agent** — handles user-initiated aborts
  with resume / restart / handover / drop options.

Expected delivery:

- Pause-on-failure semantics for L3 execution.
- Re-plan and re-run hooks that call Agent D only at the boundary.
- Handoff into visible-browser user-guided mode when automation cannot
  safely continue.
- Audit trail that distinguishes engine failure, user abort, and user
  takeover.

## M13 — User-Guided Learning & Correction

M13 implements the L2 user-guided learning path for real, replacing the
old extension-era recording idea with a visible Playwright browser.

Expected delivery:

- Visible-browser takeover mode.
- Recording of real user interactions: selector, value, click target,
  and observable state change.
- Provenance-preserving write-back into LearnedPath actions
  (`provenance = user`).
- Path correction UI for editing or replacing an existing LearnedPath.
- Trust updates driven by user correction.

No new product Agent is required by default. Add one only if the work
cannot fit the existing A-G roles.

## M14 — Learning Quality Agents & Coverage Expansion

M14 revisits L1 quality after the L3 happy path and handoff loop exist.
It also absorbs the earlier M10 draft backlog for richer controls
and pattern generalization.

Internal Agents introduced / made concrete:

- **Agent A · Page Intent Agent** — separate page-purpose understanding
  from Supervisor evaluation.
- **Agent B · Attempt Evaluator Agent** — keep attempt evaluation simple:
  output observations / anomalies; let code derive durable verdicts.
- **Agent C · Learning Reporter Agent** — produce a user-facing report:
  what the page is, what paths are reliable, what failed, what needs
  user teaching, and how trust states changed.

Coverage backlog moved here:

- Popup-based controls: Cascader, DatePicker, RangePicker, MonthPicker,
  table header sort / filter.
- Custom click-toggle controls: Tag-as-filter, pill filters,
  non-native checkbox / radio shapes.
- Form-label extractor expansion for Element Plus, Naive UI, Arco
  Design, TDesign, Quasar, and MUI where fixture or real-page evidence
  justifies the handler.
- Cross-page pattern mining for login / search / CRUD metadata that
  Agent D can consume later.

## M15 — Automated Evaluation & Continuous Optimization

- Regression replay against the full fixture catalogue.
- Drift alerts for confirmed / provisional LearnedPaths.
- Quality trend tracking by page template, scenario, trust state, and
  control type.
- Scheduled checks that never silently rewrite paths; they create
  reviewable evidence.

## M16 — External Interfaces / Open Tooling

Expose stable capability units after the main L1/L2/L3 loop is useful:

- API contracts for page learning, path planning, execution,
  verification, and user-guided recording.
- CLI commands for local debugging and batch execution.
- Skill / Tool form for third-party Agent schedulers.

External Agents may schedule WebAgentFlow, but they must not replace it
with their own per-step browser automation.

## Explicit non-goals (for current milestone)

See [`scope-boundaries.md`](./scope-boundaries.md) for the canonical
list. Highlights: no real-time per-step LLM supervision in L3, no
cross-device sync, and no external-Agent interface work before M16
unless explicitly reprioritized.
