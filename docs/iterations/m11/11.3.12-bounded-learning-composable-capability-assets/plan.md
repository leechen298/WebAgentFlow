# Plan

状态：umbrella_routing

## Documentation Phase

1. Read product model, iteration standards, M11 index, 11.3.10 / 11.3.11 context.
2. Create the 11.3.12 seven-document package.
3. Update `docs/product-model.md` with the new `LearnedCapability` product concept and M11.3.12 milestone row.
4. Update `docs/iterations/m11/README.md` with the 11.3.12 package entry.
5. Update `docs/roadmap.md` M11.3 post-closeout section with the new planned follow-up.
6. Record implementation authorization as `no` until design review is complete.
7. Convert this package to an umbrella / campaign package if design review finds
   the implementation scope too broad for one code package.

## Child Package Queue

### 11.3.12.1 - LearnedCapability Asset Foundation

Status: `PACKAGE_COMPLETE`
Type: mixed / code-gated
Goal: add the persistent `LearnedCapability` asset foundation without changing learning
or replay behavior.

Why this exists: parent design review found that asset persistence can be implemented
and verified independently, while batch lifecycle and runtime composition still need
separate design decisions.

Inputs / required reading:

- parent `contract.md`, especially LearnedCapability / CapabilityEvidence /
  compatibility / hardcoding prohibition;
- parent `technical-design.md`, Data Model and LearnedPath compatibility sections;
- `apps/api/app/models/learned_path.py`;
- `apps/api/app/repos/learned_paths_repo.py`;
- `apps/api/app/schemas/learned_path.py`;
- `apps/api/alembic/versions/20260424_0001_add_learned_paths.py`;
- `apps/api/tests/test_learned_paths_repo.py`;
- `apps/api/tests/test_exploration_learned_paths_api.py`.

Allowed changes:

- add `apps/api/app/models/learned_capability.py`;
- add `apps/api/app/repos/learned_capabilities_repo.py`;
- add `apps/api/app/schemas/learned_capability.py`;
- add an Alembic migration for `learned_capabilities`;
- do not add `learned_paths.metadata_json` in this child; composition metadata
  lands in 11.3.12.4 if still needed;
- do not add read-only debug API in this child; API/debug projection lands in a later
  package if needed;
- add focused API/repo/migration tests.

Forbidden changes:

- do not change URL-only learning scenario generation;
- do not implement `LearningBatchController`;
- do not change `wagent chat` timeout behavior;
- do not change replay selection or execution behavior;
- do not implement capability composition runtime;
- do not run live autonomous validation or `verify-scenario`;
- do not hardcode `/users`, fixture labels, selectors, DOM test ids, or seed values
  in runtime code.

Expected deliverables:

- `LearnedCapability` ORM and migration with explicit SQL types, indexes, FK rules,
  unique `dedup_key`, trust/provenance fields, and JSON evidence fields;
- repository idempotent ingest and trust/read helpers;
- Pydantic summary/detail/evidence schemas with normal redaction boundary;
- old `LearnedPath` compatibility preserved;
- focused tests and review evidence.

Expected tests / verification:

- `.venv/bin/pytest apps/api/tests/test_learned_capabilities_repo.py -v`
- `.venv/bin/pytest apps/api/tests/test_learned_paths_repo.py apps/api/tests/test_exploration_learned_paths_api.py -v`
- `uv run ruff check apps/api/app apps/api/tests` or the repo-equivalent ruff command;
- `rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app` scoped
  hardcoding scan, reviewed so false positives are explained.

Compatibility constraints:

- existing `learned_paths` rows remain readable and replayable;
- existing `exploration_runs` rows remain readable;
- no old API response field is removed or renamed;
- new LearnedCapability evidence must not claim complete workflow success.

Scope guardrails:

- this child only creates the asset foundation; read/debug projection is deferred;
- no autonomous run, no batch lifecycle, no planner scenario policy, no composition.

Exit criteria:

- child `review.md` records implementation evidence and no unresolved P0/P1;
- parent `CURRENT_STATE.md` advances to 11.3.12.2 only after child status
  `PACKAGE_COMPLETE`.

Handoff to next package:

- 11.3.12.2 may consume the repository and schemas to persist batch-created
  capabilities.

### 11.3.12.2 - Bounded Learning Batch Lifecycle

Status: `PACKAGE_COMPLETE`
Type: mixed / code-gated
Goal: implement bounded scenario planning and close/cancel/detach semantics for learning
batches.

Required precondition: 11.3.12.1 `PACKAGE_COMPLETE`.

Why this exists: URL-only learning currently runs a synchronous sequence of capability scenarios with only
an in-memory `discovery_batch_id`. A CLI timeout or interruption is not a backend lifecycle contract. The
system needs a durable batch handle, bounded policy, terminal status, and cancel / timeout semantics before
later packages add richer hints or runtime composition.

Inputs / required reading:

- parent `contract.md`, especially BoundedLearningPolicy and Learning Batch Lifecycle Contract;
- parent `technical-design.md`, especially `learning_batches`, `LearningBatchController`, and
  Conversation Integration;
- `11.3.12.1-learned-capability-asset-foundation/review.md`;
- `apps/api/app/services/learning/learning_run_service.py`;
- `apps/api/app/services/conversation/chat_runtime.py`;
- `apps/api/tests/test_learning_run_service.py`;
- `apps/api/tests/test_conversation_chat_runtime.py`;
- `apps/cli/wagent/chat.py` timeout behavior and `apps/cli/tests/test_chat.py`.

Allowed changes:

- add `LearningBatch` ORM / migration / repo / schemas;
- add bounded policy helpers and `LearningBatchController`;
- integrate URL-only capability discovery with a durable batch record;
- add `learning_batch_id` to new scenario `ExplorationRun.strategy_json`;
- extend `LearningRunResult` and chat events with batch id / status / sanitized summary;
- persist safe `LearnedCapability` rows from passed atomic evidence when the 11.3.12.1 repository accepts
  the payload;
- preserve existing compatibility `LearnedPath` writes where current chat behavior still needs them;
- add focused model / repo / service / chat tests.

Forbidden changes:

- do not implement Page Understanding capability hints;
- do not implement runtime capability composition;
- do not add Console UI batch detail;
- do not call direct autonomous-run endpoints;
- do not run live autonomous validation or `verify-scenario`;
- do not hardcode `/users`, fixture labels, selectors, DOM test ids, seed values, or route-specific prompt text.

Expected deliverables:

- durable `learning_batches` table with terminal status and summary fields;
- `BoundedLearningPolicy` default that avoids all-pairwise expansion;
- cooperative cancel / timeout checks at safe scenario boundaries;
- terminal status derivation for completed / partial_success / timed_out / cancelled / failed / unverified;
- LearningRunService aggregate result with batch id / status / summary;
- chat learning completed / failed events that include sanitized batch status and clear active task for terminal
  synchronous results;
- focused tests and review evidence.

Expected tests / verification:

- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_batches_repo.py tests/test_bounded_learning_batch_lifecycle.py -v`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_exploration_learned_paths_api.py -v`
- scoped `uv run ruff check ...` over new/changed files;
- Alembic online migration or exact online failure plus offline SQL generation;
- `rg -n '(/users|Alice|Bob|data-testid|validation-site)' apps/api/app`.

Compatibility constraints:

- old `learned_paths` rows remain readable and replayable;
- old `exploration_runs` rows without `learning_batch_id` remain valid;
- current `LearningRunResult` fields used by chat remain populated;
- no old public API response field is removed or renamed;
- CLI timeout remains a transport setting, not the source of backend batch truth.

Scope guardrails:

- this child owns batch lifecycle only;
- async detach can be deferred if synchronous v1 returns a closed terminal batch status;
- progress streaming, Console UI, Page Understanding hints, and composition remain future packages.

Exit criteria:

- child design review has no unresolved P0 / P1;
- implementation evidence is recorded in child `review.md`;
- required scoped tests pass or unrelated failures are recorded truthfully;
- parent `CURRENT_STATE.md` advances to 11.3.12.3 only after child status `PACKAGE_COMPLETE`.

Handoff to next package:

- 11.3.12.3 may consume batch status and policy to enrich Page Understanding capability hints.

Design decisions selected by child docs:

- use a `learning_batches` table for the durable handle;
- keep first implementation synchronous, with backend-owned timeout / cancel checks and terminal closeout;
- defer async detach / cancel API until a later package unless implementation review proves it is required;
- use `bounded_learning_policy.v1` with finite default budgets.

### 11.3.12.3 - Page Understanding Capability Hints

Status: `PACKAGE_COMPLETE`
Type: mixed / code-gated
Goal: extend deterministic page hints into capability candidate ranking inputs.

Required precondition: 11.3.12.2 `PACKAGE_COMPLETE`.

Why this exists: 11.3.12.2 can run bounded single-capability learning, but PageAnalysis still lacks a
target-agnostic capability hint projection. This child lets bounded learning rank page regions, controls, terminal
targets, safe sample value sources, and explicit dependency groups without target-specific runtime constants.

Inputs / required reading:

- child `11.3.12.3-page-understanding-capability-hints/contract.md`;
- child `technical-design.md`, especially public hint projection vs private executable bindings;
- `apps/api/app/schemas/page_analysis.py`;
- `apps/api/app/services/learning/page_analyzer.py`;
- `apps/api/app/services/learning/capability_discovery.py`;
- `apps/api/tests/test_page_analyzer_selector.py`;
- `apps/api/tests/test_filter_capability_discovery.py`;
- `apps/api/tests/test_learning_run_service.py`.

Allowed changes:

- add additive capability hint schemas and deterministic hint builder;
- extend PageAnalysis with optional/default capability hints;
- integrate PageAnalyzer and capability discovery to prefer hints when present;
- keep private resolver bindings process-local so redacted hint refs can still map back to executable
  `DiscoveredElement` metadata;
- add focused schema / analyzer / discovery / regression tests.

Forbidden changes:

- do not implement capability composition runtime;
- do not change LearnedCapability or LearnedPath persistence semantics unless a design review finds a compatibility
  bug;
- do not add Console UI or API projection surfaces;
- do not call direct autonomous-run endpoints;
- do not run live autonomous validation or `verify-scenario`;
- do not hardcode `/users`, fixture labels, selectors, DOM test ids, seed values, or route-specific prompt text in
  runtime code.

Expected deliverables:

- public `CapabilityHintSet` with redacted region / control / terminal / dependency / sample source hints;
- runtime-private hint resolver or equivalent mapping for executable bindings;
- capability discovery that can plan from hints while preserving fallback behavior;
- dependency-pair planning only when explicit hints and bounded policy both allow it;
- focused tests and review evidence.

Expected tests / verification:

- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_hints.py tests/test_filter_capability_discovery.py -v`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_page_analyzer_selector.py tests/test_learning_run_service.py tests/test_bounded_learning_batch_lifecycle.py -v`
- scoped `uv run ruff check ...` over changed schema / service / test files;
- `rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app`.

Compatibility constraints:

- existing PageAnalysis consumers remain compatible when hints are absent;
- existing capability discovery fallback remains available;
- existing LearningBatch, LearnedCapability, LearnedPath, and ExplorationRun rows remain readable;
- serialized hints are safe for logs / artifacts and do not expose executable selectors.

Scope guardrails:

- this child only enriches Page Understanding and capability discovery inputs;
- no composition planner, async job model, Console surface, or live validation.

Exit criteria:

- child design review has no unresolved P0 / P1 and records `implementation_authorized: yes` before code changes;
- implementation evidence is recorded in child `review.md`;
- required scoped tests pass or unrelated failures are recorded truthfully;
- parent `CURRENT_STATE.md` advances only after child status `PACKAGE_COMPLETE`.

Handoff to next package:

- 11.3.12.4 may consume redacted capability hints and executable learned capabilities for composition runtime after
  11.3.12.3 reaches `PACKAGE_COMPLETE`.

Completion evidence:

- redacted `CapabilityHintSet` schemas and deterministic builder implemented;
- PageAnalyzer attaches additive capability hints to PageAnalysis;
- capability discovery prefers hints when present and preserves fallback behavior when hints are absent or empty;
- public hint schemas validate redacted refs directly;
- 58 scoped tests passed, scoped ruff passed, hardcoding scan reviewed;
- no live validation, `verify-scenario`, or `wagent chat` run.

### 11.3.12.4 - Capability Composition Runtime

Status: `PACKAGE_COMPLETE`
Type: mixed / code-gated
Goal: compose compatible LearnedCapabilities under code-owned rules and promote successful
composition into LearnedPath after evidence gate.

Required precondition: 11.3.12.1 asset foundation, 11.3.12.2 batch lifecycle, and 11.3.12.3
capability hints complete. Precondition is satisfied and the seven-document child package now exists.

Why this exists: the parent package promise is not complete until L3 can consume atomic LearnedCapability assets when
a full LearnedPath is unavailable. This child scopes that work to deterministic composition planning, compatibility
checks, private execution handoff, and promotion guard rules without adding UI/API surfaces or LLM browser steps.

Inputs / required reading:

- child `11.3.12.4-capability-composition-runtime/contract.md`;
- child `technical-design.md`, especially public plan vs private execution handoff and promotion gate;
- `11.3.12.1-learned-capability-asset-foundation/review.md`;
- `11.3.12.2-bounded-learning-batch-lifecycle/review.md`;
- `11.3.12.3-page-understanding-capability-hints/review.md`;
- `apps/api/app/models/learned_capability.py`;
- `apps/api/app/repos/learned_capabilities_repo.py`;
- `apps/api/app/schemas/learned_capability.py`;
- `apps/api/app/services/learning/learned_path_replay.py`;
- `apps/api/tests/test_learned_capabilities_repo.py`;
- `apps/api/tests/test_learned_path_replay.py`.

Allowed changes:

- add composition schemas and deterministic composer service;
- add focused LearnedCapability page-scope lookup helper if needed;
- add focused learned-path replay compatibility helper if needed, without changing replay execution semantics;
- add promotion guard helper that requires execution/pass-gate evidence before LearnedPath promotion;
- add focused schema / service / repo / replay regression tests.

Forbidden changes:

- do not add Console UI;
- do not add a new public HTTP API;
- do not call direct autonomous-run endpoints;
- do not run live autonomous validation or `verify-scenario`;
- do not implement LLM-authored browser step execution;
- do not backfill old LearnedPaths into LearnedCapabilities;
- do not hardcode `/users`, fixture labels, selectors, DOM test ids, seed values, or route-specific prompt text.

Expected deliverables:

- public redacted `CapabilityCompositionPlan` / result / policy schemas;
- private execution handoff shape kept out of public user-facing summaries;
- deterministic candidate compatibility and ordering service;
- explicit LearnedPath preference branch;
- promotion guard that rejects plan-only or failed evidence;
- focused tests and review evidence.

Expected tests / verification:

- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_composer.py -v`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_learned_path_replay.py -v`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v`
- scoped `uv run ruff check ...` over changed schema / service / test files;
- `rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app`.

Compatibility constraints:

- existing LearnedPath rows remain readable and replayable;
- existing LearnedCapability rows remain readable;
- existing LearningBatch and ExplorationRun rows remain readable;
- plan construction never claims workflow success without execution evidence;
- public composition summaries do not expose private selectors or runtime payloads.

Scope guardrails:

- this child owns composition schemas, service, private handoff, and promotion guard only;
- no Console surface, public API, live validation, async job model, or LLM step-by-step execution.

Exit criteria:

- child design review has no unresolved P0 / P1 and records `implementation_authorized: yes` before code changes;
- implementation evidence is recorded in child `review.md`;
- required scoped tests pass or unrelated failures are recorded truthfully;
- parent `CURRENT_STATE.md` records the final campaign closeout or next documented route.

Handoff:

- after 11.3.12.4 implementation closeout, parent 11.3.12 can move to final campaign closeout unless implementation
  review identifies a required follow-up child.

Completion evidence:

- deterministic composition schemas and `CapabilityComposer` implemented;
- public plan / private execution handoff boundary enforced;
- LearnedPath preference, candidate compatibility checks, and promotion guard implemented;
- 227 scoped tests passed, scoped ruff passed, hardcoding scan reviewed;
- no live validation, `verify-scenario`, `wagent chat`, Console UI, public API, or LLM browser-step execution.

## Stop Conditions

Stop before implementation if:

- product model update is rejected;
- migration strategy cannot preserve old LearnedPaths;
- batch lifecycle cannot be made cancel-safe;
- composition would require LLM step-by-step execution;
- tests would require unauthorized live autonomous runs.

## Handoff

Next action after 11.3.12.4 closeout:

```text
Parent 11.3.12 is repo-local complete.
Await user direction for commit / push or future live validation inputs.
```
