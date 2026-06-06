# Technical Design

## Current State

当前 product-level URL-only learning 通过 `LearningRunService` 调用 autonomous explorer。
当请求没有 `spec_id`、`scenario` 和 `fill_values` 时，runtime 只能拿到泛化 goal。
筛选页上的可填写控件没有被提升为 capability inventory，也没有被拆成 scenario matrix。

结果是 action planner 很容易选择页面上最明显的 submit/search button，生成一个 click-only path。
这就是用户看到“学会了开始操作 / 帮我开始”的上游原因之一。

## Design Goals

- 在 URL-only learning 中新增 target-agnostic `PageCapabilityDiscovery`。
- 从 PageAnalysis 构建 filter inventory。
- 用通用 adapter 判断控件是否支持。
- 生成 single / pairwise / all-supported smoke scenario matrix。
- 每个 scenario 独立执行并持久化 run history。
- 只把通过 evidence gate 的 scenario ingest 为 LearnedPath。
- 让 child 2 可以读取 aggregate outcome 和 capability summaries。

## High-level Flow

```text
URL-only learning request
  -> PageAnalysis
  -> PageCapabilityDiscovery
  -> FilterCapability inventory
  -> CapabilityScenario matrix
  -> run scenario one by one
  -> persist ExplorationRun per scenario
  -> evidence gate
  -> ingest passed scenarios into LearnedPath
  -> aggregate discovery result
```

Spec-backed request flow remains unchanged:

```text
spec_id + scenario
  -> existing spec scenario runner
  -> existing pass gate
```

## Service Boundary

Add a new learning service module or sub-service, for example:

- `apps/api/app/services/learning/capability_discovery.py`

The service should avoid direct router dependencies. It can be used by
`learning_run_service.py` and tested without live browser execution when fed synthetic PageAnalysis input.

Candidate public functions:

- `build_filter_inventory(page_analysis, page_context) -> PageCapabilityInventory`
- `generate_filter_scenarios(inventory, options) -> list[CapabilityScenario]`
- `summarize_discovery_result(runs, learned_paths, failures) -> LearningCapabilityDiscoveryResult`

## Filter Inventory

Inventory construction should inspect PageAnalysis element records and structural relations:

- visible inputs and controls
- label / placeholder / aria-label / nearby text
- form grouping and toolbar grouping
- submit/search button relation
- result container candidate
- component runtime hints such as role, aria-expanded, popup relation, class hints where safe

Inventory must keep both supported and unsupported capabilities. Unsupported controls are important
for honest partial success and future adapter work.

## Adapter Scope

Supported generic control adapters for this package:

- text input
- search input
- radio
- segmented status
- select
- combobox
- cascader
- date picker
- range date picker
- month picker
- submit/search button

Adapter responsibilities:

- determine whether a control can be filled or selected target-agnostically
- generate an action binding with a stable selector strategy
- provide or request a safe generic test value
- bind the control to a submit/search action
- record unsupported reasons without dropping the capability

Adapters must not contain `/users` route logic or fixture-specific labels.

## Scenario Generation

Given supported filter capabilities:

1. Generate one `single_filter` scenario for each supported capability.
2. Generate pairwise combinations for supported capabilities.
3. Generate one `all_supported_filters_smoke` scenario.

Each scenario must include:

- stable `scenario_id`
- stable `capability_id`
- `scenario_kind`
- human label
- input bindings
- expected observation target
- source capability ids
- discovery batch id

Stable ids should be derived from page signature plus normalized capability references, not from volatile DOM order alone.

## Expected Observation Target

The first implementation may use conservative observation targets:

- result list/table/container changed
- query parameters changed
- network idle after submit
- visible applied filter tag/value changed
- empty state or result count changed

The target should be recorded per scenario. If only supporting evidence exists,
the scenario must remain unverified and must not be ingested into LearnedPath.

## Autonomous Run History

Each scenario must create an independent autonomous run history row.

`strategy_json` should include:

- `kind: "filter_capability_discovery"`
- `discovery_batch_id`
- `scenario_kind`
- `scenario_id`
- `capability_id`
- `capability_label`
- `bound_controls`
- `source_capability_ids`
- `expected_observation_target`
- `product_level: true`

The source run detail must allow the Console history page to answer:

- this run belongs to which discovery batch
- which capability was attempted
- which controls were bound
- why it passed, failed, or stayed unverified
- whether a LearnedPath was created

## LearnedPath Ingest

Passed scenario ingestion should produce LearnedPath metadata with concrete capability identity:

- `kind: "filter_capability"`
- `capability_id`
- `scenario_kind`
- `capability_label`
- `bound_controls`
- `input_bindings`
- `source_run_id`
- `discovery_batch_id`

Actions must correspond to concrete operations:

- fill/select filter control
- submit/search
- observe target

Do not ingest actions that are only:

- observe-only
- single generic click with no bound filter
- click-only search button with no input semantics

## Aggregate Result

`LearningRunResult` may be extended, or a new aggregate DTO may be introduced,
but child 2 must be able to consume:

- capability summaries
- passed learned path ids
- failed scenario summaries
- unverified scenario summaries
- unsupported capability summaries
- discovery batch id

This package does not finalize user-facing copy; it only provides structured data for child 2.

## Impact Boundary

Expected affected modules:

- `apps/api/app/services/learning/autonomous_explorer.py`
- `apps/api/app/services/learning/action_planner.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/routers/exploration.py`
- `apps/api/app/models/learned_path.py` only if existing JSON metadata is insufficient
- `apps/api/app/repos/learned_paths_repo.py`
- relevant learning schemas / tests

Router changes should remain thin. Business logic belongs in services.

## Compatibility

- Old LearnedPath and ExplorationRun rows must remain readable.
- Old single-scenario learning requests must still work.
- Spec-backed verification must not be routed through discovery unless explicitly requested.
- Existing `wagent chat` explicit learning with a real user goal must retain its identity metadata.

## Failure Handling

If PageAnalysis cannot identify any supported filter controls:

- persist a discovery result with zero supported capabilities
- preserve unsupported evidence when available
- do not claim success
- do not create LearnedPath

If some scenarios pass and some fail:

- ingest only passed scenarios
- keep failed run evidence
- expose partial outcome data for child 2

If evidence is insufficient:

- mark scenario unverified
- keep run history
- do not ingest LearnedPath

## Non-goals

- No live autonomous validation in this docs package.
- No direct autonomous-run endpoint calls from coding agents.
- No `wagent chat` final feedback copy changes in child 1.
- No fixture-specific runtime branch.
