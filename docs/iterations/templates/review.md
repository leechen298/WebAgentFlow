# Review

Status: in_progress

## <YYYY-MM-DD HH:MM> Design Review

- Reviewer:
- Decision: approved | changes_requested | rejected
- Notes:

## <YYYY-MM-DD HH:MM> Code Review

- Reviewer:
- Decision: approved | changes_requested | rejected
- Notes:

## User Feedback

- <Feedback> -> accepted | rejected, reason: <reason>

## Final Delta

### What Shipped

- <Actual delivered change.>

### Deviations From Intent / Contract / Technical Design / Plan

- <Deviation and reason, or `None`.>

### WebAgentFlow Live Run Boundary

Unless the user explicitly requests a live run, do not trigger
`verify-scenario`, autonomous runs, or product-driven browser execution.

If a live run is explicitly requested, record:

- invocation surface;
- run_id;
- pass_gate.status;
- supervisor verdict;
- scorecard;
- whether the run was product-initiated UI traffic or skill invocation.

### Validation Evidence

| Command | Expected | Actual result | Exit code | Pass / Fail / Skip | Notes |
|---|---|---|---|---|---|
| `<command>` | `<expected>` | `<actual>` | `<0/1/...>` | `<counts>` | `<reason if failed/not run>` |

### Follow-ups

- <Follow-up owner / iteration, or `None`.>
