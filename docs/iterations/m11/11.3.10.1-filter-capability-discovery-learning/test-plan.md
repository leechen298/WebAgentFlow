# Test Plan

## Test Boundary

This package requires repo-local automated tests for capability discovery,
scenario generation, metadata persistence, and LearnedPath ingest gating.

Live autonomous browser execution is not part of the default test plan. It may run only after the
user explicitly authorizes a live validation entry and provides the required target details.

## Unit Tests

### PageAnalysis to Filter Inventory

Required coverage:

- text input recognized as supported filter capability
- search input recognized as supported filter capability
- radio / segmented status recognized as supported filter capability
- select / combobox recognized as supported filter capability
- cascader recognized or recorded as unsupported with reason when adapter cannot bind it
- date picker / range date / month picker recognized or recorded with adapter support status
- submit/search button relation resolved
- unsupported controls remain in inventory evidence instead of being silently dropped

Expected proof:

- deterministic capability ids
- human labels derived from target-agnostic page evidence
- no route-specific labels hardcoded in runtime test subject

### Filter Inventory to Scenario Matrix

Required coverage:

- one `single_filter` scenario per supported capability
- pairwise matrix for supported capabilities
- exactly one `all_supported_filters_smoke` scenario
- no exponential full permutation generation
- zero supported capabilities produces zero executable scenarios plus unsupported summary
- stable scenario ids across repeated equivalent PageAnalysis input

### Control Adapter Action Binding

Required coverage:

- text/search binding produces fill action
- radio/segmented binding produces select/click action with value evidence
- select/combobox binding can open runtime option panel and choose a safe candidate in planned action form
- cascader binding either produces staged selection actions or explicit unsupported reason
- date/range/month binding produces planned date value actions or unsupported reason
- submit/search button binding attaches to each scenario

## Integration Tests Without Live Browser

Required coverage:

- synthetic PageAnalysis input generates a discovery batch and scenario matrix
- scenario metadata can be persisted as ExplorationRun strategy JSON without live execution
- failed scenario summaries remain queryable
- passed scenario summaries can be converted into LearnedPath ingest input
- unverified scenarios are not ingested

## API / Service Tests

Required coverage:

- URL-only learning request invokes capability discovery when no spec/scenario is present
- spec-backed request bypasses capability discovery and keeps existing behavior
- multiple scenario run metadata share one discovery batch id
- passed scenarios generate LearnedPath ids
- failed/unverified scenarios do not enter LearnedPath catalog
- aggregate result exposes capability summaries for child 2

## Regression Tests

Required regression:

- URL-only `/users`-style filter page no longer produces only one LearnedPath whose actions are
  a generic `#btn-search` click plus observe.

The regression fixture may use `/users` naming in test or fixture code, but product runtime must stay target-agnostic.

## Live Autonomous Run

Default status: `not run`.

Live run may be authorized only by an explicit later user request. If authorized, evidence must include:

- approved surface
- command or UI operation
- target URL
- discovery batch id
- run ids
- pass gate status per scenario
- learned path ids for passed scenarios
- failed/unverified evidence

Direct calls to `/exploration/autonomous-runs` from curl, fetch, httpx, or one-off scripts remain prohibited.
