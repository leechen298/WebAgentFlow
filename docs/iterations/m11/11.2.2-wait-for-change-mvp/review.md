# Review

Status: completed

## 11.2.2 Wait-for-change MVP — Implementation Review

### What was implemented

11.2.2 Wait-for-change MVP minimal implementation completed.

- Replay steps can carry `wait_result`.
- Only minimal post-action wait signals are supported.

### Schema changes

Added to `apps/api/app/schemas/learned_path_replay.py`:

- `ObservationSignal` — a single post-action observation signal.
- `WaitResult` — outcome of a post-action wait window.
- `ObservationSignalKind` — `Literal["url_changed", "title_changed", "page_load_finished", "network_idle_observed"]`.
- `WaitStatus` — `Literal["observed", "timeout", "skipped", "not_required"]`.
- `ReplayStepLog.wait_result: WaitResult | None = None` — backward-compatible extension.

### Wait service

New file `apps/api/app/services/learning/wait_for_change.py`:

- `wait_for_change_after_action(page, action, step_log, timeout_ms, wait_strategy)` returns `WaitResult`.
- Action policy: `click` -> short_stability_wait, `fill`/`press` -> skipped, `observe` -> not_required, failed action -> skipped.
- Budget splitting: `timeout_ms` is the total budget. Stability wait uses a bounded fraction (`min(300, timeout_ms // 2)`), network idle uses the remaining positive budget. Default `timeout_ms=1000` → 300ms stability + 700ms network idle.
- `page_load_finished` is **not** emitted in MVP — URL/title change alone does not prove browser-level document load completion. Schema kind retained for future use.
- `network_idle_observed` is emitted as a supporting signal only when the network-idle probe succeeds within the remaining budget. It can never be `primary_signal`.
- When `remaining_ms <= 0`, the network-idle probe is skipped entirely (Playwright treats `timeout=0` as "disable timeout", which would hang).
- Exception-safe: internal failures return conservative `skipped`/`timeout`.

### Replay integration

Updated `apps/api/app/services/learning/learned_path_replay.py`:

- After `execute_action`, calls `wait_for_change_after_action` and stores result in `log["wait_result"]`.
- Defensive wrapper catches unexpected wait service exceptions and constructs a conservative `WaitResult(status="skipped", notes="wait failed: ...")` so replay status is unaffected and the wait outcome is preserved.
- `_step_log_to_replay_step` passes through `wait_result`.

### Tests

- `apps/api/tests/test_wait_for_change.py` — 25 tests covering schema validation, action policy, signal detection, primary vs supporting signals, budget splitting (stability fraction, network idle remaining budget, budget sums to total), non-string page state hardening, exception policy, no-raw-HTML invariant.
- `apps/api/tests/test_learned_path_replay.py` — 5 new tests for wait integration (fill carries skipped result, click triggers wait, observe returns not_required, failed action doesn't misreport, wait exception produces conservative result without changing replay status). All 22 existing tests continue passing.

### Supported signals (MVP)

- `url_changed` (primary)
- `title_changed` (primary)
- `network_idle_observed` (supporting only — uses remaining budget after stability wait)

Not emitted in MVP (schema kinds retained for future use):

- `page_load_finished` — requires action-related load evidence that the current wait service cannot reliably detect.

### Follow-up hardening

After implementation review, the wait service was hardened so mock or corrupted
page state cannot create false `url_changed` / `title_changed` signals:

- `_read_page_state` accepts only string URL / title values; non-string values are treated as unknown.
- The exception-policy test now simulates an explicit state-read failure instead of relying on `MagicMock` URL / title behavior.
- 11.2.2 contract / plan docs now state that `page_load_finished` is retained in schema but not emitted by the current MVP.

### What is NOT implemented

- No Agent business judgment.
- No Task Result Reporter integration.
- No Page Understanding Agent.
- No recovery / retry / abort.
- No Page Context Bridge.
- No raw HTML persistence.
- No M12 / M14 / 11.3 directories created.

### Validation

- `git diff --check`: PASS
- Scoped wait/replay tests: 47/47 PASS
- `ruff`: PASS
- Full API suite in Codex sandbox: 1105 passed, 65 skipped, 29 failed due Playwright Chromium launch permission (`MachPortRendezvousServer` permission denied). Rerun outside the sandbox before final release evidence.
- M12/M14/11.3 directory check: PASS (none found)
