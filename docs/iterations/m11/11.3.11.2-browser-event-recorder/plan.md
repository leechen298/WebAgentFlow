# 实施计划（Implementation Plan）

状态：proposed

## 输入

- parent `11.3.11-terminal-state-agent-learning-stop-control`
- child 1 `11.3.11.1-terminal-state-agent-contract-taxonomy`
- this package `intent.md`
- this package `contract.md`
- this package `technical-design.md`
- this package `test-plan.md`
- current `execution_runtime.py`, `autonomous_explorer.py`, `wait_for_change.py`, `learning_run_service.py`

## 文档生成计划

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.11.2-browser-event-recorder/` |
| Package type | `code / mixed` |
| Parent / child route | child 2 of `11.3.11-terminal-state-agent-learning-stop-control` |
| Required docs | seven-document set |
| Source inputs read | parent docs, child 1 docs, product model, roadmap, current runtime files by review |
| Contract / status / evidence changes | Adds browser event timeline and redaction contract |
| Design-review gate | required before runtime implementation |
| Test-plan trigger | required due runtime/evidence/redaction changes |
| Implementation authorization boundary | `review.md` must record `implementation_authorized: yes` before code |
| Stop conditions | missing hook clarity, redaction gap, storage conflict, runtime scope drift, live validation request without approval |
| Handoff / checkpoint | after implementation closeout, route to child 3 terminal hints |

## 文件 / 模块

Allowed implementation files after authorization:

- `apps/api/app/services/execution/browser_event_recorder.py` - focused recorder service.
- `apps/api/app/services/learning/autonomous_explorer.py` - narrow hook to start/stop/snapshot recorder.
- `apps/api/app/services/execution/execution_runtime.py` - only if page/context lifecycle hook belongs there.
- `apps/api/tests/test_browser_event_recorder.py` - unit tests.
- Existing autonomous explorer tests - only targeted metadata integration coverage.

Forbidden by default:

- routers / public API schemas;
- database migrations;
- Console UI / CLI;
- action planner semantics;
- LearnedPath ingest gate;
- Terminal State Agent verdict / prompt;
- live run artifacts.
- creating pending `ExplorationRun` rows before execution solely for event ids.

## 步骤

1. Complete design review and codebase hook inspection.
2. If approved, write unit tests for event conversion/redaction/correlation/status first using fake event emitters.
3. Implement focused recorder service.
4. Add narrow runtime hook and optional metadata serialization.
5. Add integration test for optional timeline metadata if hook implemented.
6. Run required tests/static checks.
7. Update `review.md` with changed files, commands, not-run items and findings.
8. Update parent `CURRENT_STATE.md` only after child 2 closeout.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| design review | `review.md` implementation authorization | no P0/P1, hook and redaction plan clear | missing hook/redaction/storage decision |
| implementation | changed files and focused tests | tests pass, scope contained | runtime drift or redaction failure |
| closeout | final status and parent route | child 2 `PACKAGE_COMPLETE` | unverified evidence or live boundary violation |

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_browser_event_recorder.py -q` | recorder unit tests pass | Yes | exact path may change |
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_autonomous_explorer.py -q` | integration remains compatible | Yes | only if hook implemented |
| `uv run ruff check ...` | lint/import clean | Yes | changed Python files |
| `git diff --check` | whitespace clean | Yes | whole diff |

## 复核清单（Review Checklist）

- [ ] No raw secrets or bodies stored.
- [ ] Recorder failure is non-fatal by default.
- [ ] Timeline is bounded and optionally present.
- [ ] Correlation works with runtime correlation_id / attempt_id / step_index / action_id without requiring pre-created run_id.
- [ ] Existing runs and LearnedPaths remain compatible.
- [ ] No live autonomous validation claimed.
