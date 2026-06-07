# Technical Design

状态：PACKAGE_COMPLETE

## Current Code Path

`ExecutionRuntime` already models one browser -> one context -> one page. It starts in
`ExecutionRuntime.start()` and closes in `ExecutionRuntime.stop()`.

`run_autonomous_exploration()` accepts a caller-managed runtime. It does not create or close the browser.

The repeated visible browser issue comes from `LearningRunService._run_capability_discovery()`:

- seed analysis opens one runtime with `with runtime_factory(config=runtime_config) as runtime`;
- each capability scenario opens another runtime with the same pattern;
- visible `wagent chat` therefore shows one browser per seed/scenario runtime.

## Recommended Design

Add a batch-scoped runtime ownership pattern:

```python
with runtime_factory(config=runtime_config) as runtime:
    seed_analysis = analyze_seed(runtime)
    scenarios = plan_scenarios(seed_analysis)
    for scenario in scenarios:
        reset_result = reset_for_scenario(runtime, request.url, policy)
        if not reset_result.ok:
            mark_remaining_skipped_or_unverified()
            break
        scenario_result = explorer(..., runtime=runtime, ...)
        persist_scenario_result(...)
```

The first implementation can keep this inside `LearningRunService` instead of introducing a new public
runtime abstraction. If the logic grows, extract `LearningBatchBrowserSession`.

## Runtime Reset

Add a small service/helper, for example `learning_batch_browser_session.py` or a private helper in
`learning_run_service.py`:

- `reset_for_scenario(runtime, target_url, mode, baseline=None) -> ScenarioResetResult`
- `capture_baseline(runtime) -> ScenarioBaseline`
- `is_baseline_compatible(before, after) -> bool`

Suggested fields:

- `ok`
- `mode`
- `url`
- `title`
- `warnings`
- `baseline_summary`

Default reset:

1. Navigate to the original target URL.
2. Wait for load and a bounded stabilization period.
3. Close obvious transient UI when generic signals exist.
4. Capture a lightweight baseline.

Do not clear cookies or localStorage by default.

## LearningRunService Changes

Change `_run_capability_discovery()`:

1. Create `LearningBatch` as today.
2. Create one `ExecutionRuntime`.
3. Seed analyze using that runtime.
4. Plan bounded scenarios as today.
5. For each scenario:
   - check `LearningBatchController.boundary_state()`;
   - reset runtime for the scenario;
   - run `explorer(..., runtime=runtime, ...)`;
   - persist run / LearnedCapability / LearnedPath evidence as today;
   - check boundary again.
6. Close batch.
7. Let the runtime context manager close exactly once.

Do not change `_run_single()` for spec-backed or single product-level learning unless tests prove an integration need.

## BrowserEventRecorder Considerations

Because the page/context are reused:

- each `run_autonomous_exploration()` call must attach a fresh recorder;
- recorder stop must remove or neutralize listeners, or repeated attach must be proven safe;
- `browser_events.reset()` after analysis still separates setup navigation from action evidence;
- reset navigation before a scenario must not become terminal evidence for that scenario's action attempt.

If listener cleanup is not guaranteed, add explicit recorder detach tests or add a detach API before runtime reuse.

## Failure Handling

Seed analysis failure:

- close runtime;
- close batch as failed/unverified with stage `seed_analysis`.

Scenario reset failure:

- do not run the scenario;
- mark scenario skipped/unverified;
- close batch as partial/unverified depending on prior useful assets.

Scenario execution failure:

- persist failed scenario evidence when available;
- close runtime in finally;
- close batch according to bounded policy.

Browser/page crash:

- try at most one same-browser page/context replacement if the browser is still usable;
- otherwise close batch and runtime.

Persistence failure:

- close runtime;
- return failed result with error evidence;
- do not leave browser open.

## Conversation / CLI Impact

No CLI flag is required. Existing `--headless` still controls visible/headless mode.

`wagent chat` user-visible behavior should improve without a new command:

- visible mode: one browser window per learning batch;
- headless mode: no visible window;
- learning outcome wording remains governed by 11.3.10 / 11.3.12 contracts.

If progress events are updated, use generic wording such as:

- "正在复用同一个浏览器学习第 2 个能力"
- "正在重置页面状态"

Do not expose scenario ids or selector details to end users.

## Console / History Impact

Conversation history or learning batch detail may show:

- `browser_session_reuse: true`
- `runtime_start_count`
- `runtime_stop_count`
- `scenario_reset_count`
- reset failures / warnings

This is optional for first implementation but useful for debugging.

## Compatibility

Existing tests that expect runtime factory calls per scenario must be updated. The intended new invariant is:

- capability discovery batch calls runtime factory once;
- spec-backed single autonomous run still calls runtime factory once;
- replay remains unchanged.

## Anti-Hardcoding

Runtime implementation must not special-case `/users`, Ant Design-specific text, field labels, button text,
test ids, or validation-site values. Component-library reset behavior must be structural and adapter-based.
