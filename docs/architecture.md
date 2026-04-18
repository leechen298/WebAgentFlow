# Architecture

## Goal

WebAgentFlow provides a structured platform for capturing web interactions,
analysing pages autonomously, planning and executing actions, and verifying
results against authored baselines — all coordinated between a Vue console,
FastAPI backend, Python worker, and browser extension.

## System Layers

1. **Presentation** — Vue console + Chrome extension provide operator-facing
   interfaces.
2. **Application** — FastAPI service owns API contracts, orchestration entry
   points, integration boundaries.
3. **Execution** — Playwright runtime + async worker for browser automation.
4. **Infrastructure** — PostgreSQL, Redis, MinIO for persistence, cache, object
   storage.

## App Responsibilities

- `apps/console` — operator UI for recordings, skills, runs, exploration,
  autonomous workbench.
- `apps/api` — HTTP API, LLM provider layer, autonomous exploration,
  page verification, validation-api mock backend.
- `apps/worker` — async execution shell (currently scaffold).
- `apps/extension` — Chrome MV3 recorder with background / content / popup.
- `apps/validation-site` — self-hosted test fixtures (login, dashboard, …)
  that autonomous exploration runs against.

---

## Current Phase & Progress

The project follows a 12-phase development timeline. Phases 1–7 complete.
Exploration + autonomous workbench in active development.

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

**Exploration subsystem** (built on top of Phase 7):

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
- Locator schema: `apps/api/app/schemas/locator.py`
- Observation schema: `apps/api/app/schemas/observation.py`
- Learning sub-package: `apps/api/app/services/learning/`
- Page verification schema: `apps/api/app/schemas/page_verification.py`
- Page analysis schema: `apps/api/app/schemas/page_analysis.py`
- Task definition schema: `apps/api/app/schemas/task_definition.py`
- Success criteria schema: `apps/api/app/schemas/success_criteria.py`
- Task loader: `apps/api/app/services/task_loader.py`
- Exploration router: `apps/api/app/routers/exploration.py`
- Validation API router: `apps/api/app/routers/validation_api.py`
- Task definitions: `data/tasks/*.json`
- Validation specs: `apps/validation-site/specs/*.{md,assertions.json}`

### Dual-Track AST: Client vs Server Responsibilities

The project maintains two AST-related systems with distinct purposes. They
are **not in conflict**, but their boundaries must be respected.

**Client-side AstIndex** (`apps/extension/src/recorder/ast-index.ts`):

- Recording-time real-time matching tool.
- Runs in the browser during recording to immediately associate events /
  mutations with stateTree nodes.
- Produces `astMatch` on each event (confidence, nodeId, nodeLabel, areaLabel).
- **Not** the authoritative source for page structure or execution-layer
  positioning.

**Server-side FullAST** (`html_ast_parser.py` → `ast_simplifier.py` →
`server_ast_matcher.py`):

- Authoritative page fact representation.
- Page understanding (6C), step understanding (6D), combined understanding (6E)
  all consume server-side AST.
- `server_ast_matcher.py` provides `server_ast_match` — event positioning
  within the authoritative AST.
- Phase 7 execution layer should consume server-side AST and
  `server_ast_match`, not client stateTree.

**Consumption priority:**

- Client `astMatch` is preserved as recording-time auxiliary information.
- `server_ast_match` is the server-side authoritative positioning for events.
- Downstream consumers (step_builder, agent_input) prefer `server_ast_match`
  when available, fall back to client `astMatch`.
- Mutation server-side re-matching is **not yet implemented** — mutations
  still use client `astMatch` only.

> The goal is not "immediately unify all AST to the server". The client-side
> AstIndex stays for real-time recording. The server-side AST is the
> authoritative source for understanding and execution.

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

**Simplified AST** (future, NOT this phase):

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

## E. Development Timeline (12 phases)

1. ~~Page fact foundation~~ ✅
2. ~~User event recording~~ ✅
3. ~~Event–AST association~~ ✅
4. ~~DOM mutation recording~~ ✅
5. ~~Operation Step building~~ ✅
6. ~~Agent initial understanding of pages and steps~~ ✅
7. ~~Full execution capability (Playwright)~~ ✅
8. Wait-for-expected-change mechanism + automated testing (parallel tracks)
9. **Exploration loop + success evaluation + autonomous workbench** ← current
10. Path abstraction & experience accumulation (starts after exploration
    validates)
11. User correction & behavior teaching
12. Automated evaluation & continuous optimization system

**Key parallel relationships:**

- **Phase 7 execution** is complete — provides the atomic action layer for
  exploration.
- **Exploration subsystem** is built on Phase 7 — TaskDefinition →
  `run_exploration` → success evaluation → supervisor assessment.
- **Autonomous exploration subsystem** is the current focus — URL →
  `autonomous_explorer.run_autonomous_exploration` → page verification
  scorecard → user review in the workbench.
- **Path abstraction (Phase 10)** starts after exploration validates.

---

## F. Tool / Data Separation

The application is a pure engine. **Site-specific knowledge is never
hardcoded in Python code.**

- **Task definitions** live in `data/tasks/*.json` — describe what to do on
  a specific site.
- **Verification specs** live in `apps/validation-site/specs/*.assertions.json`
  — describe the authored baseline for a page.
- **The exploration engine** (`exploration_loop.py`) is generic — reads task
  definitions and executes them.
- **The autonomous engine** (`autonomous_explorer.py`) is generic — takes a
  URL and discovers structure at runtime.
- **Success criteria** are defined in task definitions or in the DB — not in
  evaluator code.
- **Switching target sites** means changing user-provided data files, not
  changing Python code.

Provenance tracking on all knowledge assets:

- `source`: `"builtin"` or `"user"`
- `provenance`: how it was created (`user_authored`, `autonomous_exploration`,
  `autonomous_then_user_corrected`, etc.)
- `based_on`, `edited_by_user`, `revision`: evolution tracking

> Knowledge assets (tasks, paths, criteria) are designed with
> migration / backup support in mind — provenance tracking preserves
> enough context that a record can be inspected, diffed, and moved
> between environments.

---

## G. Services Sub-Package Structure

`apps/api/app/services/` is organized into sub-packages for the main capability
groups.

**`services/execution/`** — Phase 7 execution pipeline:

- `execution_contract.py`, `execution_runtime.py`, `locator_resolver.py`,
  `action_executor.py`, `post_action_observer.py`
- `run_single_action.py` — simplified entry point for exploration loop
- Public API exported via `__init__.py`

**`services/learning/`** — autonomous learning, exploration, verification:

- `candidate_inference.py`, `success_evaluator.py`, `exploration_loop.py`,
  `exploration_supervisor.py`
- `page_analyzer.py`, `action_planner.py`, `autonomous_explorer.py`,
  `page_verification.py` (autonomous subsystem)
- CRUD services: `exploration_run_service.py`, `learned_path_service.py`,
  `success_criteria_service.py`, `candidate_feedback_service.py`
- Public API exported via `__init__.py`

**Remaining services** (AST, understanding, CRUD, LLM) stay flat in
`services/` root — not yet worth sub-packaging.

**Compat re-export stubs** exist at old paths (e.g.
`services/execution_runtime.py`) so existing imports keep working. New code
should use the sub-package paths.

---

## DOM Mutation Tracking (extension)

During recording, the extension monitors DOM changes via `MutationObserver`
on both the top-level document and same-origin iframe documents. Key files:

- `src/recorder/mutation-observer.ts` — `DomMutationTracker` class: observes
  childList/attributes/characterData mutations, batches at ~500ms, maps to
  AST nodes, emits `DomMutationRecord[]`.
- Mutation records are stored in `RecorderState.domMutations` and included
  in `meta.domMutations` on submission.
- Each mutation carries: target element info, mutation detail, AST
  association, frame info, area context.
- Noise filtering: script/style/svg tags, framework bookkeeping attrs
  (`_ngcontent`, `data-v-`), extension elements.
- Iframe support: same-origin iframes observed recursively; cross-origin
  silently skipped.
- Frontend: "DOM Changes" tab on RecordingDetailPage shows mutation timeline.

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
- [`parser-rules.md`](./parser-rules.md) — Initial State Parser
  (client-side DOM → StateNode) rules. Mandatory when touching extension
  parsing code.
- [`docs/scope-boundaries.md`](./scope-boundaries.md) — what's explicitly
  NOT part of the current phase.
- [`docs/roadmap.md`](./roadmap.md) — operational milestones for the v0.1
  release cut.
- [`../CLAUDE.md`](../CLAUDE.md) — session-level guidance for AI coding
  agents.
