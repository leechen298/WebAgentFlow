# Technical Design

状态：proposed

## Current State

`LearnedCapability` rows now store atomic action schema, sample value policy, terminal target, evidence, trust, and
source references. Bounded learning can create capability rows. PageAnalysis can expose redacted capability hints.
There is not yet a runtime service that retrieves multiple capabilities and builds a deterministic composition plan.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Deterministic plan | New composition schemas + service | schema / service tests | Plan construction is not execution |
| Compatibility checks | Capability candidate filter | service tests | Fail closed on cross-page / missing slot / unsupported adapter |
| LearnedPath preference | explicit resolver branch | service tests | Existing high-confidence path wins |
| Public/private boundary | redacted public plan + private execution handoff | schema / redaction tests | No selector in public plan |
| Promotion gate | helper requires execution pass evidence | service tests | No LearnedPath write from plan alone |
| Compatibility | additive files and optional metadata only | regression tests | Old rows remain valid |

## Proposed Implementation

### Files

Create:

- `apps/api/app/schemas/capability_composition.py`
- `apps/api/app/services/learning/capability_composer.py`
- `apps/api/tests/test_capability_composer.py`

Modify if needed:

- `apps/api/app/repos/learned_capabilities_repo.py` for a focused page-scope lookup helper.
- `apps/api/app/services/learning/learned_path_replay.py` only if an execution-handoff helper needs existing replay
  compatibility checks; do not change replay execution semantics.
- `apps/api/tests/test_learned_capabilities_repo.py` for lookup regression.

Forbidden in this child:

- Console UI;
- new public HTTP API;
- direct autonomous-run endpoint callers;
- LLM-authored browser step execution;
- live validation;
- target-specific runtime constants.

### Schemas

Add `capability_composition.py` with:

- `CapabilityCompositionStatus`
- `CapabilityCompositionRisk`
- `CapabilityCompositionStep`
- `CapabilityCompositionPlan`
- `CapabilityCompositionResult`
- `CapabilityExecutionHandoff`
- `CapabilityCompositionPolicy`

The public plan must carry redacted step refs and source capability ids. `CapabilityExecutionHandoff` may carry private
binding payloads but must stay service-internal and must not be returned by normal user-facing schemas.

### Service Design

`CapabilityComposer`:

1. resolve current page scope from target URL and optional PageAnalysis;
2. check whether an existing high-confidence LearnedPath should be preferred;
3. retrieve LearnedCapability candidates for the page scope;
4. filter by capability kind, trust, adapter support, terminal target, current capability hints, and required slots;
5. order capabilities under deterministic v1 rules;
6. build a public `CapabilityCompositionPlan`;
7. build a private execution handoff only when plan status is `ready`;
8. expose a promotion guard that accepts execution evidence and source capability ids.

### Candidate Matching

Minimum v1 request inputs:

- `target_url`
- `page_template`
- `user_goal`
- `required_capability_kinds`
- `slot_bindings`
- optional `current_page_analysis`
- optional `prefer_learned_path_match`

Candidate filter rules:

- reject capabilities outside the page template;
- reject unsupported `action_schema_json.version`;
- reject forbidden action schema keys already guarded by the repo;
- reject missing required slot bindings;
- reject conflicting bindings for the same control ref;
- reject low-trust candidates unless policy allows provisional trust.

### Execution Handoff

The service may produce an internal handoff:

```text
composition_id
source_capability_ids
ordered private action schemas
slot bindings
expected terminal target
```

The handoff is for existing execution/replay services only. It is not a public response and must not be stored as a
successful LearnedPath by itself.

### Promotion Guard

Add a small helper that returns `promotable=true` only when execution evidence includes:

- source `composition_id`;
- successful execution status;
- terminal evidence compatible with expected target;
- no missing required capability;
- source capability ids.

The helper may return metadata for a future LearnedPath write, but this child should avoid broad LearnedPath model
changes unless design review decides they are required.

## Data Flow

```text
user goal + page scope
  -> existing LearnedPath check
  -> LearnedCapability lookup
  -> compatibility filter
  -> deterministic ordered plan
  -> private execution handoff
  -> execution evidence
  -> promotion guard
```

## Compatibility

- Existing LearnedCapability repository behavior remains unchanged unless a lookup helper is added.
- Existing LearnedPath replay remains preferred and unchanged.
- Existing learning batch closeout remains unchanged.
- Public plan schemas are additive and not exposed through a new API in this child.

## Failure / Edge Cases

- No candidate: return `missing_capability` with missing kinds.
- Multiple equally good candidates: return `ambiguous` unless deterministic tie-break is safe.
- Cross-page candidate: reject as `unsafe`.
- Required slot missing: reject as `missing_capability`.
- Existing LearnedPath match: return `prefer_learned_path`.
- Execution evidence fails: promotion guard returns not promotable.

## Non-goals

- No Console UI.
- No new HTTP API.
- No live validation.
- No LLM browser-step execution.
- No old-data backfill.

## Test Matrix

- Schema defaults, public redaction, and status taxonomy.
- Candidate compatibility checks.
- LearnedPath preference.
- Deterministic ordering and conflict rejection.
- Private handoff contains executable action schema while public plan stays redacted.
- Promotion guard rejects plan-only / failed / missing-terminal evidence.
- Repository lookup compatibility if added.
- Hardcoding scan over runtime code.
