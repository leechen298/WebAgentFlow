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

Earlier docs used one label for two different things: the product lifecycle
of a page, and the engineering roadmap. That made planning ambiguous. From
this document forward, use these names:

- **Lifecycle Stage L1 / L2 / L3** — the fixed product lifecycle a page
  goes through in WebAgentFlow:
  autonomous learning → user-guided learning → actual work. Defined in
  §3–§6. The count is fixed at three.
- **Delivery Milestone M10 / M11 / ...** — engineering milestones tracked
  in [`roadmap.md`](./roadmap.md). The count grows over time. Iteration
  directories use milestone names such as `docs/iterations/m10/`.
- **§N** — section number *within this document*, used for
  cross-references only.

Use the L/M vocabulary in new product planning: "L3 Actual Work" for the
product lifecycle stage, and "M10 Path Asset Foundation" for the delivery
milestone.

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
- **Target website** — owns its own cookies, `localStorage`, session
  state, permissions, and authorization outcomes. WebAgentFlow does
  not replace that responsibility.
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

WebAgentFlow only cares about how to operate the target web page. The
default assumption is that the WebAgentFlow operator is already allowed
to perform the intended actions on that page.

Session state is handled by the operator and the target website. If a
page requires an existing session, the operator establishes or refreshes
that state through the target website's own flow in the engine-controlled
browser context. Cookies, `localStorage`, session expiry, and target-site
permissions remain target-site concerns. When login state expires, the
page redirects back to login, permission is denied, or an operation
fails, the run enters runtime failure / recovery / user-communication
flow.

When in doubt about where a new feature belongs, place it on this
axis first: is it engine logic, workbench glass, operator workflow,
or developer tooling? Different axes, different review standards.

### 2.1 Runtime Conversation Surface

The user always talks to **WebAgentFlow** as the application, not
directly to Task Path Planner (legacy: Agent D), Failure Recovery Agent
(legacy: Agent F), User Abort Handler (legacy: Agent G), Teaching Guide
Agent (legacy: Agent H), or any other internal Agent. Internal Agent
names are implementation roles; the runtime product surface speaks in
the unified WebAgentFlow voice.

The first useful conversation surface can be **CLI-first**. CLI-first is
about getting the full product loop working end to end: task input,
pre-execution confirmation, failure recovery, user abort, teaching-mode
dialogue, and final result reporting. A developer-capable user can also
use CLI / API to embed WebAgentFlow into their own system or build their
own operator console around it.

This runtime conversation surface is not M16's external scheduler
interface, and it is not today's `verify-scenario` development
verification tool. It is the product's runtime entrypoint.

### 2.2 Conversation Orchestrator / Dispatcher

Runtime conversation needs a code-side **Conversation Orchestrator /
Dispatcher**. It is not a new all-purpose LLM Agent. It is a session
controller and internal Agent router.

Responsibilities:

- maintain session state
- receive user messages and engine events
- route work to Task Path Planner, Task Result Reporter, Failure
  Recovery Agent, User Abort Handler, and Teaching Guide Agent at the
  correct boundary
- manage confirmation, pause, resume, abort, takeover, and teaching mode
- enforce the L3 invariant that LLMs do not enter the step-by-step
  browser execution loop
- produce user-facing text from the WebAgentFlow perspective, not from
  individual internal Agents

Example states:

- `idle`
- `task_planning`
- `awaiting_confirmation`
- `executing_path`
- `recovery_dialogue`
- `abort_dialogue`
- `guided_teaching`
- `user_demonstration`
- `reporting_result`

### 2.3 Conversation Intake Agent

`wagent chat` needs a controlled natural-language intake layer before the
Conversation Orchestrator can route work safely. This role is the
**Conversation Intake Agent**.

It is not a browser operator. It does not click, fill, call Playwright,
select a LearnedPath, or produce step-by-step browser actions. Its job is to
turn a user's natural-language message into a schema-constrained structure:
intent, target URL / site origin, action goal, slots, missing fields, and
clarification hints.

The Conversation Orchestrator remains responsible for session state, target
scope validation, learned-action matching, user-facing wording, and whether
learning or replay may run. A canonical goal from the intake layer is only a
matching aid; it is not execution authorization.

First principle:

```text
The LLM understands what the user said.
The code decides whether and how WebAgentFlow acts.
```

Responsibility matrix:

| Surface | Owner | What LLM may do | What code must do |
|---|---|---|---|
| Natural-language intake | Conversation Intake Agent | Extract intent, target, action goal, slots, missing fields, and clarification hints. | Validate the schema, reject unsafe output, and decide whether the result can move forward. |
| Conversation memory | Conversation Orchestrator / code | Use the provided session context to resolve references such as "this page" or "the previous page". | Persist and clean `pending_intake`, future `pending_target`, recent message summaries, and no-path context. |
| Learned action matching | Conversation Orchestrator / code | Suggest semantic aliases for the user's action goal. | Match only current-session learned actions within the correct `target_url` / `site_origin` scope. |
| Learning / replay permission | Conversation Orchestrator / code | Provide a user-intent hint. | Decide whether learning or replay is allowed; enforce confirmation, scope, and safety rules. |
| Browser operation | Learning / Replay services | Do not participate in step-by-step execution. | Open Playwright, fill fields, click buttons, replay LearnedPaths, and collect execution evidence. |
| User-facing wording | Conversation Orchestrator | Provide wording hints for clarification or failure cases. | Generate or filter final `user_response`; never expose schema, confidence, slot, JSON, or internal trace jargon to end users. |
| Evidence and history | Code | Summarize intent when useful. | Persist events, response provenance, redacted LLM traces, learning runs, replay summaries, and sensitive redaction. |

M11.3.4 implements the intake/provenance foundation. The next step is M11.3.5:
Customer-Facing Agent Router & Skill Runtime. It does not merely patch
bare-URL recovery. It defines how WebAgentFlow gathers conversation/page
context, asks an Agent Router for a next-step recommendation, lets code
adjudicate that recommendation, and executes only registered application
skills.

### 2.4 Response Provenance and LLM Trace

As `wagent chat` moves from code-only replies to LLM-backed intake and future
LLM-backed reporting, every user-visible WAgent reply needs a provenance record.

Response provenance answers:

- Was this reply generated by deterministic code, by an internal Agent, or by a
  hybrid path?
- Which product runtime component produced the reply?
- If an LLM was involved, which provider, model, schema, request id, and raw
  redacted trace back it?
- If a failure reply was generated by an Agent, where is the trace?

This is a runtime observability concept under the Conversation Intake Agent
track, not a new execution Agent. Codex CLI can operate CLI / Console surfaces
and read history when the user asks it to test or debug, but it is not a
WebAgentFlow internal Reply Producer.

Response provenance must not pollute LearnedPath, replay result, page
observation, Supervisor verdict, or pass-gate evidence. LLM traces may be kept
as conversation evidence only, and raw records must be redacted before they are
shown in history or copied from debug JSON.

### 2.5 Customer-Facing Agent Router and Skill Runtime

M11.3.5 introduces a product-level distinction that must hold even if the first
implementation keeps several pieces in the same Python module:

```text
Customer-Facing Agent Router != Conversation Orchestrator
```

The **Customer-Facing Agent Router** is an internal Agent role. It receives the
current user message, the Conversation Intake result, code-collected
conversation context, optional page understanding, learned-action summaries, and
the registered application skill menu. It answers one question:

```text
What should WebAgentFlow try next, and which worker Agent or application skill should
handle it?
```

The Router does not call tools, open browsers, select LearnedPaths as
authorization, or execute skills. It produces a schema-constrained route
recommendation.

The **Conversation Orchestrator** remains the code-side controller. It answers a
different question:

```text
Is this recommendation allowed to run, and who actually runs it?
```

The Orchestrator owns session state, target resolution, `pending_target`,
`pending_intake`, learned-action scope checks, MVP boundary checks, confirmation policy,
skill invocation, progress events, history, provenance, and final
user-facing wording.

The **Application Skill Registry** is the application ability menu, not an
Agent list. A skill is a bounded, auditable application operation. Earlier
drafts used "capability"; new M11.3.5 docs should use "skill" consistently.
The first registry includes:

- collect conversation context
- inspect a target page
- understand a page
- look up learned actions
- ask the user for missing information
- start learning
- start replay
- learn then execute
- record progress
- record Agent trace

Worker Agents may request skills through the Orchestrator / Skill Runtime:

- **Page Understanding Agent** reads a page-context bundle and returns page
  summary, visible controls, supported goals, and required slots. It must not
  output selectors, browser steps, or page-classification contracts.
- **Learning Agent** organizes the learning flow and requests `start_learning`.
  It is distinct from the autonomous exploration Supervisor, which only
  evaluates run outcomes.
- **Web Operation Agent** organizes execution requests and may request
  `lookup_learned_actions`, `start_replay`, or guarded `learn_then_execute`.
  It must not invent browser steps or cross target scope.

The existing product infrastructure is part of this design rather than a
parallel implementation track: HTML-to-Full-AST, Full-AST-to-Simplified-AST,
PageAnalysis, form-label extraction, action planning, Playwright execution,
ExplorationRun step history, LearnedPath model / actions, wait-for-change
signals, replay observation, task planning schemas, and response provenance all
feed the Router / Skill Runtime boundary.

LLM-backed Agent prompts are managed as versioned prompt assets, not long
strings embedded in service functions. Prompt files live under the API prompt
asset tree, each Agent owns its own prompt file and metadata, shared fragments
hold only generic WebAgentFlow boundaries / evidence / redaction / structured
output rules, and LLM traces record prompt id, version, content hash, schema,
provider, model, and redaction state.

Responsibility summary:

| Surface | Router may do | Orchestrator / code must do |
|---|---|---|
| Next-step choice | Recommend ask / inspect / understand / learn / replay / learn-then-execute. | Validate schema, target, confidence, skill preconditions, and the M11.3.5 MVP boundary. |
| Page understanding | Request or use semantic page summaries. | Build page context from real runtime evidence such as AST, PageAnalysis, URL, title, and learned actions. |
| Learned action matching | Suggest semantic goal aliases. | Match only current-session learned actions within the correct target URL / site origin scope. |
| Skill use | Recommend a registered application skill. | Invoke the skill and record progress / trace. |
| Browser operation | Never. | Delegate to Learning / Replay / execution services only. |
| User-facing response | Provide a short reason hint. | Generate the final WAgent response and hide internal Agent names unless the user is viewing debug history. |

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
3. **Page Understanding Agent (legacy: Agent A)** reads the Simplified AST plus a
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
6. **Attempt Evaluation Agent (legacy: Agent B)** judges each attempt's
   outcome and flags anomalies.
   - Output: per-attempt verdict + summary. Independent of Page
     Understanding Agent.
7. **Learning Report Agent (legacy: Agent C)** (presentation layer, low
   priority) compiles the full learning session into a report for
   the user.
   - Output: user-facing report (what the page is, what the system
     can do on it, what it couldn't figure out).
   - **Not a prerequisite** for the learning loop to function. The
     loop is complete once steps 1–6 + 8 run; this is UX polish on top
     of that data. Prioritize accuracy in Page Understanding Agent,
     Attempt Evaluation Agent, and steps 4–5 before investing in
     Learning Report Agent.
8. **Persist** as a learned page record:
   - page signature
   - page purpose (from Page Understanding Agent)
   - operable elements (from step 4)
   - successful paths (from step 5, verdict=success)
   - failed paths (from step 5, verdict≠success) — kept as negative
     knowledge to avoid repeating mistakes.

### 4.2 What L1 deliberately is not

- Not a skill registry. The learned record is a data blob keyed by
  page signature, not a named skill.
- Not a single god Agent. Page Understanding Agent, Attempt Evaluation
  Agent, and Learning Report Agent (legacy: Agents A-C) are separate prompts with
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

L2 has two sub-modes.

### 5.1 User Demonstration

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

### 5.2 Guided Teaching

Guided Teaching is still L2: the user performs the real browser action,
and the system records what the user actually did.

1. The system opens the page in a visible Playwright browser.
2. Teaching Guide Agent (legacy: Agent H) communicates the next suggested step.
3. The UI may highlight target elements, add shadows, indicators,
   tooltips, or next-step prompts.
4. The user clicks, types, selects, or otherwise operates the page.
5. The system records the real event target, value, and observed state
   change.
6. Only the recorded user action can be appended to the learned record
   with `provenance = user`.

Teaching Guide Agent's suggestion is guidance, not evidence. It must not be written
as a LearnedPath action unless the user actually performs the action.

### 5.3 Invariant

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
plan (Task Path Planner) → execute → observe → ok?  ─── yes ──→ report (Task Result Reporter)
                                                 │
                                                 └── no ──→ recovery dialogue (Failure Recovery Agent)
                                                              ├── re-plan   ──→ back to execute
                                                              ├── re-run    ──→ back to plan
                                                              └── hand off  ──→ L2 mode
```

Triggers that flip a run off the happy path:

- action hits an error (timeout, not-found, server 5xx)
- observable state doesn't change when the learned path said it should
- page has drifted (element moved, selector stale, layout changed)
- user aborts (§6.9)

The sections below describe each arm. "Happy path" is just the
sunny-day subset; the error / drift / handoff arms are first-class,
not exception cases.

### 6.2 Happy-path pipeline

1. **Task Path Planner (legacy: Agent D)** reads:
   - the user's task description
   - the learned record(s) for the target page(s)

   and picks a route. A route is a sequence of concrete actions
   (selector + action_type + value) drawn from the learned paths.

   Task Path Planner **never reads raw HTML**. It only reads learned
   data. Its job is "pick the right pre-verified path", not "figure out
   what to click from scratch".

2. **Code** executes the chosen route via Playwright.
   - Selectors, values, action types are fully deterministic — they
     came from learned data, not from an LLM decision in the loop.
   - Each action's observation (URL before/after, DOM signals, etc.)
     is recorded for the reporting Agent.

3. **Task Result Reporter (legacy: Agent E)** summarizes the outcome for
   the user. Output: natural-language result + structured fields the
   UI can render.

### 6.3 Task Result Verification

L3 does not stop at "the path executed". It must also decide whether
the task's postconditions were satisfied.

Task Result Reporter must not infer success from a clean execution log alone. It
reports from execution results, postcondition checks, artifact status,
visible errors, and any rule / spec signals available. If WebAgentFlow
cannot verify the outcome, it must tell the user `uncertain` /
`needs review` instead of claiming completion.

Postconditions can come from the selected LearnedPath, Task Path Planner's task
plan, explicit user confirmation, or rule / spec signals. Examples:

- final URL or route
- DOM text or visible state
- row count or filtered-result count
- downloaded artifact exists
- final page state
- visible error or warning

### 6.4 The core invariant

During L3 execution, **LLMs are only invoked at boundaries** —
planning at the start, reporting at the end, recovery / abort
dialogue, or a user-teaching / handoff boundary. They are **never**
invoked to decide the next click, the next keystroke, or which field
to fill, because those decisions are already encoded in the learned
record.

This is non-negotiable. It is the thing that makes WebAgentFlow
different from "LLM watches the browser and clicks around". Break
this and you've built a different product.

### 6.5 Action Risk & Consent Gate

Ambiguous plans require confirmation before execution. Some operations
also require confirmation even when the planner is confident: dangerous
or irreversible actions, external sending, deletion, payment-like flows,
permission changes, bulk modification, or any user-defined sensitive
operation.

The first version should be a deterministic policy gate with
user-configurable rules. The Conversation Orchestrator inserts this
consent gate before execution. A future Risk / Consent Advisor may
exist, but this document does not add a new Agent for it.

### 6.6 Artifact Lifecycle

Real tasks often create or consume artifacts: downloaded files,
screenshots, generated evidence, exported CSV / PDF / Excel files,
uploaded files, or final task-output attachments.

WebAgentFlow eventually needs an artifact lifecycle:

- capture
- storage
- display / return to the user
- retention
- cleanup

This is future roadmap work, not a requirement for M10.2 replay /
drift.

### 6.7 Multi-Page / Multi-Path Workflow

End-state tasks may require multiple LearnedPaths across one or more
pages. Task Path Planner may eventually compose several learned paths into a
workflow, but it must not invent a path from raw HTML at runtime.

Multi-page workflow composition is a later capability. The M11 MVP does
not need to cover the full workflow space.

### 6.8 Error handling

When an action fails (page error, element not found, observable state
didn't change, server returned 5xx, etc.):

1. Execution **pauses**. It does NOT silently retry.
2. **Failure Recovery Agent (legacy: Agent F)** opens a dialogue with the
   user:
   - what happened
   - which step failed
   - what the system thinks the options are
3. Based on the user's reply, the system does one of:
   - **Re-plan and continue**: Task Path Planner re-picks a route, taking the
     new context into account. Execution resumes.
   - **Re-execute from start**: used when partial state is unsafe.
   - **Hand off to the user**: enters L2 mode. The user finishes
     the task manually; their actions are recorded and fed back into
     the learned record.

### 6.9 User-initiated abort

The user can stop the run at any time. When they do:

1. Execution pauses immediately.
2. **User Abort Handler (legacy: Agent G)** opens a dialogue:
   - what was done so far
   - what state the page is in
   - what the user wants next (resume / restart / hand over / drop)
3. The system acts on the user's reply.

Abort is different from error: abort is the user intervening on a
run that was otherwise going fine. Different role, different prompt,
different tone.

---

## 7. The Agents (single reference table)

These are separate Agents. Don't merge them. Different prompts,
different inputs, different outputs, different models over time.

| Primary role name | Legacy alias | Lifecycle stage | Reads | Produces |
|---|---|---|---|---|
| Page Understanding Agent | Agent A | L1 | Simplified AST + screenshot | Page purpose description |
| Attempt Evaluation Agent | Agent B | L1 | Attempt log + before/after state | Per-attempt verdict + anomalies |
| Learning Report Agent *(low priority, presentation)* | Agent C | L1 | Full learning session | User-facing learning report |
| Conversation Intake Agent | no legacy alias | Runtime conversation intake | User message + session summary + pending intake + session learned actions | Structured intent / target / action / slots / missing fields |
| Customer-Facing Agent Router | no legacy alias | Runtime conversation routing | Intake result + conversation context + optional page understanding + learned-action summary + Application Skill Registry | Route decision / next Agent / recommended skill |
| Learning Agent | no legacy alias | Runtime learning workflow | Target + user goal + slots + page understanding + session context | Learning request / learning result summary |
| Web Operation Agent | no legacy alias | Runtime web operation | User goal + target + learned-action summary + session context | Replay request / learn-then-execute request / operation result summary |
| Task Path Planner | Agent D | L3 | User task + learned record | Chosen concrete route |
| Task Result Reporter | Agent E | L3 | Execution outcome | User-facing result |
| Failure Recovery Agent | Agent F | L3 (error) | Error context + recent steps | Dialogue transcript + next action |
| User Abort Handler | Agent G | L3 (user abort) | Current state + abort signal | Dialogue transcript + next action |
| Teaching Guide Agent | Agent H | L2 | Teaching goal + current page analysis + known LearnedPaths + recent user action log + optional failure / recovery context | Natural-language instruction + highlight targets + expected user action + clarification questions |

Teaching Guide Agent boundaries:

- It does not click, fill, or operate the browser.
- It does not fabricate user actions.
- Its guidance is separate from recorded `provenance = user` actions.

When adding a new Agent-facing skill or capability, first ask: **which role
does this belong to?** If the answer is "a new one", that's a product-level
decision — update this document before adding it.

### 7.1 Application Skills (single reference table)

Application skills are bounded product abilities exposed to internal Agents
through the Orchestrator / Skill Runtime. They are not Agents. The
Customer-Facing Agent Router may recommend a skill, but code owns validation,
preconditions, invocation, trace, and final user-facing wording.

Implementation status belongs to the milestone documents. This table is the
product-level reference for the runtime skill vocabulary.

| Skill | Purpose | Who may request | Executor | Browser | Writes LearnedPath | Boundary |
|---|---|---|---|---|---|---|
| `collect_conversation_context` | Build recent-message, pending-state, learned-action, last-target, and no-path context. | Orchestrator | Code | No | No | Produces a redacted context bundle before LLM use. |
| `inspect_target_page` | Inspect a target URL and collect URL, title, visible text, controls, AST, and page-analysis context. | Router recommendation / worker Agent request | Runtime + code | May open browser | No | Inspection does not mutate the target page. |
| `understand_page` | Convert page context into page summary, visible controls, supported goals, required slots, confidence, and reason summary. | Router recommendation / Learning Agent request | Page Understanding Agent | No | No | Does not output selectors, DOM paths, browser steps, or page-type contracts. |
| `lookup_learned_actions` | Find learned actions in the current session and target URL / site-origin scope. | Router / Web Operation Agent | Code / repository | No | No | Must not cross target scope. |
| `ask_user_for_missing_info` | Ask for missing target, goal, input, or confirmation. | Router recommendation | Orchestrator / Result Reporter | No | No | Final wording stays in the unified WAgent voice. |
| `start_learning` | Start product-level learning through LearningRunService / autonomous exploration. | Learning Agent | Learning Service | Yes | Yes | LearnedPath evidence must come from real browser execution. |
| `start_replay` | Execute an existing LearnedPath through replay. | Web Operation Agent | Replay Service | Yes | No | Uses replay observation / wait signals as result evidence. |
| `learn_then_execute` | For in-scope complete tasks, learn first and then replay. | Web Operation Agent / Learning Agent | Skill Runtime | Yes | Yes | Disabled for unsupported or high-impact MVP-boundary cases. |
| `record_progress_event` | Emit user-visible progress for understanding, inspecting, learning, and executing. | Orchestrator / Skill Runtime | Code | No | No | Powers CLI / Console loading and status. |
| `record_agent_trace` | Persist redacted Intake / Router / Page Understanding / worker-Agent trace. | Agent Runtime | Code | No | No | Conversation evidence only; must not pollute LearnedPath proof. |

When adding or renaming an application skill, update this table and the current
milestone contract together.

---

## 8. Cross-Cutting Invariants

Invariants that apply across all lifecycle stages. Violations are product bugs,
not implementation details.

1. **LLMs never drive per-step execution in L3.** Only planning
   / reporting / dialogue.
2. **Failure is data.** This means more than `exploration_runs`
   existing. Failed attempts, replay drift, `target_missing`,
   `unsupported_action`, and user corrections should become failure
   evidence / negative knowledge over time. Planner, learning-quality,
   evaluation, and optimization work can consume that negative
   knowledge. M10.2 does not need to implement all of this.
3. **Provenance is preserved.** Every learned action knows whether
   it came from L1 (system) or L2 (user).
4. **Re-learning is allowed.** A page can be re-learned when it
   drifts; the system must not assume learned data is permanent.
5. **No silent retries.** Errors produce dialogue, not hidden
   back-off loops.
6. **Learning and execution are different code paths.** Reusing
   L1 orchestration to run L3 tasks is a smell; L3
   should be boring and deterministic.
7. **Conversation orchestration is code-owned.** Session state,
   consent gates, recovery routing, abort handling, and teaching-mode
   switches are controlled by the Conversation Orchestrator, not by an
   unconstrained LLM loop.
8. **Engine hygiene matters.** Conversations, logs, screenshots,
   artifacts, and LLM prompt payloads need future retention, deletion,
   redaction, and audit design inside the running instance. This is
   engine hygiene for WebAgentFlow runtime evidence.

---

## 9. Where the current codebase sits

Honest mapping, so the gap between the vision and the code is
visible. Keep this section updated as lifecycle stages and milestones ship.

- **L1 steps 1–2 (HTML → AST → Simplified AST)**: shipped as
  server-side parsing (`html_ast_parser.py` + `ast_simplifier.py`).
  Autonomous exploration currently uses a live-page analyzer
  (`page_analyzer.py`) rather than the offline AST pipeline;
  reconciling the two views is open work.
- **L1 step 3 (Page Understanding Agent, legacy: Agent A)**: not yet built as a
  separate Agent. Today's Supervisor mixes intent-understanding and
  evaluation concerns.
- **L1 steps 4–5 (element extraction + trial)**: shipped in the
  autonomous exploration subsystem.
- **L1 steps 6–8 (evaluation + report + persist)**: partial.
  Verdict + 5-score verification scorecard + Supervisor summary
  exist as exploration-stage artifacts. A **product-form,
  user-facing learning report is still exploratory** — current
  output is a developer-oriented debug surface, not the final shape
  Learning Report Agent should produce. **Persist-as-learned-record shipped in
  delivery milestone M10.1** — `pass_gate = pass` runs
  auto-ingest as `learned_paths` rows keyed by
  (page_template, query_signature, dom_fingerprint, scenario), with
  a trust lifecycle (`provisional` / `confirmed` / `flaky` /
  `deprecated`) the operator drives via the run-detail page.
  Replay / drift detection against stored paths shipped in M10.2.
- **L2 (User-Guided Learning)**: not started. The 2026-04-20
  cleanup removed the old Chrome extension; L2 will be built
  from scratch on top of a **visible** Playwright browser (per §5.1),
  not on the extension. User Demonstration, Guided Teaching, and
  Teaching Guide Agent is not implemented today.
- **M11.0 runtime conversation foundation**: shipped. `wagent conversation`,
  Conversation API, Conversation Orchestrator / Dispatcher service skeleton,
  public dispatch endpoint, explicit replay hook, and CLI dispatch integration
  are implemented.
- **M11.3.4 conversation intake**: implementation complete, scoped tests passed,
  real LLM-backed smoke pending. `wagent chat` now has schema-constrained intake,
  deterministic fallback, pending-intake guardrails, response provenance, and
  redacted LLM trace history. Bare URL -> "learn" recovery and broader
  customer-facing routing are deferred to M11.3.5.
- **L3 task execution**: not started. No Task Path Planner implementation,
  no Task Result Reporter implementation, no task-to-path execution loop, no
  result verification loop, no recovery dialogue, and no teaching mode.
  Replay / drift is the M10 foundation; M11.0 is the runtime-conversation
  foundation, and M11.1 is the first planned L3 happy-path MVP.

When a lifecycle stage fully lands, update this section to reflect it.

### 9.1 Delivery milestone alignment

The current delivery plan intentionally separates path assets from real
task execution:

| Milestone | Product role | Internal Agents |
|---|---|---|
| M10 · Path Asset Foundation | LearnedPath persistence, catalog, replay execution, and drift detection. | No new Agent; provides execution substrate. |
| M11.0 · Runtime Conversation Shell & Agent Orchestration | CLI MVP, session state, Conversation Orchestrator, user message routing, and confirmation / pause / abort / takeover basics. | No new Agent by default; routes to Task Path Planner, Task Result Reporter, Failure Recovery Agent, User Abort Handler, and Teaching Guide Agent as those capabilities land. |
| M11.1 · Task-to-Path Planning & Execution MVP | Task Path Planner / Task Result Reporter, LearnedPath retrieval / ranking, slot binding, task result verification MVP, basic artifact capture, and risk / consent gate MVP. | Task Path Planner (legacy: Agent D); Task Result Reporter (legacy: Agent E). |
| M11.3.4 · Conversation Intake Agent | Schema-constrained intake for `wagent chat`: understand user language, target, action, slots, and missing information before Orchestrator validation. | Conversation Intake Agent (no legacy alias). |
| M11.3.5 · Customer-Facing Agent Router & Skill Runtime | Product-facing routing layer for `wagent chat`: context collection, Agent Router recommendation, Orchestrator adjudication, Application Skill Registry, Page Understanding / Learning / Web Operation worker boundaries, MVP high-impact boundary, and progress / trace UX. | Customer-Facing Agent Router; Page Understanding Agent used as semantic page interpreter; Learning Agent and Web Operation Agent as worker roles under Orchestrator control. |
| M12 · Recovery & Abort Dialogue | Failure recovery, user interrupt handling, and continue / replan / rerun / takeover / abandon choices. | Failure Recovery Agent (legacy: Agent F); User Abort Handler (legacy: Agent G). |
| M13 · User-Guided Learning, Teaching & Correction | Visible browser, user demonstration recording, Teaching Guide Agent guidance, highlight / shadow / indicator / tooltip, provenance=user write-back, and correction UI. | Teaching Guide Agent (legacy: Agent H); preserve user provenance. |
| M14 · Learning Quality, Coverage & Negative Knowledge | Page Understanding Agent / Attempt Evaluation Agent / Learning Report Agent, popup controls, custom click-toggle, label extractor expansion, cross-page pattern mining, and failure evidence / negative knowledge store. | Page Understanding Agent (legacy: Agent A); Attempt Evaluation Agent (legacy: Agent B); Learning Report Agent (legacy: Agent C). |
| M15 · Automated Evaluation, Audit & Hygiene | Replay regression, drift alerts, trust trend, result verification trend, artifact / log / screenshot retention cleanup, and conversation / recovery / teaching audit. | Reuses Attempt Evaluation Agent / Supervisor-style evaluation; no new Agent by default. |
| M16 · External Interfaces | Stable API, external CLI, Skill / Tool, third-party scheduler interface, and integration hooks for user-built systems. | No new product Agent; exposes existing capabilities. |
| M17 · Multi-Page Workflow Composition | Compose multiple LearnedPaths into larger workflows without inventing paths from raw HTML. | Extends Task Path Planner inputs; no new Agent by default. |
| M18 · CLI Distribution & Integration Readiness | Stable CLI distribution, local packaging, API / CLI examples, scripting / batch usage, integration cookbook, and versioned CLI / API contracts. | No new product Agent by default. |

M10.2 replay is still valuable after this reshuffle: it is the first
deterministic consumer of LearnedPath data. It does **not** implement
Task Path Planner or L3 task planning; it gives M11.1 something safe to call.

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
   - For the runtime conversation surface and for developers to invoke
     a capability directly from the terminal.
   - Fits the initial CLI-first product loop, debugging, batch jobs,
     scripts, or integration into a custom operator console.
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
> 1. **Product-internal role Agents** (§7) — roles that run *inside*
>    WebAgentFlow at runtime (Page Understanding Agent, Task Path Planner,
>    Failure Recovery Agent, …). A-H labels are legacy aliases. Defined by
>    this document.
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

This section describes a **long-term delivery direction**. The
CLI-first runtime conversation surface in §2.1 can arrive earlier
because it is part of getting the core product loop working. M16 is the
later stabilization of external scheduler interfaces and broader
tooling contracts.

Current codebase has part of the foundation:

- Browser execution and exploration capabilities.
- Page analysis / action planning / verification.
- Autonomous workbench as the operator's trigger + observation surface.
- Runtime CLI conversation foundation (`wagent conversation`), Conversation
  API, Conversation Orchestrator / Dispatcher service skeleton, public dispatch
  endpoint, explicit replay hook, and CLI dispatch integration.

Pending:

- A more stable external CLI entry.
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

The engine also needs basic hygiene for conversations, logs,
screenshots, artifacts, and LLM prompt payloads: what is recorded, how
long it is retained, how it is deleted, what can be redacted, and what
is auditable. This is engine hygiene inside the running instance for
WebAgentFlow runtime evidence.

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
