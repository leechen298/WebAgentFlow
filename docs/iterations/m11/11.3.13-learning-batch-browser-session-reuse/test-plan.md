# Test Plan

状态：proposed

## Scope

This package requires a test plan because it changes browser lifecycle, learning batch runtime ownership,
scenario isolation, cancellation cleanup, and visible-browser product UX.

No live autonomous validation is authorized by this documentation package.

## Unit Tests

### Runtime lifecycle

- Capability discovery with three planned scenarios creates one runtime.
- Runtime `start` / `stop` each happen once for the whole batch.
- Seed analysis and every scenario receive the same runtime instance.
- Runtime closes on normal completion.
- Runtime closes on seed analysis failure.
- Runtime closes on scenario execution exception.
- Runtime closes on persistence exception.

### Scenario reset

- Reset runs before each scenario.
- Reset navigates to the seed target URL without scenario query params.
- Reset failure stops or skips remaining scenarios.
- Reset warnings appear in batch summary.
- Reset does not clear cookies / localStorage by default.
- Strong reset modes are opt-in.

### Evidence isolation

- Each scenario still gets a distinct run id.
- Each scenario gets a distinct browser event correlation id.
- Terminal verdict does not use previous scenario evidence.
- BrowserEventRecorder listeners do not duplicate events across scenarios.

### LearningBatch integration

- Timeout before a scenario closes runtime and batch.
- Cancel requested before a scenario closes runtime and batch.
- Partial success closes runtime and preserves created ids.
- No asset writes occur after cancelled status.

## Integration Tests

- URL-only product learning with multiple bounded scenarios uses one runtime factory call.
- `learning_batch_summary` includes reset count / warnings if implemented.
- Existing 11.3.12 capability ingestion still writes LearnedCapability rows.
- Existing LearnedPath compatibility writes still work.
- Existing spec-backed autonomous run behavior remains unchanged.
- Existing replay behavior remains unchanged.

## CLI / Conversation Tests

- `wagent chat` visible mode still sends `browser_visibility=visible`.
- `wagent chat --headless` still sends headless mode.
- Learning feedback does not expose scenario ids or selectors.
- Timeout / failed batch does not leave session `active_task.status=learning`.

## Hardcoding / Safety Checks

- Scan runtime files for `/users`, validation-site target values, fixture names, DOM test ids, or target labels.
- Confirm tests may contain fixture selectors, but runtime code must not.

## Manual / Live Boundary

Not run in this docs package:

- `wagent chat` live learning
- product UI autonomous run
- `verify-scenario`
- direct autonomous-run endpoint

Future live validation, if explicitly authorized, should record:

- command / UI surface;
- session id;
- learning_batch_id;
- visible/headless setting;
- observed browser window count;
- run ids;
- runtime start / stop counts if exposed;
- final batch status;
- transcript and history path.

## Acceptance Gates

Implementation may close only if:

- scoped lifecycle tests prove one runtime per capability discovery batch;
- cleanup tests prove runtime closes on every terminal path;
- reset failure tests prove no polluted scenario is ingested as success;
- existing 11.3.12 tests still pass in scoped form;
- `git diff --check` passes;
- hardcoding scan is reviewed.
