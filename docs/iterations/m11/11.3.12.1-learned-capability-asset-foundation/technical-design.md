# Technical Design

状态：proposed

## Current State

Existing asset persistence is centered on:

- `apps/api/app/models/learned_path.py`
- `apps/api/app/repos/learned_paths_repo.py`
- `apps/api/app/schemas/learned_path.py`
- `apps/api/app/routers/exploration.py`
- `apps/api/alembic/versions/20260424_0001_add_learned_paths.py`

`LearnedPath` has no generic metadata column today. Composition metadata must not be hidden inside
`query_signature` or `actions`. This child does not add a LearnedPath metadata column; that decision is deferred
to the future runtime composition child package.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Persist atomic capability assets | New `LearnedCapability` ORM + migration + repo | `test_learned_capabilities_repo.py` | Does not change learning generation |
| Stable dedup | `compute_capability_dedup_key()` canonical JSON sha256 | repo unit tests | Excludes sample values |
| Trust/provenance independent from LearnedPath | Reuse enum values, separate table columns, separate repo methods | repo compatibility tests | No LearnedPath trust mutation |
| Evidence redaction boundary | Summary/detail schemas omit raw selector detail from normal projection | schema/API tests | Debug raw selectors not required in Phase 1 |
| Existing LearnedPath compatibility | No LearnedPath schema change | learned_paths regression tests | Old rows remain valid |
| No target hardcoding | no runtime route/label/test-id constants | hardcoding scan | Tests may use synthetic generic labels |

## Proposed Implementation

### Files

Create:

- `apps/api/app/models/learned_capability.py`
- `apps/api/app/repos/learned_capabilities_repo.py`
- `apps/api/app/schemas/learned_capability.py`
- `apps/api/alembic/versions/20260605_0001_add_learned_capabilities.py`
- `apps/api/tests/test_learned_capabilities_repo.py`

Modify:

- `apps/api/app/models/__init__.py` to export/import `LearnedCapability`.

Forbidden files for this child:

- `apps/api/app/models/learned_path.py`
- `apps/api/app/schemas/learned_path.py`
- `apps/api/app/repos/learned_paths_repo.py`
- `apps/api/app/routers/exploration.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/cli/wagent/chat.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- Console UI files.

### Database Schema

Create table `learned_capabilities`:

- `id`: `String(36)`, primary key.
- `page_template`: `String(512)`, non-null.
- `query_signature`: `JSON`, non-null, default `{}` in ORM and server default `'{}'` where supported by existing style.
- `dom_fingerprint`: `String(64)`, non-null.
- `capability_key`: `String(255)`, non-null.
- `capability_kind`: `String(64)`, non-null.
- `human_label`: `String(255)`, nullable.
- `region_ref`: `String(255)`, non-null.
- `control_ref`: `String(512)`, non-null.
- `adapter_type`: `String(64)`, non-null.
- `action_schema_json`: `JSON`, non-null.
- `sample_value_policy_json`: `JSON`, non-null.
- `terminal_target_json`: `JSON`, non-null.
- `evidence_json`: `JSON`, non-null.
- `provenance`: `String(16)`, non-null, default `system`.
- `trust`: `String(16)`, non-null, default `provisional`.
- `trust_reason`: `Text`, nullable.
- `trust_updated_at`: `DateTime(timezone=True)`, nullable.
- `source_run_id`: `String(36)`, nullable, FK to `exploration_runs.id`, `ondelete=SET NULL`.
- `source_learned_path_id`: `String(36)`, nullable, FK to `learned_paths.id`, `ondelete=SET NULL`.
- `dedup_key`: `String(64)`, non-null, unique.
- timestamps from `TimestampMixin`.

Indexes:

- unique constraint `uq_learned_capabilities_dedup_key`.
- index `ix_learned_capabilities_page_kind` on `page_template`, `capability_kind`.
- index `ix_learned_capabilities_trust` on `trust`.
- index `ix_learned_capabilities_source_run` on `source_run_id`.

No LearnedPath migration is included in this child.

### Repository

`compute_capability_dedup_key()` canonical payload:

```python
{
    "page_template": page_template,
    "query_signature": query_signature,
    "dom_fingerprint": dom_fingerprint,
    "capability_kind": capability_kind,
    "region_ref": region_ref,
    "control_ref": control_ref,
    "terminal_target_json": terminal_target_json,
}
```

`LearnedCapabilityRepository` methods:

- `ingest(...) -> tuple[LearnedCapability, bool]`
- `get(capability_id: str) -> LearnedCapability | None`
- `find_by_identity(...) -> LearnedCapability | None`
- `list_page(..., cursor, limit, page_template=None, capability_kind=None, trust=None)`
- `set_trust(capability_id, status, reason)`

Duplicate ingest behavior mirrors `LearnedPathRepository`: return existing row and `created=False`;
do not overwrite original evidence.

### Schemas

Add:

- `CapabilityEvidenceSummary`
- `LearnedCapabilitySummary`
- `LearnedCapabilityDetail`

Normal summary includes identity, kind, label, trust, provenance, source ids, created/updated timestamps,
and redacted evidence summary. Detail includes `action_schema`, `terminal_target`, and `sample_value_policy`,
but still does not expose raw DOM or raw selector-only debug payload unless explicitly present in a future debug schema.

### API

No HTTP API routes are implemented in this child. `apps/api/app/schemas/learned_capability.py`
is created so later service/API packages can consume stable projections without reopening asset
identity and evidence contracts.

## Affected Surfaces

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No HTTP endpoints | No existing route changes |
| API response schema | No | New internal/future schemas only | Existing LearnedPath schema unchanged |
| Database schema / migration | Yes | New `learned_capabilities` table only | Old rows remain readable |
| CLI | No | No `wagent` change | N/A |
| Console UI | No | No UI change | N/A |
| Conversation events | No | No event change | N/A |
| Replay execution | No | No replay change | N/A |
| Reporter | No | No reporter change | N/A |
| Worker / async jobs | No | No batch/job change | N/A |
| Tests / fixtures | Yes | Repo/API/compat tests | No live tests |
| Docs | Yes | Child review closeout | Parent current state update after closeout |

## Compatibility

- Existing `learned_paths` rows remain readable and replayable.
- Existing `exploration_runs` rows remain readable.
- `LearnedCapability` cannot be interpreted as complete workflow success.
- No existing LearnedPath schema or API projection changes in this child.

## Failure / Edge Cases

- Duplicate dedup key: repo catches integrity race and returns existing row.
- Invalid trust transition: repo raises `ValueError`; no router translation in this child.
- Missing source run: allowed; `source_run_id` nullable for future user-demonstration assets.
- Deleted source run/path: FK `SET NULL`.
- Empty evidence warnings: default `[]`.

## Non-goals

- No batch lifecycle.
- No chat timeout or cancel.
- No bounded learning planner changes.
- No Page Understanding hint changes.
- No composition runtime.
- No live validation.

## Test Matrix

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Repo ingest | Create, dedup, trust, source ids | `test-plan.md` repo tests |
| Migration / model | Table columns and old LearnedPath compatibility | `test-plan.md` compatibility tests |
| Schemas | Summary/detail projection and redaction | `test-plan.md` schema assertions |
| Regression | Existing LearnedPath repo/API tests still pass | `test-plan.md` regression tests |
| Hardcoding | No target route/label constants | `test-plan.md` scan |

## Validation Commands

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v
uv run ruff check apps/api/app apps/api/tests
rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app
```
