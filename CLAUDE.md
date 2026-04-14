# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Multi-agent sync rule**: This file is kept in sync with `CLAUDE.zh.md` (Chinese) and `AGENTS.md` (for Codex and other AI agents). When any of the three files is modified, the others must be updated to stay consistent.

## Project Overview

WebAgentFlow is a monorepo for an agent-driven web workflow engine with:
- Vue 3 frontend console (`apps/console`)
- FastAPI backend API (`apps/api`)
- Python worker service (`apps/worker`)
- Chrome MV3 browser extension recorder (`apps/extension`, built with WXT)
- Shared TypeScript packages (`packages/`)

## Current Project Direction

### A. Current Phase & Progress

The project follows a 12-phase development timeline. Phases 1–6 are completed; Phase 7 is in progress (7A done).

**Completed phases:**
1. **Page fact foundation** — raw HTML capture, HTML → Full AST (server-side, lxml), Full AST schema
2. **User event recording** — click, input, change, navigate, richtext-input with full context
3. **Event–AST association** — events mapped to AST nodes (exact/ancestor/none + fallback)
4. **DOM mutation recording** — MutationObserver on top-level + same-origin iframes, batching, noise filtering, AST association
5. **Operation Step building** — correlating a primary event with subsequent DOM mutations into a Step
6. **Agent initial understanding of pages and steps** — LLM provider layer, agent input contract, page understanding (6C), step understanding (6D), combined output (6E), server-side event AST matching
7A. **Execution contract** — ExecutionRequest/ExecutionResult schemas, locator priority (6-level), data consumption boundary, `build_execution_request` entry point
7B. **Execution runtime** — Playwright browser/context/page lifecycle, navigation, page observation (URL/title/HTML/screenshot), unified error handling, `create_execution_runtime` factory
7C. **Locator resolution** — 6-level priority resolver (`resolve_locator`), SelectorDescriptor for Playwright consumption, region-scoped disambiguation, structured failure reporting
7D. **Action executor** — `execute_action()` single-step executor for click/fill/select/check/uncheck/hover/press/navigate, before/after state capture, structured error handling
7E. **Post-action observation** — `observe_post_action()` / `execute_and_observe()`, screenshot + HTML snapshot, URL/title/HTML change detection, target post-state (present/visible), observation attached to ExecutionResult

**Phase 7 complete** — full single-step execution capability: contract → runtime → locator → action → observation

### B. Technical Route Change

The technical approach has shifted from the earlier direction.

**Previous approach**: The client-side DOM walker (`initial-state.ts`) produces a semantic StateNode tree directly from the live DOM in the browser, combining HTML parsing, component classification, and semantic extraction in a single browser-side pass.

**Current approach**: Split responsibilities between client and server:
- **Client (extension)** — captures raw HTML of the page and iframe content documents, sends to server
- **Server (API)** — parses HTML into Full AST using a mature third-party HTML parser library, then maps the parser output to the project-owned Full AST schema

The parser pipeline is: **third-party library for HTML parsing + project-owned Full AST schema and thin mapping logic**.

The mapping layer is deliberately thin: tag normalization, attribute filtering, text node interleaving, and visibility detection. **The parser's original tree structure is preserved as-is** — no reorganization, no semantic interpretation, no structure rewriting. The Full AST should stay close to what the third-party parser produces.

Reasons for this shift:
- Server-side parsing is more stable, debuggable, and testable
- Proper logging, error handling, and regression testing are straightforward
- Decoupled from browser DOM API — can reprocess stored HTML with improved parser without re-visiting pages
- Third-party HTML parsers (`lxml`, etc.) handle malformed real-world HTML robustly
- The existing client-side parser (`initial-state.ts`) remains functional but the primary AST pipeline is moving server-side

Server-side parser: `apps/api/app/services/html_ast_parser.py` (uses `lxml.html`)
Full AST schema: `apps/api/app/schemas/ast.py`
Server-side event matcher: `apps/api/app/services/server_ast_matcher.py`
Execution contract schema: `apps/api/app/schemas/execution.py`
Execution contract builder: `apps/api/app/services/execution_contract.py`
Execution runtime: `apps/api/app/services/execution_runtime.py`
Locator resolver: `apps/api/app/services/locator_resolver.py`
Locator schema: `apps/api/app/schemas/locator.py`
Action executor: `apps/api/app/services/action_executor.py`
Post-action observer: `apps/api/app/services/post_action_observer.py`
Observation schema: `apps/api/app/schemas/observation.py`

#### Dual-Track AST: Client vs Server Responsibilities

The project currently maintains two AST-related systems. They serve different purposes and are **not in conflict**, but their boundaries must be respected:

**Client-side AstIndex** (`apps/extension/src/recorder/ast-index.ts`):
- A recording-time real-time matching tool
- Runs in the browser during recording to immediately associate events/mutations with stateTree nodes
- Produces `astMatch` on each event (confidence, nodeId, nodeLabel, areaLabel)
- **Not** the authoritative source for page structure or execution-layer positioning

**Server-side FullAST** (`html_ast_parser.py` → `ast_simplifier.py` → `server_ast_matcher.py`):
- The authoritative page fact representation
- Page understanding (6C), step understanding (6D), combined understanding (6E) all consume server-side AST
- `server_ast_matcher.py` provides `server_ast_match` — event positioning within the authoritative AST
- Phase 7 execution layer should consume server-side AST and `server_ast_match`, not client stateTree

**Relationship and consumption priority:**
- Client `astMatch` is preserved as recording-time auxiliary information
- `server_ast_match` is the server-side authoritative positioning for events
- Downstream consumers (step_builder, agent_input) prefer `server_ast_match` when available, fall back to client `astMatch`
- Mutation server-side re-matching is **not yet implemented** — mutations still use client `astMatch` only

> The goal is not "immediately unify all AST to the server". The client-side AstIndex stays for real-time recording. The server-side AST is the authoritative source for understanding and execution.

### C. Full AST vs Simplified AST

**Full AST** (current focus):
- The page fact layer — primary state representation
- Preserves the third-party parser's original tree structure
- Preserves sibling order, parent-child relationships, text node ordering
- Preserves key attributes, iframe content (as subtree — see section D)
- Does NOT restructure, regroup, or add semantic abstractions to the tree
- Does NOT do early semantic compression or information loss
- Produced server-side from captured HTML

**Simplified AST** (future, NOT this phase):
- A **structure-preserving projection** of the Full AST — not a rewrite
- Keeps the same tree shape as the Full AST
- Does NOT reorganize siblings, invent "title + content" containers, or reorder nodes
- Primarily performs **attribute pruning**, not structural transformation
- Intended as an LLM-friendly view derived deterministically from the Full AST

> Simplified AST is a structure-preserving projection of the Full AST.

### D. Iframe Representation

The third-party HTML parser parses `<iframe>` tags from the source HTML. However, an iframe's internal document content is a separate document that the client must capture separately and pass to the server.

In the Full AST, **iframe internal content is attached as a subtree of the `<iframe>` node**, not as a side-channel field:

- `<iframe>` is a regular element node in the tree
- The frame document content is parsed and attached as a child subtree
- A synthetic `<frame-body>` wrapper node serves as the document root inside the iframe's children
- No special `frame_content` or similar side-channel fields — the unified tree structure is used throughout

> iframe is a node, and the frame document is attached as its subtree, not as a side-channel field.

This approach means:
- Tree walkers process iframe content the same way as any other subtree
- No special-casing needed for iframe in downstream consumers
- Multi-level iframe nesting is handled naturally via recursion

### E. Development Timeline (12 phases)

1. ~~Page fact foundation~~ ✅
2. ~~User event recording~~ ✅
3. ~~Event–AST association~~ ✅
4. ~~DOM mutation recording~~ ✅
5. ~~Operation Step building~~ ✅
6. ~~Agent initial understanding of pages and steps~~ ✅
7. **Full execution capability (Playwright)** ← current — real browser automation with complete action coverage
8. Wait-for-expected-change mechanism + automated testing (parallel tracks, start together with Phase 7)
9. Execution loop stabilization — action → wait → judge → next step
10. Path abstraction & experience accumulation (starts after Phase 7, grows continuously)
11. User correction & behavior teaching
12. Automated evaluation & continuous optimization system

**Key parallel relationships:**
- **Agent understanding (Phase 6)** is complete — provides page/step/combined understanding for execution layer
- **Automated testing (Phase 8B)** must start as soon as execution capability exists, not after — execution and testing grow together
- **Path abstraction (Phase 10)** is not a final summary module — it starts after execution begins and grows with the system

### F. Explicitly Out of Scope (current phase)

The following are **not** part of the current implementation phase:
- Replay execution strategies
- User behavior ↔ page change causal modeling
- Historical path template caching
- User correction & behavior teaching
- "Page summarizer" approaches that restructure DOM for readability

## Common Commands

### Setup & Development
```bash
# Install dependencies
pnpm install
python3.11 -m venv .venv
.venv/bin/pip install -e './apps/api[dev]' -e './apps/worker[dev]'

# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
pnpm run db:migrate:api

# Run all components
pnpm run dev             # Local development
pnpm run dev:lan         # LAN accessible (binds to 0.0.0.0)

# Run individual components
pnpm run dev:console     # Vite dev server (port 5174)
pnpm run dev:api         # Uvicorn dev server (port 8001)
pnpm run dev:worker
```

### Build, Lint, Test
```bash
# Build
pnpm run build              # Build all
pnpm run build:packages     # Build shared packages (required before console)
pnpm run build:console
pnpm run build:extension

# Lint & Format
pnpm run lint               # ESLint + Ruff
pnpm run format             # Prettier + Ruff

# Frontend tests (Vitest)
pnpm run test               # Run all console tests
pnpm run test:dev           # Watch mode
pnpm run test:coverage
pnpm run test:single        # Single file via env var

# API tests (Pytest)
cd apps/api && .venv/bin/pytest                             # All tests
cd apps/api && .venv/bin/pytest tests/test_health.py -v    # Single file
cd apps/api && .venv/bin/pytest -k "test_create" -v        # Pattern match
```

## Git Safety Rules

- Any development branch whose name ends with `-local` is local-only and must never be pushed to any remote.
- Before running `git push`, always check the current branch name first. If the branch ends with `-local`, stop and do not push.
- If the work on a `-local` branch needs to be published, create or move a non-`-local` branch to the same commit first, then push that branch instead.

## API Architecture

The FastAPI backend (`apps/api/app/`) uses a strict layered architecture:
- **Routers** (`routers/`): HTTP endpoints only, action-based routes
- **Services** (`services/`): Business logic
- **Repositories** (`repos/`): SQLAlchemy data access
- **Models** (`models/`): ORM models with JSON columns for flexible payloads
- **Schemas** (`schemas/`): Pydantic request/response models
- **Core** (`core/`): Config (Pydantic BaseSettings), DB session, Redis, logging, exceptions

### Action-Based Routes
All endpoints use action suffixes instead of RESTful HTTP verbs:
- `POST /recordings/create`, `GET /recordings/list`, `GET /recordings/get?recording_id=...`
- `POST /recordings/update`, `POST /recordings/delete`
- Same pattern for `/skills/*` and `/runs/*`
- `GET /health` — DB connectivity check

### Response Format
All responses use an envelope: `{"code": 0, "msg": "ok", "data": {...}}`. Defined in `schemas/base.py` as `ApiResponse[T]`. The frontend axios interceptor unwraps `data` automatically.

### Database
- PostgreSQL via Docker Compose, SQLAlchemy 2.x, Alembic migrations
- All models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` (`id`, `created_at`, `updated_at`)
- JSON columns: `Recording.events`, `Recording.meta`; `Skill.definition`; `Run.input_payload`, `Run.result_payload`, `Run.logs`

## Frontend Architecture

The Vue 3 console (`apps/console/src/`) uses:
- **Router** (`router/index.ts`): All routes wrapped in `MainLayout`
- **Stores** (`stores/`): Pinia — `app.ts` (global state, API connectivity), plus per-resource stores for recordings, skills, runs
- **API client** (`api/`): Axios modules per resource; interceptor transparently unwraps `ApiResponse.data`
- Path alias `@` maps to `src/`

Frontend tests live in `src/__tests__/` using Vitest + `@vue/test-utils`. Tests using Pinia must call `setActivePinia(createPinia())` in `beforeEach`.

### API Proxy vs Direct Mode
Controlled by `VITE_USE_DEV_PROXY` in `apps/console/.env`:
- `true` — Vite proxies `/api` requests (avoids CORS, same-origin)
- `false` — Direct calls to `VITE_API_BASE_URL`; requires `CORS_ALLOWED_ORIGINS` set on API

## Extension Architecture

Built with WXT framework (`apps/extension/`):
- `entrypoints/background.ts` — Service worker (MV3)
- `entrypoints/content.ts` — Injected into pages for event capture and DOM mutation tracking
- `entrypoints/popup/` — Vue 3 recording UI (status, name input, start/stop)
- Recording state is persisted via extension storage

### DOM Mutation Tracking

During recording, the extension monitors DOM changes via `MutationObserver` on both the top-level document and same-origin iframe documents. Key files:

- `src/recorder/mutation-observer.ts` — `DomMutationTracker` class: observes childList/attributes/characterData mutations, batches them at ~500ms intervals, maps to AST nodes, emits `DomMutationRecord[]`
- Mutation records are stored in `RecorderState.domMutations` and included in `meta.domMutations` on submission
- Each mutation carries: target element info, mutation detail (what changed), AST association (exact/ancestor/none + fallback), frame info, area context
- Noise filtering: script/style/svg tags, framework bookkeeping attrs (_ngcontent, data-v-), extension elements
- Iframe support: same-origin iframes are observed recursively; cross-origin silently skipped
- Frontend: "DOM Changes" tab on RecordingDetailPage shows mutation timeline with type, target, AST match, and change details

## Initial State Parser — DOM-to-AST Rules (client-side, gradually being replaced by server-side)

> **Note**: This section documents the existing client-side DOM walker (`initial-state.ts`). The primary AST pipeline is migrating to server-side HTML → Full AST (see "Current Project Direction" above). These client-side rules remain in effect for the extension code but new AST capabilities should be built server-side in `apps/api/app/services/html_ast_parser.py`.

The extension's `initial-state.ts` builds a simplified AST (StateNode tree) from the live DOM. When modifying or extending the parser, the following rules are **mandatory constraints**.

### Core Principle: Unified Recursion + Fallback

The parser processes each DOM node through a unified recursive flow:

```
walkNode(el):
  1. classifyNode(el)     → unified classification (known component > class/tag/id > native HTML > null)
  2. tryProcess(el, type) → attempt extraction with the matched processor
  3. processor returns empty → fall back to walkChildren generic recursion
  4. walkChildren also empty + visible content exists → localHtml fallback (type: 'custom')
```

**No branch failure may silently discard content**. A processor returning `[]` means "I cannot handle this, please fall back" — not "this element has no content".

### Top Principle: DOM Fidelity First

The parser does not "understand the page then rewrite it" — it "faithfully transcribes the page into a structured intermediate representation".

1. **Original DOM tree relationships first** — output JSON `children` order must match original DOM order
2. **Sibling order first** — never reorder siblings for semantic abstraction
3. **Node type first** — each DOM node should be preserved according to its actual type
4. **Hidden nodes must be kept** — annotated via `cssState`, never skipped
5. **Complex nodes must keep localHtml fallback** — when semantic extraction is insufficient
6. **Never restructure original page structure** to form abstractions like "title + content" or "group + detail"

### Classification Priority (highest to lowest, first match wins)

1. **Known component library elements** — e.g. `el-select`, `ant-cascader`, `van-cell`, `n-date-picker`. Processed as a whole component type, **never decomposed into internal DOM structure** (e.g. el-select with an internal input is still treated as a select). The component classifier (`component-classifier.ts`) uses prefix-agnostic detection, covering 12+ UI libraries.

2. **Identifiable custom structures via class/tag/id** — e.g. `class="xx-select"`, `role="listbox"` and other developer-named components, classified by pattern matching.

3. **Standard HTML semantic elements** — `<table>`, `<input>`, `<select>`, `<button>`, `<a>`, etc., processed according to native semantics.

4. **Unclassifiable elements** — recursively walkChildren to extract child node structure. If visible content exists but cannot be extracted, produces a `type: 'custom'` node with `localHtml` (max 500 characters).

### Element Type Rules

**Tables**: Extract headers and row data. Each cell in each row goes through the unified `walkNode` processing path (not plain text extraction). A `table` node has both `rows` (text summary for frontend display) and `children` (full structure from walkNode for Agent analysis).

**Iframes**: Same-origin iframes are recursively parsed via `contentDocument` (following the same rules); cross-origin iframes are silently skipped. Produces a section node with `blockType: 'iframe-content'`. Multi-level nested iframes are supported.

**Navigation areas**: Detected via HTML5 semantic tags (`nav`, `aside`, `header`, `footer`) and ARIA roles (`role="navigation"`, etc.) **outside** the main content root. Supports nested submenus (e.g. `el-submenu` + `aria-haspopup`). Leaf nodes are `link` or `button` types with `href`, `active` state, and `selector`. **Navigation and menu content must never be skipped or discarded** — they are essential for cross-system operation scenarios.

**Form containers**: Detected via known form-item patterns (`.el-form-item`, `.ant-form-item`, etc.), processed as label + control pairs. If the content area contains multiple interactive elements (≥2 non-simple controls, or ≥3 simple controls), recursively expanded as `group` + `children` rather than flattened into a single leaf node. If processFormItem returns empty (e.g. `el-form-item__actions` is actually a button container), **falls back** to generic walkChildren.

### Multi-Frame Initial State Merging

A page may contain multiple frames (top-level + one or more iframes, iframes may be nested). Each frame independently runs a content script and sends `RECORDING_INITIAL_STATE`. The background's `setInitialState` (`state.ts`) handles this as follows:

- **Duplicate sends from the same frameId** (e.g. content.ts two-pass) → score-based competitive replacement (keep the higher-scoring one)
- **Different frameIds** → **always merge**. The iframe's stateTree is appended as an `iframe-content` section to the existing state. Regardless of nesting depth or iframe count, every frame's content is preserved
- **Never replace instead of merge** — top-level frame navigation/menus and iframe business content are equally important; a higher node count or score in an iframe must not overwrite the top-level content

### Visibility Handling

All walk logic uses unified visibility handling — **never skip invisible elements**. `shouldSkip` only filters `SKIP_TAGS` (script/style/svg and other purely technical tags) and does not check `isVisible`. Invisible elements (`display:none`, `visibility:hidden`) are still parsed and annotated via the `cssState` field. `display:none` means not rendered and not clickable (e.g. collapsed menus); `visibility:hidden` means occupies space but still receives interaction.

**Different walk types (navigation vs content) must not use different visibility handling** — all walks share the same rules.

### Truncation Fallback

When `MAX_NODES` (300) or `MAX_NAV_ITEMS` (100) cause collection to be truncated, **remaining content must not be silently discarded**. Truncated navigation areas get `localHtml` attached to the section node, preserving the original HTML for future expansion.

### Information Retention Principle

Prioritize information with analytical value for the Agent to understand page functionality: what the page does, what interactive elements exist, what the current state is. Information with no immediate analytical value but potentially needed later (e.g. complete navigation menu raw HTML) is stored in `localHtml`, outside the Agent's primary analysis pipeline.

### Prohibited Practices

- **Never skip elements based on assumptions** — no hardcoded skip lists (except `SKIP_TAGS`). All elements must be processed (including invisible ones). Never assume developers follow semantic HTML conventions.
- **Never decompose known compound components** — `el-select` is one `select` node, not `input` + `div` + `ul`. Component boundaries are classification boundaries.
- **Never produce empty containers** — section/group nodes with empty children must be discarded.
- **Never silently discard content** — any classification failure must fall back to generic recursion; if generic recursion also fails and visible content exists, must produce localHtml fallback. Truncated content must preserve localHtml.
- **Never flatten complex structures** — if a container has multiple interactive child elements, must recursively expand into a subtree, not flatten into a single leaf + localHtml.
- **Never add specialized logic** — all processing rules must be generic, no if-else branches targeting specific component libraries or page structures. All walk types share the same filtering and processing rules.
- **Never restructure page structure for semantic tidiness** — do not merge parallel siblings into "title + content" blocks, do not alter node boundaries for "clarity", do not reorder nodes for "neatness", do not swallow intermediate tip/alert/button group/status text to form "title + content" patterns.
- **Never degrade complex cells to plain text** — table image columns must preserve `src`, action columns must preserve real buttons, input-number must be preserved as structured controls.
- **Never concatenate multiple buttons into a single string** — buttons must be preserved as individual nodes.
- **Never keep only the primary control while ignoring sibling auxiliary information** — tip/description/status text within a form-item must be preserved.

### Output Structure

- **Container nodes** (`section`, `group`): have `children[]`, `blockType`, `label`. **No `selector`**. May carry `localHtml` when truncated.
- **Leaf nodes** (`input`, `select`, `button`, `link`, `custom`, etc.): have `selector`, `value`, `label`. **No `children`**.
- **`table` nodes**: can be leaf (`rows[][]`) or container (`children[]`), depending on cell complexity.
- **`localHtml`**: only on leaf nodes where semantic extraction is insufficient, max 500 characters.
- **`rawHtmlSnapshot`**: standalone debug-only full HTML snapshot, not part of the AST.

### Tests

Multi-scenario tests (`apps/extension/src/__tests__/multi-scenario.test.ts`) cover 8 fixture types: corporate website, admin panel, H5 mobile, multi-nav docs page, no-semantic-tags page, data dashboard, Element UI nested menu + iframe, and complex nested structures (form-item with embedded tables/sub-forms, table action columns). **Any parser change must pass all existing fixture tests. New parsing behavior must include corresponding fixtures and tests.**

### Reference Test Case

`apps/extension/src/__tests__/fixtures/lottery-page.html` is a full HTML fixture from an actual user page. `apps/extension/src/__tests__/fixtures/lottery-page-expected.jsonc` is the **current (problematic) parser output**, with specific issues annotated via `//` and `/* */` comments. This is NOT the correct expected output — it is a problem checklist. New parser changes must address all annotated issues.

## Infrastructure

Docker Compose (`infra/docker/docker-compose.yml`) provides:
- **PostgreSQL 16** — primary database
- **Redis 7.4** — caching/queuing
- **MinIO** — object storage (ports 9000 API, 9001 console)

Copy `.env.example` to `.env` at repo root. Console has its own `apps/console/.env.example`.

## Worker

The worker (`apps/worker/app/`) runs a polling `JobRunner` loop. Currently a scaffold — heartbeat logging is implemented but job execution logic is not yet built out.
