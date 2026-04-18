# Product Model — WebAgentFlow

> **This document is authoritative for "what WebAgentFlow is".**
> AI coding agents (Claude Code, Codex, …) MUST treat this as the
> reference when planning features. If a proposal isn't covered here,
> pause and ask — don't invent a new role, phase, or loop and
> back-fit the code to it.
>
> If you change your understanding of the product, **update this
> file first**, then the code.

---

## 1. One Sentence

WebAgentFlow replaces the user at the keyboard on web pages: it learns
a page well enough to operate it autonomously, and when the user asks
for something, it executes the task by driving a real browser — not
by asking an LLM to click things step-by-step.

## 2. Three Phases of a Page

Every page goes through three phases in WebAgentFlow's lifetime.
Features belong to exactly one phase. Don't blur them.

| # | Phase | Who drives | Does an LLM read raw HTML per step? |
|---|---|---|---|
| 1 | Autonomous Learning | System | Yes — bounded, during learning only |
| 2 | User-Guided Learning | User (in a visible browser) | No — system records the user |
| 3 | Actual Work | System, from learned data | **NO** — this is the core invariant |

The rest of this document fills in each phase, the Agents involved, and
the invariants that must not be violated.

---

## 3. Phase 1 · Autonomous Learning

**Trigger**: The system encounters a page it has not learned (or the
user forces re-learning).

### 3.1 Pipeline

Sequential steps. Every step has a clear input/output contract so
components can be replaced independently.

1. **Fetch HTML → Full AST** (server-side, `lxml`).
   DOM-faithful; no semantic rewriting.
2. **Full AST → Simplified AST** (structure-preserving projection).
   Simplified AST removes noise but preserves node boundaries and
   sibling order. It is NOT a "page summary".
3. **Agent A · Page-Intent Agent** reads the Simplified AST plus a
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
6. **Agent B · Attempt-Evaluation Agent** judges each attempt's
   outcome and flags anomalies.
   - Output: per-attempt verdict + summary. Independent of Agent A.
7. **Agent C · Learning-Report Agent** compiles the full learning
   session into a report for the user.
   - Output: user-facing report (what the page is, what the system
     can do on it, what it couldn't figure out).
8. **Persist** as a learned page record:
   - page signature
   - page purpose (from Agent A)
   - operable elements (from step 4)
   - successful paths (from step 5, verdict=success)
   - failed paths (from step 5, verdict≠success) — kept as negative
     knowledge to avoid repeating mistakes.

### 3.2 What Phase 1 deliberately is not

- Not a skill registry. The learned record is a data blob keyed by
  page signature, not a named skill.
- Not a single god Agent. Agents A / B / C are separate prompts with
  separate outputs and separate failure modes. Don't fuse them.
- Not permanent. Re-learning is supported. A page can be re-learned
  when it changes, or when the user corrects something.

---

## 4. Phase 2 · User-Guided Learning

**Trigger** (either):

- The user explicitly enters guided-learning mode for a page the
  system already knows partially (to fill a gap).
- The user **takes over** during Phase 3 execution (error recovery or
  explicit hand-off). Take-over automatically becomes guided learning
  — the system records everything the user does from that point.

### 4.1 Pipeline

1. System opens the page in a **visible** Playwright browser (not
   headless — the user is driving).
2. User operates the page normally.
3. System records each interaction:
   - which selector was used (resolved from the real event target)
   - what value was typed / what was clicked
   - what observable state changed after the interaction
4. Captured operations are appended to the page's learned record,
   marked with `provenance = user`, and participate in Phase 3 route
   planning the same way Phase-1 paths do.

### 4.2 Invariant

Phase 2 records the user's real actions. It does **not** infer intent
via LLM, and it does **not** retroactively rewrite what the user did.
Provenance is preserved so later reviews can trust it.

---

## 5. Phase 3 · Actual Work

This is the phase that matters to the end user. Everything in Phases
1 and 2 exists to make Phase 3 cheap, fast, and reliable.

**Trigger**: The user submits a task ("log into X and download the
weekly report as CSV", etc.).

### 5.1 Happy-path pipeline

1. **Agent D · Planner Agent** reads:
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

3. **Agent E · Result-Reporting Agent** summarizes the outcome for
   the user. Output: natural-language result + structured fields the
   UI can render.

### 5.2 The core invariant

During Phase 3 execution, **LLMs are only invoked at boundaries** —
planning at the start, reporting at the end, and dialogue on error
or abort. They are **never** invoked to decide the next click, the
next keystroke, or which field to fill, because those decisions are
already encoded in the learned record.

This is non-negotiable. It is the thing that makes WebAgentFlow
different from "LLM watches the browser and clicks around". Break
this and you've built a different product.

### 5.3 Error handling

When an action fails (page error, element not found, observable state
didn't change, server returned 5xx, etc.):

1. Execution **pauses**. It does NOT silently retry.
2. **Agent F · Recovery-Dialogue Agent** opens a dialogue with the
   user:
   - what happened
   - which step failed
   - what the system thinks the options are
3. Based on the user's reply, the system does one of:
   - **Re-plan and continue**: Agent D re-picks a route, taking the
     new context into account. Execution resumes.
   - **Re-execute from start**: used when partial state is unsafe.
   - **Hand off to the user**: enters Phase 2 mode. The user finishes
     the task manually; their actions are recorded and fed back into
     the learned record.

### 5.4 User-initiated abort

The user can stop the run at any time. When they do:

1. Execution pauses immediately.
2. **Agent G · Abort-Dialogue Agent** opens a dialogue:
   - what was done so far
   - what state the page is in
   - what the user wants next (resume / restart / hand over / drop)
3. The system acts on the user's reply.

Abort is different from error: abort is the user intervening on a
run that was otherwise going fine. Different Agent, different prompt,
different tone.

---

## 6. The Agents (single reference table)

These are separate Agents. Don't merge them. Different prompts,
different inputs, different outputs, different models over time.

| ID | Name | Phase | Reads | Produces |
|---|---|---|---|---|
| A | Page-Intent | 1 | Simplified AST + screenshot | Page purpose description |
| B | Attempt-Evaluation | 1 | Attempt log + before/after state | Per-attempt verdict + anomalies |
| C | Learning-Report | 1 | Full learning session | User-facing learning report |
| D | Planner | 3 | User task + learned record | Chosen concrete route |
| E | Result-Reporting | 3 | Execution outcome | User-facing result |
| F | Recovery-Dialogue | 3 (error) | Error context + recent steps | Dialogue transcript + next action |
| G | Abort-Dialogue | 3 (user abort) | Current state + abort signal | Dialogue transcript + next action |

When adding a new capability, first ask: **which Agent does this
belong to?** If the answer is "a new one", that's a product-level
decision — update this document before adding it.

---

## 7. Cross-Cutting Invariants

Invariants that apply across all phases. Violations are product bugs,
not implementation details.

1. **LLMs never drive per-step execution in Phase 3.** Only planning
   / reporting / dialogue.
2. **Failure is data.** Failed attempts in Phase 1 are persisted, not
   discarded.
3. **Provenance is preserved.** Every learned action knows whether
   it came from Phase 1 (system) or Phase 2 (user).
4. **Re-learning is allowed.** A page can be re-learned when it
   drifts; the system must not assume learned data is permanent.
5. **No silent retries.** Errors produce dialogue, not hidden
   back-off loops.
6. **Learning and execution are different code paths.** Reusing
   Phase-1 orchestration to run Phase-3 tasks is a smell; Phase-3
   should be boring and deterministic.

---

## 8. Where the current codebase sits

Honest mapping, so the gap between the vision and the code is
visible. Keep this section updated as phases ship.

- **Phase 1 steps 1–2 (HTML → AST → Simplified AST)**: done for the
  recording/extension path; autonomous exploration currently uses a
  live-page analyzer (`page_analyzer.py`), not the offline AST
  pipeline. Reconciling these two views is open work.
- **Phase 1 steps 3 (Page-Intent Agent)**: not yet built as a
  separate Agent. Today's Supervisor mixes intent-understanding and
  evaluation concerns.
- **Phase 1 steps 4–5 (element extraction + trial)**: shipped in the
  autonomous exploration subsystem.
- **Phase 1 steps 6–8 (evaluation + report + persist)**: partial —
  verdict exists, report exists, **persist-as-learned-record does
  not**. Runs are persisted to `exploration_runs` for history, not
  as learned paths.
- **Phase 2 (User-Guided Learning)**: not started. The extension
  records events, but there is no guided-learning mode that appends
  to a learned page record.
- **Phase 3 (Actual Work)**: not started. No Planner Agent, no
  replay, no recovery dialogue. This is the next big bet.

When a phase fully lands, update this section to reflect it.

---

## 9. Related Docs

- [`architecture.md`](./architecture.md) — how the code is organized
  (layers, AST dual-track, services sub-packages). Complements this
  doc; doesn't replace it.
- [`roadmap.md`](./roadmap.md) — operational view: what's shipped
  vs. in progress vs. next.
- [`scope-boundaries.md`](./scope-boundaries.md) — what's deliberately
  NOT being built right now.
- [`parser-rules.md`](./parser-rules.md) — DOM → StateNode
  constraints that support Phase 1 steps 1–2.
- [`product-model.zh.md`](./product-model.zh.md) — Chinese mirror.
