# 契约（Contract）

状态：PACKAGE_COMPLETE

## Operator Evidence Contract

Run detail may show:

- `terminal_state_verdict.terminal_outcome`
- `terminal_state_verdict.stop_decision`
- `terminal_state_verdict.terminal_type`
- `terminal_state_verdict.evidence_strength`
- `attempt_ingest_evaluation.ingest_status`
- `attempt_ingest_evaluation.failure_category`

Run detail must not show:

- raw request / response bodies;
- secrets;
- unredacted selectors beyond existing raw JSON payload;
- any invented pass/fail status beyond persisted evidence fields.

## Compatibility

- Legacy result snapshots without terminal metadata hide the evidence summary.
- Existing run detail payload remains backward compatible.
- `pass_gate_status` stays the authoritative run outcome.

## Live Boundary

No live run, `verify-scenario`, UI smoke that triggers autonomous run, or direct autonomous endpoint calls.
