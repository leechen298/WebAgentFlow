# 技术设计（Technical Design）

状态：PACKAGE_COMPLETE

## 当前状态（Current State）

Child 2 adds redacted browser event timeline. Child 3 adds deterministic page terminal hints. The autonomous
result does not yet include a terminal-state verdict.

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| advisory verdict only | independent service returns metadata | unit tests | child 5 owns ingest |
| missing evidence not false success | default unverified/continue | unit tests | safety first |
| no target-specific rules | event/hint type matching only | boundary tests | no labels/routes |
| no browser operation | pure function/classifier | unit tests | no Playwright |

## 实现方案（Proposed Implementation）

Expected files:

- `apps/api/app/schemas/terminal_state.py`
- `apps/api/app/services/learning/terminal_state.py`
- optional additive `terminal_state_verdict` on `AutonomousExplorationResult`
- optional autonomous explorer wiring after final_state capture
- `apps/api/tests/test_terminal_state.py`

## 数据流（Data Flow）

```text
browser_event_timeline + page_terminal_hints + final_state
  -> classify_terminal_state()
  -> TerminalStateVerdict
  -> result metadata
  -> child 5 Attempt Evaluation / ingest gate
```

## 状态推导（Status / State Derivation）

Rules:

- download event -> `download_started`, strong, `stop`.
- dialog/popup event -> `modal_or_popup_opened` or `browser_dialog`, strong, `stop`.
- framenavigated/load + navigation hint -> `navigation`, strong/medium, `stop`.
- request/response + list_refresh hint -> `list_refresh` or `network_completion`, medium/strong, `stop`.
- request without response/load/failure -> `network_completion`, weak, `wait` while bounded wait remains.
- request without response/load/failure + `max_wait_reached` -> `network_completion`, weak, `unverified_stop`.
- console/pageerror/requestfailed -> `terminal_failed`, medium/strong, `unverified_stop`.
- no events/hints -> `terminal_unverified`, none, `continue`.
- recorder unavailable -> `terminal_unverified`, none, `unverified_stop`.

The implementation segments out setup/navigation evidence before action execution and requires positive
terminal browser evidence to carry action scope (`action_id`, `step_index`, or `action_type`). Unscoped async
events after reset are retained as unverified evidence, not `terminal_detected`. It then records
`needs_more_wait` and `max_wait_reached` as post-action advisory metadata. It does not mutate the autonomous
execution loop timing. Later packages may wire this recommendation into real bounded waiting / early stop after
a reviewed contract update.

## 非目标（Non-goals）

- No live run.
- No LLM prompt.
- No actual wait-loop mutation beyond metadata wiring.
- No pass gate, Supervisor, LearnedPath ingest, DB migration, Console UI, CDP, DOM diff engine, or LLM-provider
  integration.

## 测试矩阵入口（Test Matrix）

See `test-plan.md`.

## 验证命令入口（Validation Commands）

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_terminal_state.py apps/api/tests/test_terminal_hints.py apps/api/tests/test_browser_event_recorder.py -q
uv run ruff check apps/api/app/schemas/terminal_state.py apps/api/app/services/learning/terminal_state.py apps/api/tests/test_terminal_state.py
git diff --check
```
