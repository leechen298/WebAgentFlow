# Roadmap

Operational view of what's shipped, what's current, and what's next.

- For what the product **is** (three phases, seven Agents, invariants),
  see [`product-model.md`](./product-model.md). That's the authoritative
  product reference.
- For the 12-phase architectural timeline, see
  [`architecture.md`](./architecture.md) §E.

## Shipped (foundation + autonomous exploration subsystem)

Post-2026-04-20 cleanup, the only product surface in the repo is the
autonomous-Playwright pipeline. Earlier iterations (recording, Chrome
extension, task-driven exploration, skills / runs / learning-debug UI)
have been removed from the code — see
`memory/project_legacy_stack_removed.md`. For the historical 12-phase
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
- `routers/exploration.py` — `/autonomous-run[/stream]`,
  `/specs[/{id}]`, `/autonomous-runs/list|get`, `/screenshots/{file}`
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

## Phase 9 — closed 2026-04-21

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
    asserted on — their scenarios are a Phase 10 deliverable.
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

No remaining Phase 9 items. Phase 10 is now open.

## Phase 10 — Path abstraction & experience accumulation (in progress)

With Phase 9 closed, the focus shifts from "can the engine drive a
page" to "can it reuse what it learned and cover more control
shapes":

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
- **Cross-page pattern mining** — detect when distinct pages share an
  action shape (login, search, CRUD).
- **Replay execution against stored paths** with drift detection
  against current page analysis.
- **Popup-based control support** — extend `page_analyzer` +
  `action_planner` to handle components that reveal their interactive
  surface only after a click (Cascader, DatePicker, RangePicker,
  MonthPicker, column sort / filter inside a table header).
  The engine needs to first click the trigger, then operate the
  surfaced popup surface. Native inline non-text controls (radio /
  checkbox groups) are in Phase 9 scope — Phase 10 only adds the
  popup shape on top of that foundation.
- **Custom click-toggle controls** — Tag-as-filter and similar
  `<span>` / `<div>`-based pills that are not native form inputs.
  Separate from popup support because the trigger IS the interactive
  surface; no popup to operate. Folded into this phase because they
  share the "click changes a query param" contract with popup
  filters.
- **Form-label extractor · coverage expansion** — the analyzer's
  `form_label_extractor` currently ships handlers for Ant Design
  (matches `.ant-form-item` → `.ant-form-item-label`) and native
  HTML5 `<label for>`. Before Phase 10 closes, add handlers for the
  other widely-used Vue/React form libraries that follow the same
  Form.Item idiom but with a different class prefix. Candidates and
  their characteristic classes:
  - Element Plus (`el-form-item`)
  - Naive UI (`n-form-item`)
  - Arco Design (`arco-form-item`)
  - TDesign (`t-form-item`)
  - Quasar (`q-field__label`) — shape differs slightly, may need its
    own handler
  - Material UI / MUI v5 (`MuiFormControl-root` wrapping
    `MuiInputLabel-root`) — different idiom, separate handler
  Each new handler is ~15 LOC; the dispatcher in `extract_label`
  already picks the first hit. Ship as needed when fixture pages or
  user-reported real pages fall outside the current coverage. Once
  the code lands, backfill
  `apps/validation-site/specs/users.assertions.json` with the Tier 2
  scenarios that exercise each control, using the `users` fixture
  already on the page — so the scorecard flipping green becomes the
  quantitative evidence of the improvement.

## Further (Phases 11–12)

- Phase 11 — User correction & behavior teaching (the user edits a
  LearnedPath; the system learns what the user changed and why).
- Phase 12 — Automated evaluation & continuous optimization system
  (regression runs against the full fixture catalogue, drift alerts).

## Explicit non-goals (for current phase)

See [`scope-boundaries.md`](./scope-boundaries.md) for the canonical
list. Highlights: no real-time per-step LLM supervision in Phase 3, no
cross-device sync. CLI / Skill / external-Agent interfaces are **not
in this phase** either, but they are a long-term delivery direction —
see [`product-model.md`](./product-model.md) §10.
