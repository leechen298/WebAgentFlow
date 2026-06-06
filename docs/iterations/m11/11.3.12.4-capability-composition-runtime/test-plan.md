# Test Plan

状态：proposed

## Test Scope

This package requires `test-plan.md` because it changes runtime composition behavior, LearnedCapability consumption,
replay / execution handoff semantics, and LearnedPath promotion guard rules.

No live autonomous validation is authorized by this child package.

## Unit Tests

### Composition schemas

File: `apps/api/tests/test_capability_composer.py`

Required cases:

- default policy and plan schema serialize public redacted fields;
- public plan rejects raw selector / DOM / Playwright payload fields;
- `ready`, `missing_capability`, `ambiguous`, `unsafe`, `prefer_learned_path`, and `unsupported` statuses are covered;
- execution handoff is separate from public plan.

### Capability composer

File: `apps/api/tests/test_capability_composer.py`

Required cases:

- existing high-confidence LearnedPath match returns `prefer_learned_path`;
- no candidate returns `missing_capability`;
- cross-page or incompatible DOM candidate returns `unsafe`;
- missing required slot returns `missing_capability`;
- two equal candidates without safe tie-break return `ambiguous`;
- compatible control + submit capabilities produce deterministic ordered plan;
- conflicting capabilities for the same control ref are rejected;
- provisional trust is rejected by default and accepted only when policy allows it;
- private execution handoff keeps action schemas while public plan remains redacted;
- promotion guard rejects plan-only evidence, failed evidence, missing terminal evidence, and missing source capability ids;
- promotion guard accepts successful execution evidence with compatible terminal target.

### Repository lookup if added

File: `apps/api/tests/test_learned_capabilities_repo.py`

Required cases:

- page-scope lookup filters by page template and capability kind;
- trust filter preserves existing list behavior;
- existing ingest / trust / redaction tests continue to pass.

## Regression Tests

Run existing scoped regressions:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_composer.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_learned_path_replay.py -v
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v
```

## Static Checks

Run scoped ruff:

```bash
uv run ruff check apps/api/app/schemas/capability_composition.py apps/api/app/services/learning/capability_composer.py apps/api/app/repos/learned_capabilities_repo.py apps/api/tests/test_capability_composer.py apps/api/tests/test_learned_capabilities_repo.py
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
- `wagent chat` live learning or execution against a target site.

Future live validation requires explicit user approval and parent runner inputs.

## Acceptance Gates

Implementation may close only if:

- required unit / integration tests pass;
- scoped ruff passes or unrelated failures are recorded truthfully;
- hardcoding scan is reviewed;
- no unresolved P0 / P1 design, code, evidence, or scope finding remains;
- no live validation is claimed;
- `review.md` records commands run and commands not run.
