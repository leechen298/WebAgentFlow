# Intent

状态：proposed

## Goal

Implement the scoped design for code-owned capability composition runtime: when a complete LearnedPath is missing,
WebAgentFlow can retrieve compatible LearnedCapabilities, build a deterministic ordered plan, reject unsafe or
ambiguous compositions, and prepare an execution handoff that may be promoted to LearnedPath only after evidence gate
success.

## Why Now

11.3.12.1 created `LearnedCapability` persistence. 11.3.12.2 created bounded learning batches that can ingest
successful atomic capability evidence. 11.3.12.3 added target-agnostic Page Understanding hints. The remaining parent
package promise is runtime composition: using verified atomic capabilities without returning to exhaustive
learn-every-combination behavior.

## In Scope

- Deterministic `CapabilityCompositionPlan` schema and result taxonomy.
- Code-owned retrieval / compatibility / ordering rules for LearnedCapabilities.
- Missing / ambiguous / unsafe composition rejection with explicit reasons.
- Preference for existing high-confidence LearnedPath over composition when available.
- Execution handoff payload that uses existing replay / execution services and never emits LLM browser steps.
- Promotion guard: no LearnedPath write unless execution evidence passes the existing gate.
- Focused repo-local tests and evidence.

## Out of Scope

- Console UI.
- New public LearnedCapability or composition HTTP API.
- LLM-driven step-by-step browser execution.
- New internal Agent roles or lifecycle stages.
- Live autonomous validation, `verify-scenario`, product UI smoke, or `wagent chat` live target runs.
- Async learning jobs beyond existing LearningBatch semantics.
- Backfilling old LearnedPaths into LearnedCapabilities.

## Success Criteria

- Composition plan schemas and service produce deterministic, auditable plans from compatible capabilities.
- Unsafe, missing, cross-page, low-trust, or ambiguous candidates fail closed with reviewable reasons.
- Existing LearnedPath preference remains explicit and test-covered.
- Promotion into LearnedPath is guarded by execution/pass-gate evidence, not by plan construction.
- Scoped tests, ruff, and hardcoding scan pass or failures are recorded truthfully.
