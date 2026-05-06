# Product Model — WebAgentFlow

> This document is the **product baseline** — the current shared
> understanding of what WebAgentFlow is. Treat it as a general outline,
> not a rigid constitution.
>
> - When the **product direction** changes (a new lifecycle stage, a new Agent
>   role, an invariant shifts), update this doc first, then the code.
> - Day-to-day implementation details don't need to round-trip through
>   this doc — just keep the overall shape consistent.
> - If a proposal doesn't fit any lifecycle stage / Agent here and feels like a
>   product-level addition rather than an implementation detail, pause
>   and check with the user before writing code.

---

## Terminology (lifecycle stages vs. delivery milestones)

The word "phase" previously described two different things: the product
lifecycle of a page, and the engineering roadmap. That made planning
ambiguous. From this document forward, use these names:

- **Lifecycle Stage L1 / L2 / L3** — the fixed product lifecycle a page
  goes through in WebAgentFlow:
  autonomous learning → user-guided learning → actual work. Defined in
  §3–§6. The count is fixed at three.
- **Delivery Milestone M10 / M11 / ...** — engineering milestones tracked
  in [`roadmap.md`](./roadmap.md). The count grows over time. Existing
  iteration directories keep their legacy names such as
  `docs/iterations/phase-10/` to avoid churn, but the roadmap should call
  the milestone **M10**.
- **§N** — section number *within this document*, used for
  cross-references only.

Do not write a bare "Phase 3" or "Phase 10" in new product planning.
Use "L3 Actual Work" for the product lifecycle stage, and "M10 Path
Asset Foundation" for the delivery milestone.

---

## 1. One Sentence

WebAgentFlow aims to replace the user at the keyboard on web pages:
it first learns a page well enough to operate it, and is **gradually
moving toward** executing user-submitted tasks by driving a real
browser — not by asking an LLM to click things step-by-step.

## 2. System Role Boundaries

Before the lifecycle stages, a note on **who does what**. These boundaries are
easy to forget mid-session and lead to the system quietly drifting
into the wrong shape.

- **WebAgentFlow engine** (code + in-product Agents) — the runtime.
  Fetches pages, analyzes, tries actions via Playwright, runs the
  Supervisor. It is the one that actually does the work at runtime.
- **Workbench UI** (`/exploration/autonomous`) — the operator's
  window. It's where the user **observes** what the engine is doing,
  **manually triggers** runs during development, and **accepts or
  rejects** results. It's not the engine; it's the glass in front of
  the engine.
- **User** — the operator. Triggers runs, reviews results, gives
  corrections. During L2 (user-guided learning) the user is the
  actual operator of the page, not a reviewer. The operator is assumed
  to have the right to operate the target website they ask
  WebAgentFlow to operate.
- **AI coding agents** (Claude Code, Codex, …) — build and maintain
  the engine. They are **not** in the runtime loop. They must not
  run the app on the user's behalf and report results back, because
  doing so collapses the user's ability to tell "the app works" from
  "the AI agent faked it with scaffolding". (See `CLAUDE.md`
  §"AI Coding Agent — Execution Boundary" for the hard rule.)

**Runtime environment**: the engine drives an **independent Chromium
bundled with the app** (installed via `playwright install chromium`),
not the user's own browser. In order of importance:

1. **Safety / isolation** — the user's cookies, logged-in sessions,
   bookmarks, extensions, and history are never touched by the
   engine, and vice versa. This matters for enterprise users where
   data hygiene is a hard requirement.
2. **Controlled environment** — everyone runs the same Chromium
   build, with no noise from user-side extensions or profile state.
3. **Room for extension** — surfaces to inject the engine's own UX
   (Agent chat overlay, instrumentation) and to install plugins or
   apply deeper browser customization later.

Session state is handled by the operator and the target website. If a
page requires an existing session, the operator establishes or refreshes
that state through the target website's own flow in the engine-controlled
browser context. Cookies, `localStorage`, and session expiry remain
target-site concerns; when they expire or redirect, the run enters
recovery / user-communication flow.

When in doubt about where a new feature belongs, place it on this
axis first: is it engine logic, workbench glass, operator workflow,
or developer tooling? Different axes, different review standards.

## 3. Three Lifecycle Stages of a Page

Every page goes through three lifecycle stages in WebAgentFlow's
lifetime. Features belong to exactly one lifecycle stage. Don't blur
them.

| ID | Lifecycle stage | Who drives | Does an LLM read raw HTML per step? |
|---|---|---|---|
| L1 | Autonomous Learning | System | Yes — bounded, during learning only |
| L2 | User-Guided Learning | User (in a visible browser) | No — system records the user |
| L3 | Actual Work | System, from learned data | **NO** — this is the core invariant |

The rest of this document fills in each lifecycle stage, the Agents
involved, and the invariants that must not be violated.

---

## 4. L1 · Autonomous Learning

**Trigger**: The system encounters a page it has not learned (or the
user forces re-learning).

### 4.1 Pipeline

Sequential steps. Every step has a clear input/output contract so
components can be replaced independently.

1. **Fetch HTML → Full AST** (server-side, `lxml`).
   DOM-faithful; no semantic rewriting.
2. **Full AST → Simplified AST** (structure-preserving projection).
   Simplified AST removes noise but preserves node boundaries and
   sibling order. It is NOT a "page summary".
3. **Agent A · Page Intent Agent** reads the Simplified AST plus a
   screenshot and writes down what the page is for.
   - Output: a short page-purpose description, persisted with the
     page signature.
   - This is semantic understanding, not operable-element extraction.
4. **Code** (deterministic, no LLM) extracts operable elements from
   the page: fillable / submit / clickable / navigation / select /
   toggle. Classification is structural only.
5. **Code** drives Playwright to try operations on those elements and
   records what happened — including the failures. Failure paths are
   kept as negative knowledge, not discarded.
6. **Agent B · Attempt Evaluator Agent** judges each attempt's
   outcome and flags anomalies.
   - Output: per-attempt verdict + summary. Independent of Agent A.
7. **Agent C · Learning Reporter Agent** (presentation layer, low
   priority) compiles the full learning session into a report for
   the user.
   - Output: user-facing report (what the page is, what the system
     can do on it, what it couldn't figure out).
   - **Not a prerequisite** for the learning loop to function. The
     loop is complete once steps 1–6 + 8 run; C is UX polish on top
     of that data. Prioritize accuracy in A / B / 4 / 5 before
     investing in C.
8. **Persist** as a learned page record:
   - page signature
   - page purpose (from Agent A)
   - operable elements (from step 4)
   - successful paths (from step 5, verdict=success)
   - failed paths (from step 5, verdict≠success) — kept as negative
     knowledge to avoid repeating mistakes.

### 4.2 What L1 deliberately is not

- Not a skill registry. The learned record is a data blob keyed by
  page signature, not a named skill.
- Not a single god Agent. Agents A / B / C are separate prompts with
  separate outputs and separate failure modes. Don't fuse them.
- Not permanent. Re-learning is supported. A page can be re-learned
  when it changes, or when the user corrects something.

---

## 5. L2 · User-Guided Learning

**Trigger** (either):

- The user explicitly enters guided-learning mode for a page the
  system already knows partially (to fill a gap).
- The user **takes over** during L3 execution (error recovery or
  explicit hand-off). Take-over automatically becomes guided learning
  — the system records everything the user does from that point.

### 5.1 Pipeline

1. System opens the page in a **visible** Playwright browser (not
   headless — the user is driving).
2. User operates the page normally.
3. System records each interaction:
   - which selector was used (resolved from the real event target)
   - what value was typed / what was clicked
   - what observable state changed after the interaction
4. Captured operations are appended to the page's learned record,
   marked with `provenance = user`, and participate in L3 route
   planning the same way L1 paths do.

### 5.2 Invariant

L2 records the user's real actions. It does **not** infer intent
via LLM, and it does **not** retroactively rewrite what the user did.
Provenance is preserved so later reviews can trust it.

---

## 6. L3 · Actual Work

This is the lifecycle stage that matters to the end user. Everything in
L1 and L2 exists to make L3 cheap, fast, and reliable.

**Trigger**: The user submits a task ("log into X and download the
weekly report as CSV", etc.).

### 6.1 Run shape — happy path is not the whole picture

A real L3 run is **not** a straight line from plan to report.
It's a loop that can branch any time the page disagrees with what
the learned record expected:

```
plan (D) → execute → observe → ok?  ─── yes ──→ report (E)
                                │
                                └── no ──→ recovery dialogue (F)
                                             ├── re-plan   ──→ back to execute
                                             ├── re-run    ──→ back to plan
                                             └── hand off  ──→ L2 mode
```

Triggers that flip a run off the happy path:

- action hits an error (timeout, not-found, server 5xx)
- observable state doesn't change when the learned path said it should
- page has drifted (element moved, selector stale, layout changed)
- user aborts (§6.5)

The sections below describe each arm. "Happy path" is just the
sunny-day subset; the error / drift / handoff arms are first-class,
not exception cases.

### 6.2 Happy-path pipeline

1. **Agent D · Path Planner Agent** reads:
   - the user's task description
   - the learned record(s) for the target page(s)

   and picks a route. A route is a sequence of concrete actions
   (selector + action_type + value) drawn from the learned paths.

   Agent D **never reads raw HTML**. It only reads learned data. Its
   job is "pick the right pre-verified path", not "figure out what to
   click from scratch".

2. **Code** executes the chosen route via Playwright.
   - Selectors, values, action types are fully deterministic — they
     came from learned data, not from an LLM decision in the loop.
   - Each action's observation (URL before/after, DOM signals, etc.)
     is recorded for the reporting Agent.

3. **Agent E · Result Reporter Agent** summarizes the outcome for
   the user. Output: natural-language result + structured fields the
   UI can render.

### 6.3 The core invariant

During L3 execution, **LLMs are only invoked at boundaries** —
planning at the start, reporting at the end, recovery / abort
dialogue, or a user-teaching / handoff boundary. They are **never**
invoked to decide the next click, the next keystroke, or which field
to fill, because those decisions are already encoded in the learned
record.

This is non-negotiable. It is the thing that makes WebAgentFlow
different from "LLM watches the browser and clicks around". Break
this and you've built a different product.

### 6.4 Error handling

When an action fails (page error, element not found, observable state
didn't change, server returned 5xx, etc.):

1. Execution **pauses**. It does NOT silently retry.
2. **Agent F · Recovery Dialogue Agent** opens a dialogue with the
   user:
   - what happened
   - which step failed
   - what the system thinks the options are
3. Based on the user's reply, the system does one of:
   - **Re-plan and continue**: Agent D re-picks a route, taking the
     new context into account. Execution resumes.
   - **Re-execute from start**: used when partial state is unsafe.
   - **Hand off to the user**: enters L2 mode. The user finishes
     the task manually; their actions are recorded and fed back into
     the learned record.

### 6.5 User-initiated abort

The user can stop the run at any time. When they do:

1. Execution pauses immediately.
2. **Agent G · Abort Dialogue Agent** opens a dialogue:
   - what was done so far
   - what state the page is in
   - what the user wants next (resume / restart / hand over / drop)
3. The system acts on the user's reply.

Abort is different from error: abort is the user intervening on a
run that was otherwise going fine. Different Agent, different prompt,
different tone.

---

## 7. The Agents (single reference table)

These are separate Agents. Don't merge them. Different prompts,
different inputs, different outputs, different models over time.

| ID | Name | Lifecycle stage | Reads | Produces |
|---|---|---|---|---|
| A | Page Intent Agent | L1 | Simplified AST + screenshot | Page purpose description |
| B | Attempt Evaluator Agent | L1 | Attempt log + before/after state | Per-attempt verdict + anomalies |
| C | Learning Reporter Agent *(low priority, presentation)* | L1 | Full learning session | User-facing learning report |
| D | Path Planner Agent | L3 | User task + learned record | Chosen concrete route |
| E | Result Reporter Agent | L3 | Execution outcome | User-facing result |
| F | Recovery Dialogue Agent | L3 (error) | Error context + recent steps | Dialogue transcript + next action |
| G | Abort Dialogue Agent | L3 (user abort) | Current state + abort signal | Dialogue transcript + next action |

When adding a new capability, first ask: **which Agent does this
belong to?** If the answer is "a new one", that's a product-level
decision — update this document before adding it.

---

## 8. Cross-Cutting Invariants

Invariants that apply across all lifecycle stages. Violations are product bugs,
not implementation details.

1. **LLMs never drive per-step execution in L3.** Only planning
   / reporting / dialogue.
2. **Failure is data.** Failed attempts in L1 are persisted, not
   discarded.
3. **Provenance is preserved.** Every learned action knows whether
   it came from L1 (system) or L2 (user).
4. **Re-learning is allowed.** A page can be re-learned when it
   drifts; the system must not assume learned data is permanent.
5. **No silent retries.** Errors produce dialogue, not hidden
   back-off loops.
6. **Learning and execution are different code paths.** Reusing
   L1 orchestration to run L3 tasks is a smell; L3
   should be boring and deterministic.

---

## 9. Where the current codebase sits

Honest mapping, so the gap between the vision and the code is
visible. Keep this section updated as lifecycle stages and milestones ship.

- **L1 steps 1–2 (HTML → AST → Simplified AST)**: shipped as
  server-side parsing (`html_ast_parser.py` + `ast_simplifier.py`).
  Autonomous exploration currently uses a live-page analyzer
  (`page_analyzer.py`) rather than the offline AST pipeline;
  reconciling the two views is open work.
- **L1 step 3 (Page Intent Agent)**: not yet built as a
  separate Agent. Today's Supervisor mixes intent-understanding and
  evaluation concerns.
- **L1 steps 4–5 (element extraction + trial)**: shipped in the
  autonomous exploration subsystem.
- **L1 steps 6–8 (evaluation + report + persist)**: partial.
  Verdict + 5-score verification scorecard + Supervisor summary
  exist as exploration-stage artifacts. A **product-form,
  user-facing learning report is still exploratory** — current
  output is a developer-oriented debug surface, not the final shape
  Agent C should produce. **Persist-as-learned-record shipped in
  delivery milestone M10.1** — `pass_gate = pass` runs
  auto-ingest as `learned_paths` rows keyed by
  (page_template, query_signature, dom_fingerprint, scenario), with
  a trust lifecycle (`provisional` / `confirmed` / `flaky` /
  `deprecated`) the operator drives via the run-detail page.
  Replay / drift detection against stored paths is being planned in
  M10.2.
- **L2 (User-Guided Learning)**: not started. The 2026-04-20
  cleanup removed the old Chrome extension; L2 will be built
  from scratch on top of a **visible** Playwright browser (per §5.1),
  not on the extension. No guided-learning mode exists today.
- **L3 (Actual Work)**: not started. No Path Planner Agent, no
  task-to-path execution loop, no recovery dialogue. Replay / drift is
  the M10 foundation; M11 is the first planned L3 happy-path MVP.

When a lifecycle stage fully lands, update this section to reflect it.

### 9.1 Delivery milestone alignment

The current delivery plan intentionally separates path assets from real
task execution:

| Milestone | Product role | Internal Agents |
|---|---|---|
| M10 · Path Asset Foundation | Make LearnedPaths reusable: persistence, catalog, replay, drift detection. | No new Agent; provides execution substrate. |
| M11 · Task-to-Path Planning MVP | First L3 happy path: user task → choose / bind LearnedPath → execute → report. | Agent D · Path Planner Agent; Agent E · Result Reporter Agent. |
| M12 · Recovery & Handoff | L3 failure and abort branches: pause, explain, re-plan, re-run, or hand off. | Agent F · Recovery Dialogue Agent; Agent G · Abort Dialogue Agent. |
| M13 · User-Guided Learning & Correction | L2 visible-browser takeover plus path correction / provenance write-back. | No new Agent by default; preserve user provenance. |
| M14 · Learning Quality Agents & Coverage | Revisit L1 quality: page purpose, simple attempt evaluation, learning report, richer controls and patterns. | Agent A · Page Intent Agent; Agent B · Attempt Evaluator Agent; Agent C · Learning Reporter Agent. |
| M15 · Automated Evaluation & Continuous Optimization | Regression runs, drift alerts, quality trend tracking. | Reuses Agent B / Supervisor-style evaluation; no new Agent by default. |
| M16 · External Interfaces | Stable API / CLI / Skill / Tool surface for external schedulers. | No new product Agent; exposes existing capabilities. |

M10.2 replay is still valuable after this reshuffle: it is the first
deterministic consumer of LearnedPath data. It does **not** implement
Agent D or L3 task planning; it gives M11 something safe to call.

---

## 10. Open-source delivery forms

WebAgentFlow is not only a UI-fronted application — it should also
exist as an **independently runnable, externally callable open-source
tool**. This section describes *how the engine's capabilities can be
opened up to the outside world*, not a new lifecycle stage.

### 10.1 Two delivery shapes

WebAgentFlow supports (at least) two shapes of use:

1. **Complete application**
   - Users interact through WebAgentFlow's own UI.
   - Learning, running, reviewing, and taking over all happen in a
     visible environment.
   - This is the primary shape for end users.

2. **Capability-open shape**
   - Learning, planning, execution, and verification capabilities are
     exposed through stable interfaces.
   - External systems or third-party Agents can call them.
   - Callers include but are not limited to: Codex, Claude Code,
     OpenClaw, or other Agent / automation systems.

### 10.2 Scope of exposed capabilities

What's exposed outward is not "the whole product UI" but a set of
explicit capability units. At minimum:

- **Page learning**
  - Structural analysis of a page.
  - Extraction of operable elements.
  - Output: page understanding, attempt results, learning report.
- **Path planning**
  - From existing learned data, **select / compose / fill gaps in**
    an executable route for a concrete task. Never fabricate a new
    route from scratch at runtime.
- **Execution**
  - Automated browser operations against a real page.
  - Returns per-step execution log, observable state changes,
    outcome.
- **Verification**
  - Rule-based verification / spec comparison / internal-Agent review
    of an execution result.
- **User-guided learning recording**
  - When the user takes over, record the user's real actions to
    supplement learned data.

### 10.3 Interface shapes

The capabilities above should be reachable via at least three
entry shapes:

1. **API**
   - For machine-to-machine calls over HTTP / streaming.
   - The standard remote entry.
2. **CLI**
   - For developers to invoke a capability directly from the terminal.
   - Fits debugging, batch jobs, script or CI integration.
3. **Skill / Tool form**
   - For third-party Agent frameworks to treat WebAgentFlow as an
     invokable tool.
   - The external Agent decides *when* to call.
   - WebAgentFlow does the actual browser work.

### 10.4 Role relationship

Even with a CLI / Skill / API, the role relationship does not change:

- **WebAgentFlow** is the page-learning and page-execution engine.
- **External Agents** are schedulers — they decide what to call and
  when, but they do not step-by-step operate the browser themselves.
- **The user** is the final confirmer, and can take over at any
  point — which re-enters L2 user-guided learning.

A third-party Agent may call WebAgentFlow, but should not replace
WebAgentFlow with its own per-step browser automation.

> **Clarification — three kinds of "Agent" appear near this document,
> don't confuse them**:
>
> 1. **Product-internal Agents A–G** (§7) — roles that run *inside*
>    WebAgentFlow at runtime (Page Intent, Path Planner, Recovery Dialogue,
>    …). Defined by this document.
> 2. **Third-party Agent** (this §10) — an *external* runtime
>    scheduler that calls WebAgentFlow's CLI / Skill / API to get
>    browser work done. Not part of WebAgentFlow.
> 3. **AI coding agent** (Claude Code, Codex, …) — a development-time
>    tool operating on this repository. **Not in the runtime loop at
>    all.** Bound by `CLAUDE.md` §"AI Coding Agent — Execution
>    Boundary" regardless of whether §10 CLI / Skill entries exist.

### 10.5 Boundaries when exposing capabilities

Opening capabilities outward does NOT relax the existing invariants:

- In L3 actual work, LLMs still don't enter the per-step
  execution loop.
- Execution is still done by code + browser automation.
- Failure, take-over, and recovery dialogue still follow the
  L1/L2/L3 lifecycle model.
- External interfaces are a different *way to call*, not a different
  *product logic*.

### 10.6 Current state and priority

This section describes a **long-term delivery direction**. Not all of
it is shipped, and **its current priority sits below landing the
L1/L2/L3 main loop itself** — L3 actual work must be stable
and useful before heavy investment in CLI / Skill / API surface area
is justified.

Current codebase has part of the foundation:

- Browser execution and exploration capabilities.
- Page analysis / action planning / verification.
- Autonomous workbench as the operator's trigger + observation surface.

Pending:

- A more stable CLI entry.
- A clearer Skill / Tool interface definition.
- Calling conventions oriented at third-party Agents.
- Capability boundaries and I/O contracts for external callers.

### 10.7 Instance-local data

The engine's data boundary is **one running instance**. WebAgentFlow
persists only engine artifacts inside that instance: LearnedPaths,
trust records, and feedback history.

"Real-user data fine-tuning" is not a separate mechanism. It is the
L1/L2/L3 lifecycle model operating on *this instance's* pages: the
user demos during L2, confirms or rejects during L3 review, and the
engine's LearnedPath store adapts over time.
More usage on an instance → more signal → better behavior, scoped to
that instance.

Session expiry, redirects, permission denial, or missing authorization
are runtime recovery / user-communication events.

Invariants:

- The engine MUST NOT embed instance identity into LLM prompts, logs,
  SSE events, or outbound reports.
- The engine MUST NOT push learned data out of the instance on its own.
- Persistence code SHOULD stay behind ordinary repository boundaries,
  without speculative ownership or storage abstractions.

This framing was made explicit in delivery milestone M10 alongside
LearnedPath persistence. Before that, "one instance = one user's data"
was implicit.

---

## 11. Related Docs

- [`architecture.md`](./architecture.md) — how the code is organized
  (layers, AST dual-track, services sub-packages). Complements this
  doc; doesn't replace it.
- [`roadmap.md`](./roadmap.md) — operational view: what's shipped
  vs. in progress vs. next.
- [`scope-boundaries.md`](./scope-boundaries.md) — what's deliberately
  NOT being built right now.
- [`product-model.zh.md`](./product-model.zh.md) — Chinese mirror.

---

§10 describes *how WebAgentFlow's capabilities can be opened up for
external use*, not a new lifecycle stage. It sits on top of the
L1/L2/L3 lifecycle model; it does not replace it.
