# Architecture

## Goal

WebAgentFlow provides a structured platform for learning web pages,
reusing verified LearnedPaths, planning task execution from learned data,
and verifying results against authored baselines — coordinated between a
Vue console, FastAPI backend, Python worker scaffold, and Playwright
runtime.

## System Layers

1. **Presentation** — Vue console provides operator-facing interfaces.
2. **Application** — FastAPI service owns API contracts, orchestration entry
   points, integration boundaries.
3. **Conversation / Orchestration** — planned runtime layer near the
   FastAPI application boundary. It will connect user messages, Agent
   calls, browser execution events, confirmation gates, abort / recovery
   dialogue, takeover, and teaching mode. It is a code-side session
   controller / dispatcher, not an LLM controller that chooses browser
   actions step by step. The Runtime Conversation Surface can start as
   a CLI and later be called by user-owned systems or operator consoles
   through stable CLI / API contracts.
4. **Execution** — Playwright runtime + async worker for browser automation.
5. **Infrastructure** — PostgreSQL, Redis, MinIO for persistence, cache, object
   storage.

## App Responsibilities

- `apps/console` — operator UI: autonomous workbench, run history,
  LearnedPath catalog, and overview landing page. Planned future
  responsibilities may include teaching overlays, operator review
  surfaces, artifact display, and richer workbench panels.
- `apps/api` — HTTP API, LLM provider layer, autonomous exploration,
  LearnedPath persistence / replay, page verification, validation-api
  mock backend. Planned future responsibilities include conversation
  sessions, orchestrator endpoints, Agent routing, artifact metadata,
  and failure-evidence APIs.
- `apps/worker` — async execution scaffold (currently scaffold).
- `apps/validation-site` — self-hosted test fixtures (login, users, …)
  that autonomous exploration runs against.
- `apps/cli` — Python CLI (`wagent`) plus the `verify-scenario`
  Claude Code skill that invokes it. It may later host the M11.0
  runtime conversation CLI, but that runtime surface is not implemented
  today.

---

## Current Progress

The old architecture timeline below records historical technical
accumulation. The current planning vocabulary lives in
[`product-model.md`](./product-model.md) and [`roadmap.md`](./roadmap.md):
product lifecycle stages are L1 / L2 / L3, delivery milestones are M10 /
M11 / ...

Current delivery milestone: **M10 Path Asset Foundation**. Current
executable package: `10.2-replay-execution-drift-detection`.

Current code status:

- M10 Path Asset Foundation is the active milestone.
- `10.2` replay / drift is the current task.
- `apps/worker` is still a scaffold.
- L2 user-guided learning, L3 task execution, runtime conversation,
  Conversation Orchestrator, Agent routing for D / E / F / G / H, and
  Agent H Teaching Guide Agent are planned but not implemented.

**Completed phases:**

1. **Page fact foundation** — raw HTML capture, HTML → Full AST (server-side,
   lxml), Full AST schema.
2. **User event recording** — click, input, change, navigate, richtext-input
   with full context.
3. **Event–AST association** — events mapped to AST nodes
   (exact / ancestor / none + fallback).
4. **DOM mutation recording** — MutationObserver on top-level + same-origin
   iframes, batching, noise filtering, AST association.
5. **Operation Step building** — correlating a primary event with subsequent
   DOM mutations into a Step.
6. **Agent initial understanding of pages and steps** — LLM provider layer,
   agent input contract, page understanding (6C), step understanding (6D),
   combined output (6E), server-side event AST matching.
7. **Full execution capability (Playwright)** — single-step execution chain:
   - 7A: ExecutionRequest/ExecutionResult contract, 6-level locator priority,
     `build_execution_request`.
   - 7B: Playwright browser/context/page lifecycle, `create_execution_runtime`.
   - 7C: 6-level priority locator resolver, SelectorDescriptor, region-scoped
     disambiguation.
   - 7D: `execute_action()` for click/fill/select/check/uncheck/hover/press/
     navigate/scroll.
   - 7E: `observe_post_action()` / `execute_and_observe()`, change detection,
     target post-state.

**Exploration subsystem** (built on top of legacy Phase 7):

- **Success evaluator** — rule-based evaluation of 6 condition types
  (url_changed, url_contains, title_contains, element_present, html_changed,
  no_error); 3-state semantics (success / failure / uncertain).
- **Task definitions** — external JSON files in `data/tasks/` describing
  site-specific tasks, with provenance tracking.
- **Exploration loop** — generic engine; zero site-specific code.
- **Exploration supervisor** — post-run LLM assessment (verdict / summary /
  anomalies / suggestions) with rule-based fallback.
- **Exploration workbench** — frontend page with 4 zones (task config,
  execution timeline, page state + supervisor, user verdict).

**Autonomous exploration subsystem** (new, user-driven through the workbench):

- **Page analyzer** (`services/learning/page_analyzer.py`) — live-page element
  discovery with structural-only classification (no keyword/site heuristics).
  Infers `semantic_role` for fillables (username / password / email / search /
  text) from HTML type + generic name/placeholder fragments.
- **Action planner** (`services/learning/action_planner.py`) — rule-based
  multi-field planner. `fill_values` dict maps semantic roles to best-fit
  fillable; fallback submit picker scores nearby clickables when no structural
  submit exists.
- **Autonomous explorer** (`services/learning/autonomous_explorer.py`) —
  orchestrator emitting phase events to SSE. Outcome verdict is
  `success | incomplete | no_progress | uncertain`.
- **Page verification comparator** (`services/learning/page_verification.py`) —
  compares an autonomous run against an authored spec
  (`apps/validation-site/specs/<page>.assertions.json`); produces a 5-score
  scorecard (element_recognition / action_coverage / verdict_accuracy /
  distraction_avoidance / supervisor_agreement). No aggregate total.
- **Autonomous Workbench** (`pages/AutonomousWorkbenchPage.vue`) — user-driven
  UI with SSE live progress; **7 blocks**: run config, live phase status,
  page analysis, execution timeline (with click-to-preview step screenshots
  via `<a-image>`), verification (self verdict + supervisor + 5-score
  scorecard), raw SSE event audit (every event captured with copy button +
  full-screen modal), source-origin legend.
- **Supervisor transparency** — the Supervisor Agent's `<think>...</think>`
  reasoning trace is preserved in `LlmResponse.thinking`, surfaced on the
  supervisor card as a collapsible "thinking process" panel. The model ID
  (`_model`) is shown alongside. `generate_structured` in `llm_provider.py`
  splits thinking from the final answer via `_split_thinking()` instead of
  silently stripping it.
- **Locale-aware Supervisor** — UI locale (BCP-47 code like `zh`, `en`,
  `ja`) passes through the stream endpoint into the Supervisor prompt as a
  "write natural-language fields in {language}" override. Map in
  `autonomous_explorer._LANGUAGE_NAMES`.
- **Validation site** (`apps/validation-site`) — self-hosted Vue fixtures
  (login + dashboard today, more to come) so autonomous exploration doesn't
  depend on public sites (which introduce CAPTCHA / rate-limit noise).
  Index page at `/` catalogues available fixtures (`IndexPage.vue`).

---

## B. Technical Route Change — Client vs Server AST

**Previous**: client-side DOM walker (`initial-state.ts`) produces a semantic
StateNode tree directly from the live DOM in the browser.

**Current**: split responsibilities.

- **Client (extension)** captures raw HTML (page + iframe documents), sends
  to server.
- **Server (API)** parses HTML → Full AST using `lxml.html`, maps to the
  project-owned Full AST schema.

The mapping layer is deliberately thin: tag normalization, attribute
filtering, text node interleaving, visibility detection. **The parser's
original tree structure is preserved as-is** — no reorganization, no semantic
interpretation, no structure rewriting.

Why:

- Server-side parsing is more stable, debuggable, testable.
- Proper logging, error handling, regression testing are straightforward.
- Decoupled from browser DOM API — can reprocess stored HTML with an improved
  parser without re-visiting pages.
- Third-party parsers (`lxml`, etc.) handle malformed real-world HTML robustly.

Key files:

- Server parser: `apps/api/app/services/html_ast_parser.py` (uses `lxml.html`)
- Full AST schema: `apps/api/app/schemas/ast.py`
- Server-side event matcher: `apps/api/app/services/server_ast_matcher.py`
- Execution contract: `apps/api/app/schemas/execution.py`
- Execution sub-package: `apps/api/app/services/execution/`
- Learning sub-package: `apps/api/app/services/learning/`
- Page verification schema: `apps/api/app/schemas/page_verification.py`
- Page analysis schema: `apps/api/app/schemas/page_analysis.py`
- Exploration router: `apps/api/app/routers/exploration.py`
- Validation API router: `apps/api/app/routers/validation_api.py`
- Validation specs: `apps/validation-site/specs/*.{md,assertions.json}`

### Dual-Track AST: Client vs Server Responsibilities

The project maintains two AST-related systems with distinct purposes. They
are **not in conflict**, but their boundaries must be respected.

**Server-side FullAST** (`html_ast_parser.py` → `ast_simplifier.py`):

- Authoritative page fact representation.
- `page_analyzer.py` consumes the Full AST to discover interactive
  elements during autonomous exploration.
- `page_verification.py` compares the observed page against the authored
  spec baseline using the same AST representation.

> Client-side recording tracks (`apps/extension`) have been retired;
> autonomous exploration drives a visible Playwright browser directly.

---

## C. Full AST vs Simplified AST

**Full AST** (current focus):

- Page fact layer — primary state representation.
- Preserves the third-party parser's original tree structure.
- Preserves sibling order, parent-child relationships, text node ordering.
- Preserves key attributes, iframe content (as subtree — see below).
- Does NOT restructure, regroup, or add semantic abstractions to the tree.
- Does NOT do early semantic compression or information loss.
- Produced server-side from captured HTML.

**Simplified AST** (future, NOT the current delivery milestone):

- A **structure-preserving projection** of the Full AST — not a rewrite.
- Keeps the same tree shape as the Full AST.
- Does NOT reorganize siblings, invent "title + content" containers, or
  reorder nodes.
- Primarily performs **attribute pruning**, not structural transformation.
- Intended as an LLM-friendly view derived deterministically from the Full AST.

> Simplified AST is a structure-preserving projection of the Full AST.

---

## D. Iframe Representation

The third-party HTML parser parses `<iframe>` tags from the source HTML.
However, an iframe's internal document content is a separate document that
the client must capture separately and pass to the server.

In the Full AST, **iframe internal content is attached as a subtree of the
`<iframe>` node**, not as a side-channel field:

- `<iframe>` is a regular element node in the tree.
- The frame document content is parsed and attached as a child subtree.
- A synthetic `<frame-body>` wrapper node serves as the document root inside
  the iframe's children.
- No special `frame_content` or similar side-channel fields — the unified tree
  structure is used throughout.

> iframe is a node, and the frame document is attached as its subtree, not as
> a side-channel field.

Consequences:

- Tree walkers process iframe content the same way as any other subtree.
- No special-casing needed for iframe in downstream consumers.
- Multi-level iframe nesting is handled naturally via recursion.

---

## E. Historical Development Timeline (legacy 12-step view)

This list is retained as architecture history. It is not the current
roadmap vocabulary; use `roadmap.md` M10 / M11 / ... for forward
planning.

1. ~~Page fact foundation~~ ✅
2. ~~User event recording~~ ✅
3. ~~Event–AST association~~ ✅
4. ~~DOM mutation recording~~ ✅
5. ~~Operation Step building~~ ✅
6. ~~Agent initial understanding of pages and steps~~ ✅
7. ~~Full execution capability (Playwright)~~ ✅
8. Wait-for-expected-change mechanism + automated testing (partially
   absorbed into `pass_gate`, scorecards, and page verification)
9. ~~Exploration loop + success evaluation + autonomous workbench~~ ✅
10. Path abstraction & experience accumulation (current delivery
    milestone M10)
11. User correction & behavior teaching (reshaped into M13)
12. Automated evaluation & continuous optimization system (reshaped into
    M15)

**Key parallel relationships:**

- **Legacy Phase 7 execution** is complete — provides the atomic action layer for
  exploration.
- **Exploration subsystem** is built on legacy Phase 7 — TaskDefinition →
  `run_exploration` → success evaluation → supervisor assessment.
- **Autonomous exploration subsystem** remains the learning foundation — URL →
  `autonomous_explorer.run_autonomous_exploration` → page verification
  scorecard → user review in the workbench.
- **Path abstraction (M10)** starts after exploration validates.

---

## F. Tool / Data Separation

The application is a pure engine. **Site-specific knowledge is never
hardcoded in Python code.**

- **Verification specs** live in `apps/validation-site/specs/*.{md,assertions.json}`
  — describe the authored baseline for a page, including positive-path
  and negative-path scenarios.
- **The autonomous engine** (`autonomous_explorer.py`) is generic — takes a
  URL (optionally paired with a spec + scenario) and discovers structure
  at runtime.
- **Switching target sites** means adding a new spec, not changing Python
  code.

---

## G. Services Sub-Package Structure

`apps/api/app/services/` is organized into a small number of capability
groups. Current implemented services mostly back autonomous exploration
and M10 Path Asset Foundation. The later conversation, teaching,
artifact, and evidence services below are planned service areas unless
explicitly marked as implemented.

**`services/execution/`** — Playwright runtime:

- `execution_runtime.py` — chromium/context/page lifecycle wrapper.
- Public API exported via `__init__.py`.

**`services/learning/`** — autonomous exploration + page verification:

- `autonomous_explorer.py` — orchestrator, SSE event emission,
  Supervisor LLM call.
- `page_analyzer.py` — live-page element discovery.
- `action_planner.py` — rule-based multi-field planner.
- `supervisor_observations.py` — LLM observation-atom schema and
  code-side verdict derivation.
- `page_verification.py` — spec-baseline comparator producing a
  five-part scorecard.
- `page_signature.py` — pure functions
  (`path_template` / `query_signature` / `dom_fingerprint`) that
  compute the LearnedPath identity quadruple. Called by the
  exploration router's ingest hook on `pass_gate = pass`.

**`services/analysis/`** — analyzer helpers (e.g. `form_label_extractor.py`).

**Top-level flat services:** `html_ast_parser.py`, `ast_simplifier.py`,
`llm_provider.py`.

**Compat re-export stubs** exist at old paths (e.g.
`services/execution_runtime.py`) so existing imports keep working. New code
should use the sub-package paths.

### Planned Service Areas

These service areas are architecture placeholders for M11+ work; they
should not be read as existing packages:

**`services/conversation/`** — planned runtime conversation and
orchestration:

- session state
- Conversation Orchestrator / Dispatcher
- user message and engine event routing
- message log
- confirmation, abort, recovery, takeover, and teaching-mode state

**`services/teaching/`** — planned L2 teaching support:

- highlight target generation
- Agent H Teaching Guide integration
- visible-browser teaching event handling
- user action recorder integration

**`services/artifacts/`** — planned artifact handling:

- download / export / screenshot capture
- artifact metadata
- artifact display / return hooks
- retention and cleanup hooks

**Failure evidence / negative knowledge** — planned learning and
evaluation input:

- failed attempts
- replay drift
- `target_missing` / `unsupported_action` evidence
- user correction evidence

M10.2 replay / drift may emit the raw evidence signals, but it does not
implement the full negative-knowledge store.

---

## H. Planned Runtime Event Flow

The future runtime loop should preserve a single user-facing
WebAgentFlow conversation while routing internally through bounded
Agents and deterministic services:

```text
User message
-> Runtime Conversation Surface
-> Conversation Orchestrator / Dispatcher
-> Agent D / F / G / H or execution service
-> Browser runtime / replay engine / teaching recorder
-> result event
-> Conversation Orchestrator / Dispatcher
-> Agent E / F / G / H response
-> user
```

Important invariant: the Orchestrator owns session state and routing.
LLMs can participate at planning, reporting, recovery / abort, and
teaching boundaries, but they must not become a per-step browser action
controller.

---

## I. Planned Teaching Mode Architecture

Teaching mode is an L2 capability planned for M13. It is not part of
the current M10.2 replay / drift package.

Planned pieces:

- visible Playwright browser
- overlay / highlight layer for target elements
- indicator / tooltip / next-step prompt rendering in the operator UI
- user event recorder that captures real clicks, inputs, selections,
  navigation, and observable state changes
- Agent H Teaching Guide Agent producing natural-language guidance and
  highlight targets

Recorded LearnedPath actions must come from real user events. Agent H
suggestions are guidance, not provenance, and cannot be written directly
as LearnedPath actions.

---

## J. Planned Artifacts and Failure Evidence

Future L3 execution should treat artifacts as first-class task outputs:
downloaded files, exports, screenshots, generated evidence, and final
task attachments should have capture, metadata, display / return,
retention, and cleanup paths.

Failure evidence / negative knowledge should also become first-class
learning and evaluation input. Failed attempts, replay drift,
`target_missing`, `unsupported_action`, visible errors, and user
corrections should feed planning, learning quality, regression
evaluation, and optimization. M10.2 can produce replay / drift evidence,
but it does not implement the full store.

---

## Infrastructure

Docker Compose (`infra/docker/docker-compose.yml`) provides:

- **PostgreSQL 16** — primary database.
- **Redis 7.4** — caching/queuing.
- **MinIO** — object storage (ports 9000 API, 9001 console).

Copy `.env.example` to `.env` at repo root. Console has its own
`apps/console/.env.example`.

## Worker

`apps/worker/app/` runs a polling `JobRunner` loop. Currently a scaffold —
heartbeat logging is implemented but job execution logic is not yet built out.

---

## See Also

- [`product-model.md`](./product-model.md) — **authoritative product
  model**. This document describes how the code is organized; product
  model describes what the code is supposed to do. Read product model
  first when deciding *what* to build.
- [`docs/scope-boundaries.md`](./scope-boundaries.md) — what's explicitly
  NOT part of the current delivery milestone.
- [`docs/roadmap.md`](./roadmap.md) — operational milestones for the v0.1
  release cut.
- [`../CLAUDE.md`](../CLAUDE.md) — session-level guidance for AI coding
  agents.
