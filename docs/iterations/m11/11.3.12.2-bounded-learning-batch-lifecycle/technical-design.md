# Technical Design

状态：implemented

## Current State

Current product-level URL-only learning lives in `LearningRunService._run_capability_discovery()`:

- it seed-analyzes the page;
- builds filter inventory;
- generates a discovery batch id string;
- generates scenarios from current capability discovery logic;
- executes each scenario synchronously in a new runtime context;
- persists `ExplorationRun` and maybe `LearnedPath`;
- returns aggregate `LearningRunResult` fields to `chat_runtime.py`.

There is no durable `learning_batches` table, no policy object, no batch repository, no batch status history,
and no service-owned cancellation handle. `wagent chat` has a client HTTP timeout, but that timeout is not a
backend lifecycle contract.

11.3.12.1 added:

- `LearnedCapability` ORM / migration / repository / schemas;
- recursive redaction and forbidden direct action-payload validation;
- repo-local tests and LearnedPath compatibility regression.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Durable batch handle | New `LearningBatch` ORM, migration, repository | model / repo tests | Old runs without batch remain valid |
| Bounded policy | `BoundedLearningPolicy` schema + planner budget enforcement | policy / planner tests | Defaults must avoid all-pairwise expansion |
| Terminal statuses | `LearningBatchStatus` enum-like literals and status derivation helper | status tests | Terminal statuses cannot be reopened except explicit future package |
| Cancel safety | Cooperative cancel checks before/after safe scenario boundaries | controller unit tests | No cross-batch runtime close |
| Timeout safety | Monotonic clock budget checks between scenarios | timeout tests with fake clock | No live browser required |
| No success without closed evidence | `LearningRunResult` includes batch status / id / summary; chat event reads it | chat runtime tests | Active task cleared on terminal batch |
| No writes after cancelled | controller checks status before attach asset ids | repo / service tests | Cancellation is terminal |
| LearnedPath compatibility | old fields retained; optional batch id only in strategy metadata | existing regression tests | Old rows remain readable |
| No target hardcoding | code uses generic policy / scenario metadata | hardcoding scan | Tests may use synthetic labels |

## Proposed Implementation

### Files

Create:

- `apps/api/app/models/learning_batch.py`
- `apps/api/app/repos/learning_batches_repo.py`
- `apps/api/app/schemas/learning_batch.py`
- `apps/api/app/services/learning/bounded_learning.py`
- `apps/api/app/services/learning/learning_batch_controller.py`
- `apps/api/alembic/versions/20260605_0002_add_learning_batches.py`
- `apps/api/tests/test_learning_batches_repo.py`
- `apps/api/tests/test_bounded_learning_batch_lifecycle.py`

Modify:

- `apps/api/app/models/__init__.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`

Forbidden in this child:

- no Console UI;
- no new LearnedCapability HTTP API;
- no runtime capability composition;
- no Page Understanding hint schema changes;
- no direct autonomous-run endpoint calls;
- no target-specific runtime constants.

### Data Model / Migration

Create table `learning_batches`:

- `id`: `String(36)`, primary key.
- `session_id`: `String(36)`, nullable, index.
- `target_url`: `String(2048)`, non-null.
- `page_template`: `String(512)`, nullable until seed analysis completes.
- `query_signature`: `JSON`, non-null, default `{}`.
- `dom_fingerprint`: `String(64)`, nullable until seed analysis completes.
- `status`: `String(32)`, non-null, indexed.
- `policy_json`: `JSON`, non-null.
- `request_json`: `JSON`, non-null.
- `planned_scenarios_json`: `JSON`, non-null, default `[]`.
- `summary_json`: `JSON`, non-null, default `{}`.
- `created_run_ids_json`: `JSON`, non-null, default `[]`.
- `created_capability_ids_json`: `JSON`, non-null, default `[]`.
- `created_learned_path_ids_json`: `JSON`, non-null, default `[]`.
- `started_at`: `DateTime(timezone=True)`, nullable.
- `completed_at`: `DateTime(timezone=True)`, nullable.
- `cancel_requested_at`: `DateTime(timezone=True)`, nullable.
- timestamps.

Indexes:

- `ix_learning_batches_session_status` on `session_id`, `status`.
- `ix_learning_batches_status` on `status`.
- `ix_learning_batches_created_at` on `created_at`.

No backfill is required. Existing `ExplorationRun.strategy_json` may receive `learning_batch_id` for new runs.

### Schemas

Add `apps/api/app/schemas/learning_batch.py`:

- `LearningBatchStatus`
- `LearningBatchTerminalReason`
- `BoundedLearningPolicy`
- `LearningBatchRequestSummary`
- `LearningBatchScenarioSummary`
- `LearningBatchSummary`
- `LearningBatchDetail`

Projection rules:

- summary/detail include ids and counts;
- user-facing summary hides raw selectors, raw DOM, raw action payloads, and seed values;
- operator/debug raw projection is out of scope.

### Repository

`LearningBatchRepository`:

- `create_pending(...)`
- `mark_running(batch_id, page_identity=None, planned_scenarios=None)`
- `request_cancel(batch_id, reason)`
- `mark_terminal(batch_id, status, summary, created ids)`
- `append_run(batch_id, run_id)`
- `append_capability(batch_id, capability_id)`
- `append_learned_path(batch_id, learned_path_id)`
- `get(batch_id)`
- `list_for_session(session_id, status=None, cursor=None, limit=20)`

Repository must reject asset attachment after terminal `cancelled`.

### Service / Module Design

`bounded_learning.py`:

- `default_bounded_learning_policy()`
- `apply_policy_to_scenarios(inventory, scenarios, policy)`
- `should_stop_after_attempt(state, policy)`
- `derive_batch_terminal_status(...)`

`learning_batch_controller.py`:

- owns a `LearningBatchRepository`;
- accepts a monotonic clock injectable for tests;
- accepts a `cancel_checker(batch_id) -> bool` injectable for service-level cooperative cancellation tests and
  future API / async callers;
- creates pending batch before seed analysis;
- marks running after seed identity and planned scenarios are known;
- checks repository cancel state, `cancel_checker`, and timeout before each scenario;
- appends run/capability/path ids after each scenario;
- marks terminal status exactly once.

The first implementation may remain synchronous. It must still return a closed `LearningRunResult` with
`learning_batch_id`, `learning_batch_status`, and `learning_batch_summary`.

Synchronous v1 does not claim true user-facing in-flight cancellation through CLI Ctrl+C or a second chat
message. Current `wagent chat` waits for the dispatch response and cannot send another cancel message while
the same request is blocked in the learning handler. V1 cancellation coverage is therefore service/controller
level via repository `request_cancel()` or the injected cancel checker. Product-level in-flight cancel needs a
future async/progress/cancel API package.

### LearningRunService Integration

Extend `LearningRunRequest`:

- `session_id: str | None = None`
- `bounded_policy: BoundedLearningPolicy | None = None`
- `learning_batch_id: str | None = None` only for future resume/cancel-aware calls, not required for v1.

Extend `LearningRunResult`:

- `learning_batch_id: str | None = None`
- `learning_batch_status: str | None = None`
- `learning_batch_summary: dict[str, Any] = field(default_factory=dict)`

In `_run_capability_discovery()`:

1. Create pending batch.
2. Check cancellation before seed analysis.
3. Seed-analyze the page and update identity.
4. Build inventory and scenario candidates.
5. Apply bounded policy.
6. Mark running with planned scenarios.
7. Execute scenarios synchronously with safe boundary checks.
8. Persist `ExplorationRun` as today, adding `learning_batch_id` to strategy metadata.
9. Persist `LearnedCapability` rows for passed atomic capability evidence where 11.3.12.1 repository accepts
   the payload. Compatibility `LearnedPath` writes may remain for current chat behavior.
10. Derive terminal batch status and return aggregate result.

LearnedCapability mapping for v1:

- `capability_kind`: map current scenario kinds / bindings to `control_input`, `control_select`,
  `control_toggle`, or `submit_search`; unsupported or ambiguous mappings are summarized as failed /
  unsupported instead of forced into a row.
- `action_schema_json`: use `capability_action.v1` with `adapter_type`, `operation`, `required_slots`, and
  `control_binding` containing stable role / binding metadata only. Do not include direct Playwright,
  LLM, replay, execution, or raw payload keys.
- `sample_value_policy_json`: record value source class such as visible option / visible row / synthetic low
  confidence, without seed values in public summary.
- `terminal_target_json`: record generic terminal target kind such as `list_refresh`, `empty_result`,
  `query_persisted`, or `unknown`, not raw DOM.
- `evidence_json`: use `capability_evidence.v1` with source, terminal outcome, business-match flag,
  evidence strength, warnings, and redaction marker. Raw selectors from existing scenario summaries stay in
  raw run evidence and must not be copied into chat/event projections.

### Conversation Integration

`chat_runtime.py` should pass `session_id` into the learning handler and persist batch status in events:

- `chat_learning_started`: include `learning_batch_id` when available, or an event once the result returns if
  synchronous v1 cannot know it before the call.
- `chat_learning_completed`: include `learning_batch_id`, `learning_batch_status`, and sanitized summary.
- `chat_learning_failed`: include `learning_batch_id`, `learning_batch_status`, timeout / cancel reason when
  available.

On terminal batch result, active task must be cleared. If a future async detach is implemented, active task
may point to resumable batch status instead, but v1 should not claim async detach.

For failed / unverified terminal batch results, `_learning_failed()` must deliberately clear the learning
active task when `learning_result.learning_batch_status` is terminal. The current behavior of merely marking
the active task as `failed` is not sufficient for this child.

## Data Flow

```text
Conversation learn request
  -> LearningRunRequest(session_id, bounded_policy)
  -> LearningBatchController.create_pending
  -> seed PageAnalysis
  -> bounded scenario planning
  -> scenario loop with cancel/timeout checks
  -> ExplorationRun + LearnedCapability / compatibility LearnedPath writes
  -> LearningBatch terminal summary
  -> LearningRunResult with batch id/status
  -> chat events + active_task closeout
```

## Status / State Derivation

Priority:

1. `partial_success` if timeout or cancellation is observed after useful assets were persisted.
2. `cancelled` if cancellation is observed before any useful asset was persisted.
3. `timed_out` if wall-clock budget expires before any useful asset was persisted.
4. `completed` if all planned scenarios close and all required evidence gates pass.
5. `partial_success` if at least one useful asset passed and failed / unsupported / unverified remainders exist.
6. `unverified` if no useful asset passed but unverified scenario evidence exists.
7. `failed` otherwise.

`cancel_requested` is non-terminal and must not be the final status.

## Compatibility

- Existing tests that assert `LearningRunResult.run_ids`, `learned_path_ids`, capability summaries, and
  learning outcome should continue to pass after adding batch fields.
- Existing `LearnedPathRepository` and exploration API behavior remains compatible.
- Existing CLI `wagent chat` timeout flag remains a transport timeout, not the backend lifecycle authority.

## Failure / Edge Cases

- No supported scenarios: batch terminal status `failed`; unsupported summaries are recorded.
- All scenarios unverified: batch terminal status `unverified`; no successful asset is advertised.
- Timeout before first scenario: `timed_out`.
- Timeout after passed capabilities: `partial_success`.
- Cancellation before seed analysis or before any useful asset: `cancelled`.
- Cancellation after passed capabilities but before next scenario: `partial_success` with cancellation reason.
- Repository race on terminal status: terminal mark is idempotent only if status and summary are unchanged.
- LearnedCapability ingest rejects unsafe payload: scenario is recorded as failed / unsupported, not silently
  dropped.

## Non-goals

- No async worker queue.
- No progress streaming API.
- No Console batch detail page.
- No Page Understanding hint schema.
- No capability composition runtime.
- No live validation.

## Test Matrix

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Model / migration | Batch table metadata and server defaults | `test-plan.md` model / migration entries |
| Repository | status transitions, cancel, terminal attachment rules | `test-plan.md` repo tests |
| Policy | scenario count and all-pairwise suppression | `test-plan.md` bounded policy tests |
| Service integration | `_run_capability_discovery()` creates and closes batch | `test-plan.md` service tests |
| Timeout / cancel | fake clock / cancellation hook closes terminal status | `test-plan.md` lifecycle tests |
| Chat runtime | events carry batch status and active task closes | `test-plan.md` chat tests |
| Compatibility | LearnedPath / LearnedCapability tests continue to pass | `test-plan.md` regression tests |
| Static safety | no target hardcoding, scoped ruff | `test-plan.md` static checks |

## Validation Commands

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_batches_repo.py tests/test_bounded_learning_batch_lifecycle.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v
uv run ruff check apps/api/app/models/learning_batch.py apps/api/app/repos/learning_batches_repo.py apps/api/app/schemas/learning_batch.py apps/api/app/services/learning/bounded_learning.py apps/api/app/services/learning/learning_batch_controller.py apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_batches_repo.py apps/api/tests/test_bounded_learning_batch_lifecycle.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/alembic/versions/20260605_0002_add_learning_batches.py
rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app
```
