# Scope Boundaries — What's Explicitly Out of Scope

This document lists capabilities that are **deliberately not** part of the
current phase. When in doubt, check here before proposing or implementing
them. Items on this list are deferred until a prerequisite phase validates.

## Current Phase

Phase 9 — exploration loop, success evaluation, autonomous workbench.
Phases 1–7 are complete (see [`architecture.md`](./architecture.md)).

## Not in Scope

### Execution & Orchestration

- **CLI tool** (`apps/cli`) — wait until exploration loop validates real
  usage patterns.
- **Skill registry / skill runtime** — current services ARE the callable
  interface; no separate registry yet.
- **Replay execution strategies** — replaying recorded steps deterministically
  across environments is a later concern.

### Supervision

- **Real-time per-step LLM supervision (Layer 1)** — post-run assessment
  (Layer 2) first, since it's cheaper to reason about.
- **External AI-coding-agent supervision** — the AI coding tool (Claude Code,
  Codex, …) must not act as supervisor. See `CLAUDE.md` §
  "AI Coding Agent — Execution Boundary".

### Learning & Abstraction

- **User behavior ↔ page change causal modeling** — future work under
  Phase 10.
- **Historical path template caching** — Phase 10 / 11.
- **User correction & behavior teaching** — Phase 11.

### Parser / AST

- **"Page summarizer" approaches that restructure DOM for readability** — the
  AST layer must preserve structural fidelity. Summarization, if needed, is a
  separate downstream view.
- **Simplified AST with semantic restructuring** — the Simplified AST is a
  structure-preserving projection, not a rewrite.

### Data / Persistence

- **Approve / reject full persistence** (autonomous and task-driven
  exploration) — currently MVP placeholders; the authoritative LearnedPath
  write-back is deferred.
- **Cross-device / cloud sync of task definitions** — data belongs to the
  user; local-first is the current stance.

## Re-evaluation Triggers

Open this list whenever:

- A phase completes and you're asking "what's next?" — check prerequisites
  and entry criteria for deferred items.
- A user asks for a feature that "feels obvious" but isn't in the codebase —
  it's probably deliberately deferred.
- Working on a feature that seems to require one of these — consider whether
  a smaller alternative would unblock the current phase without pulling in
  the deferred work.

## Related

- [`architecture.md`](./architecture.md) §E — development timeline.
- [`roadmap.md`](./roadmap.md) — operational milestones.
- [`../CLAUDE.md`](../CLAUDE.md) — session-level guidance.
