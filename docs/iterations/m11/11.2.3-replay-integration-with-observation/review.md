# Review

Status: implementation complete

## Implementation summary

11.2.3 replay observation aggregation implemented.

### Files modified

- `apps/api/app/schemas/learned_path_replay.py` — added `ReplayObservationStatus`,
  `StepObservationRef`, `ReplayObservationSummary`; added optional
  `observation_summary` field to `ReplayResult`.
- `apps/api/app/services/learning/learned_path_replay.py` — integrated
  `build_replay_observation_summary()` into `run_replay()` for action execution
  and observational paths; blocked/drifted/runtime_error paths remain `None`.
- `apps/api/tests/test_learned_path_replay.py` — added 6 integration tests for
  observation summary in replay context.

### Files created

- `apps/api/app/services/learning/replay_observation.py` — aggregation service
  with `build_replay_observation_summary()`.
- `apps/api/tests/test_replay_observation_summary.py` — 27 unit tests covering
  schema, aggregation, and boundary invariants.

## Validation evidence

### Scoped tests

Command:
```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_replay_observation_summary.py tests/test_learned_path_replay.py -v
```

Expected: all tests pass.
Actual: **55 passed** in 8.28s.
Exit code: 0.

### Ruff lint

Command:
```bash
cd apps/api && ../../.venv/bin/ruff check app/schemas/learned_path_replay.py app/services/learning/replay_observation.py app/services/learning/learned_path_replay.py tests/test_replay_observation_summary.py tests/test_learned_path_replay.py
```

Expected: no errors.
Actual: **All checks passed!**
Exit code: 0.

### Whitespace check

Command:
```bash
git diff --check
```

Expected: no output.
Actual: clean.
Exit code: 0.

### Full API suite

Command:
```bash
cd apps/api && ../../.venv/bin/python -m pytest -q
```

Expected: all tests pass (sandbox Playwright skips allowed).
Actual: **1167 passed, 65 skipped** in 32.90s.
Exit code: 0.

### Forbidden directory check

Command:
```bash
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Expected: no output.
Actual: no output.
Exit code: 0.

## Contract alignment

| Contract requirement | Status |
|---|---|
| Replay Observation Evidence is replay-level aggregation | Implemented: `build_replay_observation_summary()` aggregates from steps. |
| WaitResult is step-level outcome (read-only) | Only reads `step.wait_result`, does not modify. |
| ObservationSignal is evidence atom | Aggregates signal kinds and refs from `wait_result.observed_signals`. |
| `has_primary_observation` != business success | Summary sets boolean + status only; does not change `ReplayResult.status`. |
| `has_timeout` != retry | Timeout enters counts/flags/notes only; no retry/recovery. |
| `has_only_supporting_observation` conservative | Only true when no primary + at least one supporting signal. |
| Does not modify `ReplayResult.status` semantics | `observation_summary` is optional supplement, not part of status derivation. |
| Does not call Task Result Reporter | Verified by import boundary test. |
| Does not store raw HTML/DOM dump | Summary/ref schemas have no raw payload fields. |
| Blocked/drifted returns `observation_summary=None` | Verified by integration test. |
| Observational path `actions=[]` returns `not_applicable` | Verified by integration test. |

## Not run

| Item | Reason | Risk |
|---|---|---|
| E2E | Aggregation covered by API/service tests; no UI changes. | Cannot prove Console UI displays summary. |
| Live UI smoke | No UI changes; no external test operator required. | Cannot prove browser path visualization. |
| `verify-scenario` | No autonomous run triggered. | No live supervisor evidence. |
| Task Result Reporter tests | 11.2.5 only. | Cannot prove reporter consumes summary. |
| M12 recovery tests | M12 only. | Cannot prove failure dialogue. |
