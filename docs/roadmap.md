# Roadmap

Operational view of what's shipped, what's current, and what's next.

- For what the product **is** (L1/L2/L3 lifecycle stages, internal
  Agents A-H, invariants),
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
  DB, and docs; at that cleanup point, `exploration_runs` was the only
  surviving table. M10 later added `learned_paths`.

No remaining Phase 9 items. The active delivery milestone is M10.

## M10 — Path Asset Foundation (in progress)

M10 focuses on making LearnedPath a reusable asset. It remains a
foundation milestone, not an L3 task runner: no runtime conversation
shell, no Agent D Path Planner, no Agent H Teaching Guide Agent, and no
task-to-path execution loop. It builds the deterministic substrate that
M11 will call.

- **LearnedPath persistence — SHIPPED 2026-04-25 (10.1)**.
  `pass_gate = pass` runs auto-ingest as `learned_paths` rows keyed
  by `(page_template, query_signature, dom_fingerprint, scenario)`,
  with a four-state trust lifecycle (`provisional` / `confirmed` /
  `flaky` / `deprecated`). Iteration record:
  [`docs/iterations/phase-10/10.1-learned-path-persistence/`](./iterations/phase-10/10.1-learned-path-persistence/).
  End-to-end evidence: `run_id=6c97c030-5aae-4f93-8abd-91c4446df9d7`
  -> `learned_path_id=31d3cf58-65a8-4298-bafc-9feee1ed6a90`,
  scorecard 5/5, supervisor source `llm`.
- **LearnedPath catalog — SHIPPED (10.1.5)**.
  The console has an asset-level LearnedPath catalog for inspecting
  paths, source runs, stored actions, and trust state. Path-level trust
  operations live in the catalog; run history keeps run review and
  read-only LearnedPath references separate.
- **Replay execution + drift detection — CURRENT (10.2)**.
  A user can pick one LearnedPath from the catalog, provide a URL, and
  ask the engine to replay the stored actions. The result is a replay
  status plus drift reasons such as page mismatch, signature changed,
  target missing, or unsupported action. This is not `pass_gate`, not a
  Supervisor verdict, and not task planning.

10.2 replay / drift results will become a future source of failure
evidence and drift evidence, but 10.2 does not need to implement a full
negative-knowledge store. M10 closes when LearnedPath can be persisted,
inspected, trusted / deprecated, and deterministically replayed with
explainable drift.

## M11.0 — Runtime Conversation Shell & Agent Orchestration

M11.0 creates the first runtime product surface for talking to
WebAgentFlow. A CLI is enough at this stage because the goal is to close
the full functional loop before polishing richer operator surfaces.

Expected delivery:

- A CLI-first runtime conversation surface where the user talks to
  **WebAgentFlow**, not directly to Agent D / E / F / G / H.
- A code-side Conversation Orchestrator / Dispatcher that maintains
  session state and routes user messages plus engine events to Agent
  D / E / F / G / H boundaries as those milestone capabilities come
  online.
- Basic messages or commands for task input, confirmation, pause,
  resume, abort, and takeover.
- State support for the M11.1 happy path, plus enough structure for M12
  recovery / abort dialogue and M13 teaching flows.
- Unified user-facing output from the WebAgentFlow point of view.

This is a runtime product entrypoint. It is not the M16 external CLI /
API surface, and it is not the current `verify-scenario` development
verification tool.

## M11.1 — Task-to-Path Planning & Execution MVP

M11.1 is the first L3 Actual Work milestone. The user describes a task
through the M11.0 conversation surface; WebAgentFlow selects and
parameterizes learned paths, executes them through the M10 replay
engine, verifies the task result as far as possible, and reports the
result.

Internal Agents introduced / made concrete:

- **Agent D · Path Planner Agent** — reads the user task plus learned
  data, selects / composes a route, binds task parameters into
  replaceable action values, and never reads raw HTML.
- **Agent E · Result Reporter Agent** — reads the execution outcome,
  postcondition checks, artifact status, and final-state signals, then
  returns a user-facing result with structured fields the UI can render.

Expected delivery:

- LearnedPath retrieval and ranking for the task.
- Slot binding: map task terms such as names, dates, statuses, export
  formats, or search terms into learned action values.
- Pre-execution confirmation when the planner's route or bound values
  are ambiguous.
- Execution through the M10 replay engine, not through autonomous
  exploration.
- Task result verification MVP: postcondition checks, artifact status,
  final-state signals, and explicit `uncertain` / `needs review`
  reporting when the result cannot be verified.
- Basic artifact capture / return for downloaded files, exports,
  screenshots, and final artifact references when the task produces
  them.
- Action risk & consent gate MVP before execution for dangerous,
  irreversible, externally sending, bulk modification, permission
  modification, or user-defined sensitive operations.

The first risk gate can be deterministic policy plus user-configurable
rules owned by the Orchestrator. Do not add a new Agent for this
milestone.

Explicit non-goals for M11.1: no hidden autonomous relearning, no
per-step LLM browser control, no full recovery dialogue beyond
returning a clear failure state and handing the session to M12-capable
flows.

## M12 — Recovery & Abort Dialogue

M12 turns failures and user aborts into first-class product flows. It
depends on the M11.0 conversation shell because recovery and abort are
runtime dialogues, not isolated execution statuses.

Internal Agents introduced / made concrete:

- **Agent F · Recovery Dialogue Agent** — explains a failed step, offers
  continue / rerun / replan / takeover / abandon options, and produces
  the next boundary action.
- **Agent G · Abort Dialogue Agent** — handles user-initiated aborts
  with continue / rerun / replan / takeover / abandon options.

Expected delivery:

- Pause-on-failure semantics for L3 execution.
- Recovery dialogue that can route to Agent D only at planning
  boundaries.
- Abort dialogue for user interruption and user-requested stop.
- Takeover handoff into M13 User Demonstration or Guided Teaching when
  automation cannot safely continue.
- Audit trail that distinguishes engine failure, user abort, recovery
  choice, and user takeover.

If M13 is not implemented yet, the M12 MVP may stop at pause +
explanation + user choice. It should not promise complete recording or
teaching-mode write-back before M13 exists.

## M13 — User-Guided Learning, Teaching & Correction

M13 implements the L2 user-guided learning path for real. It has two
sub-modes: User Demonstration and Guided Teaching.

Internal Agent introduced / made concrete:

- **Agent H · Teaching Guide Agent** — communicates the next teaching
  step, proposes highlight targets, asks clarification questions, and
  never operates the browser directly.

Expected delivery:

- Visible Playwright browser for takeover / teaching mode.
- User Demonstration recording: the user operates the page, and the
  system records real interactions, selectors, values, click targets,
  and observable state changes.
- Guided Teaching: WebAgentFlow guides the user with element highlight,
  shadow, indicator, tooltip, or next-step prompt; the user still
  performs the real click / input / selection.
- Provenance-preserving write-back into LearnedPath actions only from
  real user actions (`provenance = user`).
- Agent H suggestions remain guidance; they cannot be written directly
  as LearnedPath actions.
- Path correction UI for editing or replacing an existing LearnedPath.
- Trust updates driven by user correction and correction evidence.

## M14 — Learning Quality Agents & Coverage Expansion

M14 revisits L1 quality after the L3 happy path and handoff loop exist.
It also absorbs the earlier M10 draft backlog for richer controls,
pattern generalization, and negative knowledge.

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

Negative knowledge / failure evidence becomes formal here:

- Store failed attempts, replay drift, `target_missing`,
  `unsupported_action`, and user correction evidence.
- Feed that evidence to Agent D planning, Agent B evaluation, learning
  quality reports, and M15 automated evaluation.
- Add richer postcondition patterns and artifact verification patterns
  here or in M15, depending on implementation scope.

## M15 — Automated Evaluation & Continuous Optimization

- Regression replay for confirmed / provisional LearnedPaths against
  the fixture catalogue and selected real-page baselines.
- Failure evidence trends by page template, scenario, trust state,
  control type, and drift reason.
- Drift alerts for confirmed / provisional LearnedPaths.
- Task result verification trend tracking.
- Artifact existence and retention checks.
- Conversation, recovery, and teaching session audit.
- Data, log, screenshot, artifact, and LLM prompt-payload retention /
  cleanup policy.
- Scheduled checks that never silently rewrite paths; they create
  reviewable evidence.

## M16 — External Interfaces / Open Tooling

M16 exposes stable capability units after the main L1/L2/L3 loop is
useful. It is not the M11.0 runtime conversation CLI.

Expected delivery:

- Versioned API contracts for page learning, path planning, execution,
  verification, artifacts, and user-guided recording.
- Stable CLI commands for external schedulers, local scripting, and
  batch usage.
- Skill / Tool form for third-party Agent schedulers.
- Integration points for developer-capable users to connect
  WebAgentFlow to their own systems or operator consoles through
  CLI / API.

External Agents may schedule WebAgentFlow, but they must not replace it
with their own per-step browser automation.

## M17 — Multi-page Workflow Composition

M17 expands L3 from single-path execution to workflow composition.

Expected delivery:

- Compose multiple LearnedPaths into a larger workflow.
- Carry state across pages, such as search -> detail -> export.
- Support workflow-level recovery, takeover, and teaching mode across
  page transitions.
- Let Agent D compose already learned paths, while forbidding it from
  inventing browser paths from raw HTML.

## M18 — CLI Distribution & Integration Readiness

M18 makes the CLI / API distribution and integration story stable after
the runtime loop and workflow composition are useful.

Expected delivery:

- Stable CLI distribution.
- Docker / local packaging.
- API / CLI examples.
- Scripting and batch-usage recipes.
- Integration cookbook for connecting WebAgentFlow to user-owned
  systems or operator consoles.
- Versioned CLI / API contract and compatibility policy.

M18 does not add project-owned operator identity / tenant management,
credential storage, hosted operator-data management, commercial charging,
or usage-entitlement management.

## Explicit non-goals (for current milestone)

See [`scope-boundaries.md`](./scope-boundaries.md) for the canonical
list. Current M10.2 highlights:

- No runtime conversation shell.
- No Agent D, Agent H, or L3 task runner.
- No L3 task result verification.
- No artifact lifecycle.
- No multi-page workflow composition.
- No action risk gate.
- No project-owned operator identity, credential-vault, hosted
  operator-data, commercial charging, or usage-entitlement work.
