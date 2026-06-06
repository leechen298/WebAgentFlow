# Intent

状态：implemented

## Goal

Implement the design basis for a bounded learning batch lifecycle so product-level URL-only learning has
a durable batch handle, explicit budget policy, terminal status, and cancel / timeout behavior that closes
or safely detaches browser-driving work.

## Motivation

11.3.10 introduced URL-only capability discovery by generating multiple filter scenarios. 11.3.11 made
terminal / ingest evidence stricter. 11.3.12.1 added `LearnedCapability` persistence. The remaining
runtime problem is lifecycle ownership: `wagent chat` can timeout or be interrupted while backend learning
continues synchronously through scenario runs, with no durable batch status that tells the user whether
learning completed, partially completed, timed out, or was cancelled.

This package creates the bounded batch layer before Page Understanding hints or runtime composition so later
packages can add richer scenario selection without reintroducing unbounded work.

## Scope / Non-goals

- Do not implement Page Understanding capability hints; 11.3.12.3 owns ranking and richer hints.
- Do not implement L3 capability composition or promotion into LearnedPath; 11.3.12.4 owns composition.
- Do not run live autonomous validation, `verify-scenario`, product UI autonomous runs, or direct
  autonomous-run endpoints.
- Do not make CLI transport timeout the source of truth for backend lifecycle.

## Success Criteria

- A reviewed design defines `BoundedLearningPolicy`, `LearningBatch`, statuses, budget handling, cancel,
  timeout, detach, and closeout semantics.
- The implementation plan is scoped to durable batch status plus LearningRunService / chat integration, not
  Page Understanding or composition.
- The test plan proves bounded scenario generation, status derivation, cancel / timeout cleanup, compatibility
  with existing LearnedPath and LearnedCapability behavior, and no target hardcoding.
- `review.md` records design review and implementation authorization before code work starts.
