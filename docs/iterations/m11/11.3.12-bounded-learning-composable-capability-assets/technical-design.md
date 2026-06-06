# Technical Design

状态：proposed

## Design Summary

11.3.12 adds a persistent atomic learning asset between ExplorationRun and LearnedPath:
`LearnedCapability`. It also changes URL-only learning from exhaustive scenario generation to
bounded capability discovery, then enables runtime composition when a complete LearnedPath is missing.

This design is target-agnostic. `/users` is only the motivating validation case.

## Contract Alignment

- `LearnedCapability` stores reusable page operation evidence.
- LearnedPath remains the complete replay path asset.
- Page Understanding Agent provides hints, not executable steps.
- Code owns capability composition and browser execution.
- Learning batches must close, cancel, or detach; they cannot silently outlive chat.

## Data Model

### New table: `learned_capabilities`

Proposed fields:

- `id`
- `page_template`
- `query_signature`
- `dom_fingerprint`
- `capability_key`
- `capability_kind`
- `human_label`
- `region_ref`
- `control_ref`
- `adapter_type`
- `action_schema_json`
- `sample_value_policy_json`
- `terminal_target_json`
- `evidence_json`
- `provenance`
- `trust`
- `trust_reason`
- `source_run_id`
- `source_learned_path_id`
- `dedup_key`
- timestamps

`dedup_key` should be based on page signature + capability kind + stable control/region reference + terminal target.

### Optional new table: `learning_batches`

If implementation cannot safely express batch lifecycle through existing conversation metadata and
exploration run strategy metadata, add `learning_batches`:

- `id`
- `session_id`
- `target_url`
- `status`
- `policy_json`
- `started_at`
- `ended_at`
- `cancel_requested_at`
- `summary_json`
- `created_run_ids`
- `created_capability_ids`
- `created_learned_path_ids`

If this table is deferred, `technical-design.md` must be revised before implementation to explain the
alternative durable batch handle.

### LearnedPath compatibility extension

Add metadata, preferably under existing JSON fields where possible:

- `source_capability_ids`
- `composition_id`
- `composition_policy_version`

Do not make old LearnedPath rows invalid.

## Schemas

Add or extend Pydantic schemas:

- `LearnedCapabilitySummary`
- `LearnedCapabilityDetail`
- `CapabilityEvidenceSummary`
- `CapabilityCompositionRequest`
- `CapabilityCompositionPlan`
- `CapabilityCompositionResult`
- `LearningBatchSummary`
- `BoundedLearningPolicy`

API responses must hide selector-level sensitive detail from public user-facing surfaces while preserving it in operator/debug detail views.

## Services

### Capability Inventory Builder

Refactor current `capability_discovery.py` so temporary `FilterCapability` data can be converted into
persistable capability candidates.

Responsibilities:

- consume PageAnalysis and Page Understanding hints;
- classify page regions and controls;
- produce capability candidates with adapter support status;
- attach sample value candidates and terminal targets.

### LearnedCapabilityRepository

Responsibilities:

- idempotent ingest by `dedup_key`;
- trust updates;
- lookup by page signature, origin, capability kind, label, and region;
- join to source ExplorationRun / LearnedPath evidence.

### BoundedLearningPlanner

Responsibilities:

- choose scenario set under budget;
- prefer single-capability probes;
- add dependency combinations only when evidence suggests dependency;
- suppress repeated failing selector / adapter attempts;
- stop on budget or no-new-capability thresholds.

### LearningBatchController

Responsibilities:

- own batch lifecycle status;
- receive cancellation signals from chat timeout, user cancel, Ctrl+C, or API disconnect if supported;
- close Playwright resources on cancellation;
- mark incomplete batches as `timed_out`, `cancelled`, `partial_success`, or `unverified`;
- write conversation events and history detail summaries.

### CapabilityComposer

Responsibilities:

- translate user intent and slot bindings into source capability candidates;
- build deterministic ordered action plans;
- reject unsafe, ambiguous, missing, or incompatible compositions;
- hand execution to replay / execution runtime;
- promote successful composition into LearnedPath after gate.

Agent involvement stays limited to intent and semantic recommendation. Code owns final composition and execution.

## Page Understanding Integration

Extend Page Understanding output or deterministic terminal hints with:

- `page_purpose`
- `regions`
- `function_candidates`
- `terminal_candidates`
- `sample_value_candidates`
- `dependency_hints`
- `coverage_recommendations`

If LLM-backed Page Understanding is not ready, deterministic PageAnalysis-derived hints may fill these fields initially.

## Conversation Integration

`wagent chat` learning flow should change from a blocking single HTTP request to one of two allowed designs:

1. Synchronous with larger/no read timeout but hard backend batch timeout and guaranteed closed result.
2. Async learning job with progress events, batch id, cancellation, and history page.

The second design is recommended. It avoids making CLI transport timeout the learning lifecycle boundary.

On timeout / cancellation:

- user-facing reply should say learning did not finish;
- session active task must close or point to a resumable batch;
- browser resources must close unless batch explicitly detached;
- no new LearnedPath may be presented as ready without closed evidence.

## API / Console Surface

Potential API additions:

- `GET /learning/batches/{id}`
- `POST /learning/batches/{id}/cancel`
- `GET /learned-capabilities`
- `GET /learned-capabilities/{id}`

Console follow-up:

- Learning batch detail shows capability coverage, failed capabilities, pending / cancelled state.
- LearnedPath detail should show source capability ids when present.
- A future LearnedCapability detail page can show evidence without exposing unsafe raw selectors in non-debug views.

## Migration / Backfill

Initial migration should not backfill all old LearnedPaths into LearnedCapabilities automatically.

Allowed initial behavior:

- new learning batches create LearnedCapabilities;
- old LearnedPaths continue to work;
- optional lazy derivation may show "derived from old path" in debug UI but must not claim verified atomic capability without source evidence.

## Risk Areas

- Over-trusting synthetic sample values that only produce empty results.
- Misbinding component-library controls, such as date/month labels binding to a region selector.
- Letting capability composition become LLM-driven browser execution.
- Adding batch cancellation that closes a browser used by another active batch.
- Creating a schema that makes old LearnedPaths unreadable.

## Test Matrix Summary

Detailed test cases are in `test-plan.md`. Required implementation tests cover:

- model/repo migration and idempotent ingest;
- PageAnalysis -> capability candidates;
- bounded planner scenario suppression;
- batch cancellation and timeout;
- composition from capabilities;
- no target hardcoding;
- conversation history and user-facing learning outcome.
