# Contract

状态：implemented

## Scope

This child package defines and implements the batch lifecycle layer for L1 product learning. It does not
change L1 / L2 / L3 lifecycle stages and does not add an internal Agent role.

## BoundedLearningPolicy

`BoundedLearningPolicy` is a code-owned policy object that limits product learning work before any browser
scenario is started.

Required fields:

- `version`: policy version string, initially `bounded_learning_policy.v1`.
- `max_scenario_count`: maximum planned scenario attempts in one batch.
- `max_wall_clock_seconds`: backend-owned wall-clock budget.
- `max_failures_per_adapter`: repeated failure threshold per adapter / control binding.
- `max_consecutive_no_new_capability`: stop threshold after attempts produce no new persisted capability.
- `allow_dependency_pairs`: whether dependency-pair probes may be planned.
- `allow_all_supported_smoke`: whether the broad all-supported smoke scenario may be planned.
- `cancel_check_interval`: scenario-boundary cancellation check label or interval, not a busy thread loop.

Default policy must prefer independent single-capability probes and must not generate all pairwise
combinations by default.

## LearningBatch

`LearningBatch` is the durable handle for one `start_learning` operation. HTTP request lifetime is not the
batch lifetime.

Required identity / lifecycle fields:

- `id`
- `session_id`
- `target_url`
- `page_template`
- `query_signature`
- `dom_fingerprint`
- `status`
- `policy_json`
- `request_json`
- `planned_scenarios_json`
- `summary_json`
- `created_run_ids_json`
- `created_capability_ids_json`
- `created_learned_path_ids_json`
- `started_at`
- `completed_at`
- `cancel_requested_at`
- timestamps

Allowed statuses:

- `pending`: row created before seed analysis / planning.
- `running`: batch owns current learning execution.
- `completed`: all planned scenarios closed and at least one useful asset was produced with no blocking
  failed / unverified remainder.
- `partial_success`: at least one useful asset was produced, but budget, unsupported controls, failed probes,
  or unverified probes remain.
- `timed_out`: backend wall-clock budget reached.
- `cancel_requested`: cancellation was requested and will be honored at the next safe boundary.
- `cancelled`: cancellation closed the batch; no later asset writes may be attached to this batch.
- `failed`: no useful asset was produced and no unverified-only result explains the failure.
- `unverified`: only unverified evidence was produced or terminal / ingest gate could not confirm assets.

Terminal statuses: `completed`, `partial_success`, `timed_out`, `cancelled`, `failed`, `unverified`.

## Cancel / Timeout / Detach Contract

Cancellation is cooperative at safe boundaries:

- before seed page analysis;
- after seed page analysis and before scenario planning;
- before each scenario run;
- immediately after each scenario run before persisting batch summary.

The controller must not close a browser runtime owned by another batch. A scenario runtime opened inside this
batch must be closed by its context manager before the cancellation state is finalized.

Timeout is backend-owned and must be checked between scenarios. If timeout happens after some assets were
persisted, the batch status is `partial_success` only when closed evidence proves useful assets; otherwise it
is `timed_out`.

Synchronous v1 cancellation sources are deliberately narrow:

- a controller-level `cancel_checker(batch_id)` hook, used by tests and future API / async callers;
- repository `request_cancel()` calls that happen before the synchronous service reaches a safe boundary.

Current `wagent chat` Ctrl+C and client HTTP timeout are not reliable backend cancel signals for an already
running synchronous request. They must not be documented or tested as product-level backend cancellation in
this child. Until async detach / cancel API exists, the backend lifecycle guarantee is: the synchronous service
returns only after the batch reaches a terminal status, with backend-owned timeout limiting the work.

Detach is allowed only when there is a durable `learning_batch_id` and user-visible status path. This package
does not require async background execution in the first implementation; if async detach is not implemented,
the service must return a closed terminal status instead of pretending the batch can be resumed.

Forbidden:

- backend browser-driving work continues with no batch id;
- `active_task.status=learning` remains after a terminal batch result;
- batch writes `LearnedPath` or `LearnedCapability` after terminal `cancelled`;
- current synchronous `wagent chat` Ctrl+C is claimed to cancel an already-running backend batch;
- user-facing chat reports success without terminal batch status and evidence summary.

## Evidence Contract

Batch summary evidence must include:

- policy version and applied limits;
- planned / attempted / skipped scenario counts;
- run ids created;
- learned capability ids created;
- learned path ids created, if any compatibility path writes remain;
- failed / unverified / unsupported scenario summaries;
- terminal status reason;
- whether cancellation or timeout occurred.

Batch summary must not expose raw DOM, raw selectors, target-specific fixture labels, seed values, or
validation-site-only aliases in user-facing projection.

## Compatibility Contract

- Existing `LearningRunResult` fields may remain for chat compatibility.
- Existing `learned_paths` rows remain readable and replayable.
- 11.3.12.1 `LearnedCapability` rows remain readable; this package may write new rows through its repository
  only when the evidence contract is satisfied.
- Existing `exploration_runs` remain raw attempt history; they may cite `learning_batch_id` in strategy metadata
  but old rows without the field remain valid.
- No direct autonomous-run HTTP endpoints are called by tests or implementation.

## Runtime Hardcoding Prohibition

Runtime code must not hardcode:

- `/users`
- target field labels
- target button text
- fixture data values
- DOM test ids
- validation-site-only aliases
- route-specific prompt text

Target details may appear only in tests, fixtures, docs, and redacted artifacts.

## Implementation Authorization

Implementation requires reviewed `technical-design.md`, current `test-plan.md`, and
`implementation_authorized: yes` in `review.md`.
