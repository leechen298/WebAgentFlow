# 技术设计（Technical Design）

状态：PACKAGE_COMPLETE

## 当前状态

Child 4 adds `terminal_state_verdict` to `AutonomousExplorationResult`. `LearningRunService`
persists finished runs and calls `_maybe_ingest_learned_path()`, which already checks `pass_gate.status`
before creating a LearnedPath.

## Proposed Runtime Shape

Expected files if implementation is authorized:

- `apps/api/app/schemas/attempt_evaluation.py`
- `apps/api/app/services/learning/attempt_evaluation.py`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/tests/test_attempt_evaluation.py`
- scoped updates to existing learning run service tests

## Data Flow

```text
final_data
  -> extract pass_gate + terminal_state_verdict + trimmed actions
  -> evaluate_attempt_ingest()
  -> AttemptIngestEvaluation
  -> _maybe_ingest_learned_path() permits or rejects LearnedPath creation
```

## Implementation Rules

- Keep evaluation pure and deterministic.
- Keep `_maybe_ingest_learned_path()` as the integration point.
- Preserve existing pass_gate check as mandatory.
- Reject missing or unverified terminal verdict before action parameterization.
- Record a compact rejection reason in flexible run result payload only if needed and backward compatible.

## Compatibility

- Existing tests that expect pass_gate failure to block ingest must still pass.
- Existing confirmed LearnedPaths remain replayable.
- Old run history without terminal verdict should not crash readers.

## Non-goals

- No DB migration.
- No Console / CLI display.
- No live validation.
- No LLM prompt.
- No change to Supervisor or scorecard.

## Validation Commands

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_attempt_evaluation.py apps/api/tests/test_learning_run_service.py -q
uv run ruff check apps/api/app/schemas/attempt_evaluation.py apps/api/app/services/learning/attempt_evaluation.py apps/api/app/services/learning/learning_run_service.py apps/api/tests/test_attempt_evaluation.py
git diff --check
```
