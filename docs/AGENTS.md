# AGENTS.md — docs-local guidance

Guidance for Codex and other AI coding agents when working under
`docs/`.

> Keep this file in sync with `docs/CLAUDE.md`.

## Scope

This file applies to documentation work under `docs/`, especially deep
iteration folders such as `docs/iterations/phase-10/10.1.5-*/`.

The repository-level execution rules in `../AGENTS.md` still apply. In
particular, do not trigger autonomous runs except through the permitted
project skill and reporting contract.

## Required Reading

Before changing iteration documents, read:

1. `../AGENTS.md`
2. `product-model.md`
3. `iterations/README.md`
4. The relevant Phase index, for example `iterations/phase-10/README.md`
5. The relevant Phase plan, for example `iterations/phase-10/phase-plan.md`
6. The specific iteration `intent.md`, `plan.md`, and `review.md`

Do not rely on an older chat summary when these files are cheap to read.

## Iteration Docs Are A Set

For a real iteration, `intent.md`, `plan.md`, and `review.md` are a unit:

- `intent.md` says why the work exists and what is out of scope.
- `plan.md` says how the work should be implemented and verified.
- `review.md` records what actually happened, what changed from the plan,
  what was verified, and any remaining risk.

Do not treat `review.md` as optional. If implementation work happened, the
iteration is not closed until `review.md` reflects the actual outcome.

## Current Implementation Beats Old Planning

When code evolves away from the original plan, update the docs to explain
the current valid model instead of preserving stale wording.

Examples:

- If a later sub-iteration moves an operation from one page to another,
  update the earlier summary or review with a "current valid behavior" note.
- If a plan said "no backend changes" but implementation added a projection
  field, record that as a deliberate deviation in `review.md`.
- If a Phase index says an item is "executable" but its review is complete,
  update the Phase index and plan to "completed".

The goal is not to rewrite history. Keep historical notes, but mark which
behavior is current so future agents do not implement against an obsolete
plan.

## Phase Index Sync

When adding, completing, renaming, or superseding an iteration under
`docs/iterations/phase-N/`, check and update:

- `docs/iterations/phase-N/README.md`
- `docs/iterations/phase-N/phase-plan.md` when it exists
- The iteration's own `intent.md`, `plan.md`, and `review.md`
- Any earlier summary or review that now contains misleading current-state
  wording

Directory names and task numbers must match. Avoid hidden mappings like
"directory 03 corresponds to task 10.2".

## Verification Notes

Only record commands that were actually run. If tests were not run because
the change is documentation-only, say that plainly. If a command fails due
to an unrelated existing issue, record the exact failure and why it does or
does not block the iteration.

For live autonomous runs, follow `../AGENTS.md`: report `pass_gate.status`,
Supervisor verdict, five scorecard scores, and `run_id`.
