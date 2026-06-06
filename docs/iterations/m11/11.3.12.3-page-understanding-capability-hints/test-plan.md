# Test Plan

状态：proposed

## Test Scope

This package requires `test-plan.md` because it changes PageAnalysis schema, PageAnalyzer output, capability
discovery planning input, and bounded-learning scenario selection.

No live autonomous validation is authorized by this child package.

## Unit Tests

### Capability hints

File: `apps/api/tests/test_capability_hints.py`

Required cases:

- empty / minimal PageAnalysis returns `CapabilityHintSet` with version and safe defaults;
- fillable search controls produce `control_input` hints;
- submit controls produce `submit_search` terminal-action hints;
- select / toggle controls produce correct capability kinds;
- unsupported / ambiguous controls preserve warnings instead of pretending support;
- dependency groups are emitted only for structural range / cascader / tab / modal evidence;
- normal projections do not expose raw selectors, raw DOM, target labels, or seed values.
- public `region_ref`, `control_ref`, and `terminal_target_ref` are stable redacted ids, not CSS selectors, XPath,
  accessible labels, test ids, option values, or raw DOM paths.
- sample value sources accept only:
  `generated_by_type`, `static_safe_default`, `empty_safe_probe`, `existing_option_value_redacted`, and
  `operator_supplied`.
- `existing_option_value_redacted` records only redacted evidence in serialized hints.

### Capability discovery integration

File: `apps/api/tests/test_filter_capability_discovery.py`

Required cases:

- discovery uses hints when present;
- discovery falls back to current PageAnalysis fields when hints are absent;
- discovery can generate executable scenarios from redacted hint refs by resolving them through runtime-private
  bindings or the original `DiscoveredElement` inventory.
- discovery skips / marks unsupported a hinted capability when its private binding is missing, without serializing a
  selector into the public hint as a fallback.
- serialized hints remain redacted even when generated scenarios keep executable selectors internally.
- default bounded policy does not plan dependency pairs without explicit dependency hints and policy opt-in;
- dependency-pair scenarios appear only when both hint and policy allow them.

## Regression Tests

Run existing scoped regressions:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_page_analyzer_selector.py tests/test_filter_capability_discovery.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_bounded_learning_batch_lifecycle.py -v
```

## Static Checks

Run scoped ruff:

```bash
uv run ruff check apps/api/app/schemas/capability_hints.py apps/api/app/schemas/page_analysis.py apps/api/app/services/learning/capability_hints.py apps/api/app/services/learning/page_analyzer.py apps/api/app/services/learning/capability_discovery.py apps/api/tests/test_capability_hints.py apps/api/tests/test_filter_capability_discovery.py apps/api/tests/test_learning_run_service.py
```

Run hardcoding scan:

```bash
rg -n '(/users|Alice|Bob|data-testid|validation-site|启用用户|邮箱查用户)' apps/api/app
```

Expected: no new runtime target hardcoding. Existing generic `data-testid` collection/redaction hits must be
explained if present.

## E2E / UI Smoke Boundary

No E2E / UI smoke is authorized in this child package.

## Live Validation Boundary

Not authorized:

- `verify-scenario`;
- product UI autonomous run;
- direct `/exploration/autonomous-runs` calls;
- `wagent chat` live learning against a target site.

Future live validation requires explicit user approval and parent runner inputs.

## Acceptance Gates

Implementation may close only if:

- required unit / integration tests pass;
- scoped ruff passes or unrelated failures are recorded truthfully;
- hardcoding scan is reviewed;
- existing PageAnalysis / learning service regressions pass;
- no unresolved P0 / P1 design, code, evidence, or scope finding remains;
- `review.md` records commands run and commands not run.
