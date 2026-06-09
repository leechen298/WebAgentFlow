# Technical Design

状态：reviewed_for_implementation

## Current State

Existing 11.3.12.4 implementation provides:

- `CapabilityCompositionRequest`
- `CapabilityCompositionPlan`
- `CapabilityComposer.compose()`
- private execution handoff
- `evaluate_composition_promotion()`

It does not provide:

- automatic candidate family derivation；
- page-scope capability graph construction；
- bounded combination generation；
- batch execution of composition candidates；
- promotion write into `LearnedPath`；
- redacted provider evidence bundle export。

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| `CompositionCandidate` is not a `LearnedPath` | Add candidate schema / table / repo with candidate status separate from `learned_paths` | candidate schema / repo tests | Generated candidates are not success evidence |
| Generation is bounded | `BoundedCompositionCandidateGenerator` emits only configured families and max counts | generation tests | No exponential permutations |
| Static rejection before execution | Candidate generation records rejection reasons for scope, trust, slot, terminal, conflict, and unsupported operation issues | generation / static rejection tests | Reuses `CapabilityComposer` fail-closed checks |
| Execution uses approved runtime | Executor consumes private `CapabilityExecutionHandoff`; tests use fake runtime, not autonomous-run HTTP endpoints | executor tests | No direct autonomous-run calls |
| Promotion requires execution evidence | `CompositionPromotionService` calls `evaluate_composition_promotion()` before any `LearnedPath` write | promotion tests | Failed / unverified candidates remain negative evidence |
| Provider bundle is redacted | `LearningEvidenceBundleBuilder` exports redacted projections only | bundle redaction tests | No DB dump, private handoff, selectors, DOM, oracle, seed copy, or raw IDs |
| Runtime stays target-agnostic | No Validation Site URL / route / labels / selectors / oracle ids in product runtime or prompts | hardcoding scan | Test fixtures may contain generic sample data only |

## Affected Surfaces

- API service layer: new learning services for candidate generation, execution,
  promotion, and bundle export.
- API schemas: additive `CompositionCandidate` and
  `waf.learning_evidence_bundle.v1` schemas.
- API models / migrations: new `composition_candidates` table.
- Repositories: new candidate repository plus focused page-scope capability lookup.
- Tests: new candidate, promotion, bundle, and regression tests.
- No Console UI change in this package.
- No public HTTP API is required in this package.
- No live validation is authorized in this package.

## Proposed Services

### CapabilityGraphBuilder

Inputs:

- target URL / page signature；
- current PageAnalysis hints when available；
- persisted `LearnedCapability` rows；
- trust / evidence policy。

Output:

- page-scoped capability graph；
- capability groups by kind；
- dependency hints；
- terminal action candidates；
- rejected capability reasons。

### CompositionRequirementDeriver

Inputs:

- user goal / canonical goal；
- page purpose hints；
- available capability graph；
- optional provider evaluation request categories。

Output:

- required candidate families；
- required capability kinds per family；
- slot requirements；
- risk constraints。

This service may consume LLM-parsed intent categories, but code owns final requirement shape.

### BoundedCompositionCandidateGenerator

Inputs:

- capability graph；
- derived requirements；
- bounded policy。

Output:

- `CompositionCandidate` records；
- static rejection records；
- coverage summary。

Generation rules:

- single terminal chain；
- dependency pair chain；
- all-supported smoke chain only when bounded policy allows；
- no exponential full permutation；
- deterministic ordering；
- stable candidate ids。

### CompositionCandidateExecutor

Executes ready candidates through existing execution / replay runtime.

Responsibilities:

- convert candidate into private execution handoff；
- run ordered actions；
- collect terminal evidence；
- call ingest / promotion evaluation；
- record negative evidence for fail / unverified。

### CompositionPromotionService

Responsibilities:

- call existing `evaluate_composition_promotion()`；
- write `LearnedPath` only after successful execution evidence；
- attach source capability ids in metadata / actions evidence；
- dedupe candidates / paths；
- avoid writing provider-private details。

### LearningEvidenceBundleBuilder

Produces `waf.learning_evidence_bundle.v1` for external provider evaluation.

Fields:

- operator actions and approved surface summary；
- component detection summary；
- learning batch summary；
- learned capability summary；
- learned path summary；
- candidate generation summary；
- candidate execution summary；
- promotion summary；
- run / pass gate / terminal / ingest summary；
- redaction metadata。

The builder must use redacted projections for `PageAnalysis`, `LearningBatch`,
`LearnedCapability`, `LearnedPath`, `ExplorationRun`, and composition attempts.
It must not expose DB rows, raw selectors, DOM, private execution handoffs, provider oracle details,
or target seed copy.

## Persistence

Decision: use a new durable `composition_candidates` table.

Rationale:

- Candidates need independent status, retry, static rejection, execution outcome,
  promotion decision, negative evidence, and bundle export.
- `LearningBatch.summary_json` and `ExplorationRun.strategy_json` should remain
  summaries / strategy snapshots, not the source of truth for candidate lifecycle.
- A durable table keeps provider report export independent of private execution
  payloads while still allowing stable redacted refs.

Table fields:

- `id`
- `candidate_id`
- `target_scope_ref`
- `page_template`
- `query_signature`
- `dom_fingerprint`
- `candidate_family`
- `source_capability_ids_json`
- `ordered_capability_kinds_json`
- `expected_terminal_target_json`
- `risk_level`
- `confidence`
- `generation_reason`
- `status`
- `static_rejection_reason`
- `execution_outcome_json`
- `promotion_decision_json`
- `negative_evidence_json`
- `learning_batch_id`
- `source_run_id`
- `promoted_learned_path_id`

`candidate_id` is a stable deterministic id derived from page scope, family,
source capability ids, ordered capability kinds, and expected terminal target.

Status transitions:

```text
generated
  -> rejected_static
  -> ready_for_execution
  -> executing
  -> execution_passed | execution_failed | execution_unverified
  -> promoted_to_learned_path | negative_evidence_recorded
```

Only `execution_passed -> promoted_to_learned_path` may write a `LearnedPath`.

## Schema Changes

Add `apps/api/app/schemas/capability_composition_candidates.py` with:

- `CompositionCandidateStatus`
- `CompositionCandidateFamily`
- `CompositionCandidateRisk`
- `CompositionCandidateConfidence`
- `CompositionCandidatePublic`
- `CompositionCandidateGenerationPolicy`
- `CompositionCandidateGenerationRequest`
- `CompositionCandidateGenerationResult`
- `CompositionCandidateExecutionOutcome`
- `CompositionCandidatePromotionResult`
- coverage metric schemas

Add `apps/api/app/schemas/learning_evidence_bundle.py` with:

- `LearningEvidenceBundle`
- redacted operator action, page analysis, batch, capability, path, run,
  composition, and redaction sections.

Public bundle refs use opaque hashes such as `cap_ref_*`, `path_ref_*`,
`run_ref_*`, and `candidate_ref_*`. Full target URLs, raw UUIDs, selectors,
DOM, seed values, private execution handoffs, provider oracle ids, credentials,
cookies, and tokens are forbidden in bundle payloads.

## Service / Module Design

Create:

- `apps/api/app/models/composition_candidate.py`
- `apps/api/app/repos/composition_candidates_repo.py`
- `apps/api/app/services/learning/capability_graph.py`
- `apps/api/app/services/learning/composition_candidate_generator.py`
- `apps/api/app/services/learning/composition_candidate_executor.py`
- `apps/api/app/services/learning/composition_promotion_service.py`
- `apps/api/app/services/learning/learning_evidence_bundle.py`

Modify:

- `apps/api/app/repos/learned_capabilities_repo.py`: add a focused
  `list_for_page_scope()` helper filtered by page template, query signature,
  DOM fingerprint, and allowed trust.
- `apps/api/app/models/__init__.py`: export the new ORM model.
- Alembic migration: create the new candidate table.

Do not modify:

- Console UI.
- Public autonomous-run endpoints.
- Product prompts with target-specific details.

## API / Conversation Integration

Current package surfaces:

- internal services for candidate generation, execution, promotion, and bundle export；
- conversation history may display redacted composition attempt summaries when the runtime already has them；
- no new public endpoint is required；
- no public endpoint exposes private action payloads。

## Metrics

Candidate coverage metrics are computed from generated candidates and candidate families derived by
WebAgentFlow from user intent, page hints, and bounded policy. Provider-side Validation Site can compute
stronger oracle coverage from private expected families.

WebAgentFlow bundle should provide enough observed data without seeing oracle answers.

Coverage metric formulas:

- `required_family_coverage = generated_required_families / requested_required_families`
- `critical_capability_participation = critical_capabilities_in_candidates / critical_capabilities_available`
- `candidate_reasonable_rate = ready_or_executed_candidates / generated_candidates`
- `execution_attempt_coverage = executed_candidates / ready_for_execution_candidates`
- `promotion_reliability = promoted_candidates_with_pass_evidence / promoted_candidates`
- `negative_evidence_capture_rate = failed_or_rejected_recorded / failed_or_rejected_total`

When a denominator is zero, the metric is `null` with a reason rather than `1.0`.

## Security / Redaction

Evidence report must redact:

- selectors；
- raw DOM；
- target seed values；
- cookies / credentials；
- provider oracle details。

Additional rule: public `target_url` from the contract is represented in
provider-facing bundles as `target_scope_ref` plus `page_template`. Runtime rows
may keep target URL / page scope for operation, but public artifacts must not
publish full URLs unless an approved operator action log explicitly requires it
and the URL has been redacted.

## Failure / Edge Cases

- No terminal action capability: generate `rejected_static` with missing terminal reason.
- Missing slot binding: generate `rejected_static`; do not call executor.
- Provisional trust not allowed: reject statically unless policy explicitly allows it.
- Multiple source capabilities write the same control: reject statically.
- Existing high-confidence LearnedPath exists: do not generate a primary executable candidate for the same family; record learned-path preference.
- Executor returns failure: candidate becomes `execution_failed` and negative evidence is recorded.
- Executor returns insufficient terminal evidence: candidate becomes `execution_unverified`; no promotion.
- Promotion dedupe finds existing equivalent LearnedPath: record promoted path ref without duplicating actions.
- Redaction scan finds forbidden token: bundle export fails closed.

## Out Of Scope

- Cross-page workflow composition。
- Full arbitrary form workflow synthesis。
- LLM-authored browser steps。
- Live validation in this docs package。
