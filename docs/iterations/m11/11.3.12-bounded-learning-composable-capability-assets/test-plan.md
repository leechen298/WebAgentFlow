# Test Plan

状态：proposed

## Test Scope

This package requires `test-plan.md` because it affects schema, service boundaries, conversation behavior,
browser lifecycle, evidence semantics, and future runtime composition.

No live autonomous validation is authorized by this documentation package.

## Unit Tests

### LearnedCapability model / repository

- Creates a LearnedCapability with required fields.
- Computes stable `dedup_key`.
- Idempotently ingests duplicate capability evidence.
- Keeps old LearnedPath rows readable.
- Supports trust transitions without affecting LearnedPath trust.

### Capability candidate generation

- Converts text input / search input / select / radio / date / tab / export button into capability candidates.
- Marks unsupported controls with explicit reason.
- Does not silently skip component-library controls.
- Does not include target-specific labels or route constants in runtime code.

### Page Understanding hints

- Produces region hints for filter area, result area, action bar, tab set, modal roots.
- Produces terminal candidates for list refresh, empty result, modal, toast, download, network completion.
- Produces sample value candidates from visible rows/options when available.
- Falls back to synthetic values with lower evidence strength when no sample exists.

### BoundedLearningPlanner

- Generates independent single-capability probes.
- Adds dependency pairs only for recognized dependencies.
- Does not generate all pairwise combinations by default.
- Stops after max scenario count.
- Suppresses repeated attempts for a selector / adapter after configured failure threshold.

### LearningBatchController

- Marks batch `completed` when all planned probes finish.
- Marks `partial_success` when useful capabilities pass but some are skipped / failed.
- Marks `timed_out` when wall-clock budget is reached.
- Marks `cancelled` when user/CLI requests cancellation.
- Closes browser runtime on cancellation.
- Does not leave session `active_task.status=learning` indefinitely.

### CapabilityComposer

- Builds a plan from compatible capabilities and user slots.
- Rejects missing required capabilities.
- Rejects ambiguous same-kind controls without user clarification.
- Prefers existing LearnedPath over composition when confidence is higher.
- Promotes a successful composition into LearnedPath only after evidence gate.

## Integration Tests

- URL-only learning creates a LearningBatch, multiple LearnedCapabilities, and optionally LearnedPaths.
- Failed / unsupported capabilities appear in batch summary but not as successful LearnedCapabilities.
- Empty-result search is accepted as terminal evidence but marked `business_match_observed=false`.
- Status / radio filter failures are kept as failed capability evidence, not hidden.
- Capability composition execution uses source capability ids and writes a composition result.
- Conversation history displays batch status, capability summaries, failed/skipped reasons, and source ids.

## CLI / Conversation Tests

- `wagent chat` learning timeout does not leave an unbounded backend process.
- Ctrl+C or explicit cancel closes or detaches the learning batch with a visible status.
- Learning success feedback lists learned capability categories, not fixed "magic phrases".
- Partial learning feedback lists learned and not-learned capabilities.
- No control words become aliases, match terms, business goals, or learned action names.

## Console Tests

- Learning batch detail shows closed / cancelled / timed_out status.
- LearnedPath detail shows source capability ids when present.
- LearnedCapability list/detail can be deferred, but if implemented it must hide unsafe raw detail in normal view.

## Regression Tests

- Existing M10 LearnedPath replay tests continue to pass.
- Existing M11.1 Task Path Planner candidate ranking continues to work with old LearnedPath rows.
- Existing 11.3.10 capability discovery tests do not regress.
- Existing 11.3.11 terminal / ingest tests continue to pass.
- Runtime does not hardcode `/users`, target field labels, or fixture values.

## Live Validation Boundary

Not run in this docs package:

- `verify-scenario`
- product UI autonomous run
- `wagent chat` live learning
- direct autonomous-run endpoint

Future live validation, if explicitly authorized, must record:

- reset scope;
- command / UI surface;
- session id;
- learning batch id;
- run ids;
- learned capability ids;
- learned path ids;
- pass_gate / terminal / ingest summary;
- cancellation / timeout status;
- raw transcript or stable artifact path.

## Acceptance Gates

Implementation may close only if:

- all relevant unit / integration / CLI tests pass;
- no old LearnedPath compatibility regression is found;
- no unbounded learning batch remains after timeout/cancel tests;
- no runtime hardcoding scan finds target route / label / fixture constants;
- review records commands run and commands not run.
