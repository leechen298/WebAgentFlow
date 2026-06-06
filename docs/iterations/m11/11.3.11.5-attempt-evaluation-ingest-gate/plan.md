# 实施计划（Implementation Plan）

状态：PACKAGE_COMPLETE

## 输入

- Parent package docs
- Child 4 `TerminalStateVerdict`
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/app/services/learning/page_verification.py` pass_gate semantics

## 文件 / 模块

Allowed if implementation is authorized:

- `apps/api/app/schemas/attempt_evaluation.py`
- `apps/api/app/services/learning/attempt_evaluation.py`
- scoped changes in `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/tests/test_attempt_evaluation.py`
- scoped changes in existing learning run service tests

Forbidden:

- DB migration / new persistence table.
- Console / CLI display.
- Supervisor / pass_gate computation changes.
- live validation.
- target-specific route / selector rules.

## 步骤

1. Review docs and authorize or block runtime implementation.
2. Add pure attempt evaluation schema and service tests.
3. Implement deterministic gate.
4. Integrate into `_maybe_ingest_learned_path()`.
5. Add service regression for terminal-unverified no-ingest.
6. Run targeted tests / ruff / diff check.
7. Update review and parent route to child 6.

## Stop Conditions

- Any path allows `terminal_unverified` or `terminal_failed` to create a successful LearnedPath.
- Implementation changes pass_gate/Supervisor semantics.
- Implementation requires DB migration.
- Live validation is requested without required GOAL_RUNNER inputs.

## Checklist

- [x] pass_gate remains mandatory.
- [x] terminal verdict is mandatory for new ingest.
- [x] missing terminal verdict is not success.
- [x] failed / unverified terminal states are blocked.
- [x] existing old read paths remain compatible.
