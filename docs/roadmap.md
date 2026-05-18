# Roadmap

Operational view of what's shipped, what's current, and what's next.

- For what the product **is** (L1/L2/L3 lifecycle stages, internal
  role Agents with A-H as legacy aliases, invariants),
  see [`product-model.md`](./product-model.md). That's the authoritative
  product reference.
- Iteration folders use milestone names such as `docs/iterations/m10/`.
  Roadmap language uses **Delivery Milestone M<N>** to avoid confusing
  delivery planning with lifecycle stage L1/L2/L3.
- For the historical 12-step architectural timeline, see
  [`architecture.md`](./architecture.md) §E.

## Release Status

- **v0.1**: first working task-to-path MVP; release closeout prepared. See
  [`docs/releases/v0.1.md`](./releases/v0.1.md).
- **v0.2**: planned; failure recovery / abort / runtime robustness.

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

## Legacy Delivery M9 — closed 2026-04-21

Autonomous exploration, user-driven verification. Closure gate: all 5
authored scenarios re-ran on 2026-04-21 via the `verify-scenario`
skill, every one `pass_gate = pass` with supervisor source `llm` and
5/5 across the scorecard (element_recognition, action_coverage,
verdict_accuracy, distraction_avoidance, supervisor_agreement). Run
IDs live in `exploration_runs`.

Notable closures during M9:

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

No remaining M9 items. M10 is now closed; the next delivery milestone is
M11.0.

## M10 — Path Asset Foundation (completed 2026-05-08)

M10 made LearnedPath a reusable asset. It remained a foundation
milestone, not an L3 task runner: no runtime conversation shell, no
Task Path Planner (legacy: Agent D), no Teaching Guide Agent (legacy: Agent H), and no
task-to-path execution loop. It built the deterministic substrate that
M11 will call.

- **LearnedPath persistence — SHIPPED 2026-04-25 (10.1)**.
  `pass_gate = pass` runs auto-ingest as `learned_paths` rows keyed
  by `(page_template, query_signature, dom_fingerprint, scenario)`,
  with a four-state trust lifecycle (`provisional` / `confirmed` /
  `flaky` / `deprecated`). Iteration record:
  [`docs/iterations/m10/10.1-learned-path-persistence/`](./iterations/m10/10.1-learned-path-persistence/).
  End-to-end evidence: `run_id=6c97c030-5aae-4f93-8abd-91c4446df9d7`
  -> `learned_path_id=31d3cf58-65a8-4298-bafc-9feee1ed6a90`,
  scorecard 5/5, supervisor source `llm`.
- **LearnedPath catalog — SHIPPED (10.1.5)**.
  The console has an asset-level LearnedPath catalog for inspecting
  paths, source runs, stored actions, and trust state. Path-level trust
  operations live in the catalog; run history keeps run review and
  read-only LearnedPath references separate.
- **Replay execution + drift detection — SHIPPED / completed 2026-05-08 (10.2)**.
  A user can pick one LearnedPath from the catalog, provide a URL, and
  ask the engine to replay the stored actions. The result is a replay
  status plus drift reasons such as page mismatch, signature changed,
  target missing, or unsupported action. This is not `pass_gate`, not a
  Supervisor verdict, and not task planning.

M10 closed with LearnedPath persisted, cataloged, trusted / deprecated,
explicitly replayed, and drift-explained. Deterministic E2E is in place
and passed (`pnpm run test:e2e`, 9 passed). Codex exploratory validation
has a first evidence report (`PASS 12 / FAIL 0 / BLOCKED 0 / NOT_RUN 4`).
10.2 replay / drift results will become a future source of failure
evidence and drift evidence, but 10.2 did not implement a full
negative-knowledge store.

As of the v0.1 closeout, M11.0 and M11.1 have completed through
`11.1.8-task-to-path-tests-and-evidence`. The branch is being prepared as the
first working task-to-path MVP, not as a released/tagged artifact yet.

## M11.0 — Runtime Conversation Shell & Agent Orchestration

M11.0 creates the first runtime product surface for talking to
WebAgentFlow. A CLI is enough at this stage because the goal is to close
the full functional loop before polishing richer operator surfaces.

Iteration docs:
[`docs/iterations/m11/11.0-runtime-conversation-shell-orchestration/`](./iterations/m11/11.0-runtime-conversation-shell-orchestration/).

Progress:

- 11.0.1 Conversation Domain Contract shipped: schemas, slash-command
  parser, and pure state transitions (`29 passed`).
- 11.0.2 Conversation Session Store shipped and hardened: DB-backed
  sessions, messages, events, repository validation (`61 passed`).
- 11.0.3 Conversation API shipped: seven `/conversation/...` endpoints
  (`84 passed`).
- 11.0.4 Runtime CLI Shell shipped: non-interactive `wagent conversation`
  commands for session, message, transcript, and events (`67 passed`).
- 11.0.5 Orchestrator Dispatcher shipped: service-only dispatcher skeleton
  with `dispatch_user_input` and `dispatch_engine_event` placeholder
  (`101 passed`). No replay hook, no new CLI commands, no new HTTP endpoints.
- 11.0.6 Explicit Replay Command Hook shipped: Orchestrator replay handler
  protocol, `run_explicit_replay` bridge to M10 replay engine,
  `POST /conversation/sessions/{id}/dispatch` endpoint, CLI `send` routed
  through dispatch (`179 passed` API + `67 passed` CLI).
- 11.0.7 Conversation Tests and Evidence shipped: conversation runtime E2E
  smoke plus fresh replay / conversation evidence (`10 passed` E2E).
- M11.0 execution packages are complete.

Expected delivery:

- A CLI-first runtime conversation surface where the user talks to
  **WebAgentFlow**, not directly to Task Path Planner / Task Result Reporter / Failure Recovery Agent / User Abort Handler / Teaching Guide Agent (legacy: Agents D-H).
- A code-side Conversation Orchestrator / Dispatcher that maintains
  session state and routes user messages plus engine events to Task Path
  Planner, Task Result Reporter, Failure Recovery Agent, User Abort Handler,
  and Teaching Guide Agent boundaries as those milestone capabilities come
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

M11.1 is complete for the v0.1 release closeout through
`11.1.8-task-to-path-tests-and-evidence`. It connects natural-language task
input to LearnedPath retrieval / ranking, Task Path Planner preview,
confirmation, deterministic replay execution, and Task Result Reporter output.

Internal Agents introduced / made concrete:

- **Task Path Planner (legacy: Agent D)** — reads the user task plus learned
  data, selects / composes a route, binds task parameters into
  replaceable action values, and never reads raw HTML.
- **Task Result Reporter (legacy: Agent E)** — reads the execution outcome,
  postcondition checks, artifact status, and final-state signals, then
  returns a user-facing result with structured fields the UI can render.

Delivered for v0.1 closeout:

- 11.1.1 Task Planning Domain Contract.
- 11.1.2 LearnedPath Retrieval and Ranking.
- 11.1.3 Task Path Planner MVP.
- 11.1.4 Task Planning Dispatch Preview.
- 11.1.5 Plan Confirmation and Consent Gate.
- 11.1.6 Execution via Replay.
- 11.1.7 Result Verification and Task Result Reporter.
- 11.1.8 Task-to-path Tests and Evidence (`1104` API tests passed,
  `25` E2E passed, ruff clean, no unresolved P1/P2).

The v0.1 shipped chain is:

```text
TaskInput -> LearnedPath retrieval / ranking -> Task Path Planner
-> planning preview -> confirmation -> replay execution
-> Task Result Reporter
```

Current boundaries:

- Slot Binding remains future scope.
- `replay completed` does not mean `task succeeded`.
- Missing postcondition evidence returns `uncertain` / `needs review`.
- Failed / blocked execution does not trigger automatic recovery or hidden
  relearning.

Explicit non-goals for M11.1: no hidden autonomous relearning, no
per-step LLM browser control, no full recovery dialogue beyond
returning a clear failure state and handing the session to M12-capable
flows.

## M11.2 — 运行时观察与真实网页稳健性增强

M11.2 是 v0.1 后续稳健性增强轨道。它不重新展开 task-to-path planning，
也不启动 v0.2 / M12。它的目标是在 replay 周围定义并后续实现 observation
layer：动作之后页面发生了什么、预期变化是否被观察到、哪些结构化信号可以作为
result evidence。

11.2.0 是文档初始化包：只初始化 runtime observation scope 和
realistic web runtime case catalog。它记录 Post-action Observation、Passive
Runtime Observation，以及 modal、toast、delayed button、loading state、
partial refresh、SPA content change、server push、passive DOM mutation 等真实
网页场景。

详细 11.2.x 拆包计划放在
[`docs/iterations/m11/m11-plan.md`](./iterations/m11/m11-plan.md) 和
[`docs/iterations/m11/11.2-runtime-observation-realistic-hardening/`](./iterations/m11/11.2-runtime-observation-realistic-hardening/)。
本路线图只保留 M11.2 的高层定位。

M11.2 不定义 recovery、retry、abort、user interruption、takeover 或 teaching
behavior。这些仍属于 v0.2 / M12 或更后续阶段。

## M11.3.x — Interactive Chat Productization

M11.3 turns the runtime conversation substrate into a product-facing
`wagent chat` loop. It is still CLI-first, but the user should be able to
teach and run page operations without understanding sessions, LearnedPath,
preview, or replay internals.

Delivered / current packages:

- **11.3 Interactive Chat Closed Loop** — accepted; `wagent chat` creates an
  `interactive_chat` session, learns a page operation, persists a LearnedPath,
  and executes the learned action in the same session.
- **11.3.1 Visible Chat Browser Operation** — implementation complete; chat
  learning and replay default to the app-bundled visible Playwright Chromium,
  with `--headless` opt-out.
- **11.3.2 Chat History & Debug Console** — implementation complete; conversation
  history/debug surfaces and CLI resume/list/history support.
- **11.3.3 Product-Level Chat Test Site Separation** — accepted; product-test-site
  is separate from validation-site, and product-level chat learning no longer
  depends on validation specs / assertions.
- **11.3.4 Conversation Intake Agent** — implementation complete; adds a
  schema-constrained natural-language intake role, deterministic fallback,
  guardrails, response provenance, and redacted LLM trace history. Scoped tests
  passed; real LLM-backed smoke remains pending.
- **11.3.5 Customer-Facing Agent Router & Capability Runtime** — proposed;
  expands the chat recovery problem into the product-facing Agent routing
  layer. It defines Customer-Facing Agent Router != Conversation Orchestrator,
  the Capability Registry, Page Understanding / Learning / Web Operation
  worker-Agent boundaries, target resolution, risk policy, no-thinking routing,
  progress/loading behavior, and history traces for route decisions and
  capability calls.

M11.3.4 and M11.3.5 do not let an LLM operate the browser. The LLM understands
user language, page semantics, and next-step routing; code validates scope,
risk, state, and execution policy; registered capabilities call Learning /
Replay / execution services for the browser work.

Codex CLI can read history for debugging as an external development Agent, but
it is not a product runtime Reply Producer.

## M12 — Recovery & Abort Dialogue

M12 turns failures and user aborts into first-class product flows. It
depends on the M11.0 conversation shell because recovery and abort are
runtime dialogues, not isolated execution statuses.

Internal Agents introduced / made concrete:

- **Failure Recovery Agent (legacy: Agent F)** — explains a failed step, offers
  continue / rerun / replan / takeover / abandon options, and produces
  the next boundary action.
- **User Abort Handler (legacy: Agent G)** — handles user-initiated aborts
  with continue / rerun / replan / takeover / abandon options.

Expected delivery:

- Pause-on-failure semantics for L3 execution.
- Recovery dialogue that can route to Task Path Planner only at planning
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

- **Teaching Guide Agent (legacy: Agent H)** — communicates the next teaching
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
- Teaching Guide Agent suggestions (legacy: Agent H) remain guidance; they cannot be written directly
  as LearnedPath actions.
- Path correction UI for editing or replacing an existing LearnedPath.
- Trust updates driven by user correction and correction evidence.

## M14 — Learning Quality, Coverage & Negative Knowledge

M14 revisits L1 quality after the L3 happy path and handoff loop exist.
It also absorbs the earlier M10 draft backlog for richer controls,
pattern generalization, and negative knowledge.

Internal Agents introduced / made concrete:

- **Page Understanding Agent (legacy: Agent A)** — separate page-purpose understanding
  from Supervisor evaluation.
- **Attempt Evaluation Agent (legacy: Agent B)** — keep attempt evaluation simple:
  output observations / anomalies; let code derive durable verdicts.
- **Learning Report Agent (legacy: Agent C)** — produce a user-facing report:
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
  Task Path Planner can consume later.

Negative knowledge / failure evidence becomes formal here:

- Store failed attempts, replay drift, `target_missing`,
  `unsupported_action`, and user correction evidence.
- Feed that evidence to Task Path Planner planning, Attempt Evaluation Agent
  evaluation, learning
  quality reports, and M15 automated evaluation.
- Add richer postcondition patterns and artifact verification patterns
  here or in M15, depending on implementation scope.

## M15 — Automated Evaluation, Audit & Hygiene

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

## M16 — External Interfaces

M16 exposes stable capability units after the main L1/L2/L3 loop is
useful. It is not the M11.0 runtime conversation CLI.

Expected delivery:

- Versioned API contracts for page learning, path planning, execution,
  verification, artifacts, and user-guided recording.
- Stable CLI commands for external schedulers, local scripting, and
  batch usage.
- Skill / Tool form for third-party Agent schedulers.
- Third-party scheduler interface.
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
- Let Task Path Planner compose already learned paths, while forbidding it from
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

## Explicit non-goals (M11.0)

See [`scope-boundaries.md`](./scope-boundaries.md) for the canonical
list. M11.0 is the runtime conversation and orchestration foundation;
the completed M10.2 replay boundaries remain useful historical
reference. Highlights:

- No Task Path Planner / Task Result Reporter / Failure Recovery Agent / User Abort Handler / Teaching Guide Agent (legacy: Agents D-H) implementations.
- No L3 task runner or task-to-path planning.
- No L3 task result verification.
- No artifact lifecycle.
- No multi-page workflow composition.
- No action risk gate.
- No target-site session or permission custody; login expiry,
  permission denial, auth redirects, and operation failures remain
  runtime failure / recovery issues.
