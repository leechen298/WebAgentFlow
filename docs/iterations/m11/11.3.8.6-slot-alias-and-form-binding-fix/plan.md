# 实施计划（Plan）

状态：PACKAGE_COMPLETE

## Steps

1. Record `11.3.8.5` live failure evidence and route to this repair package.
2. Run read-only design / safety review.
3. Add RED tests for action planner field-signal matching and chat slot alias
   handoff.
4. Implement target-agnostic field-signal matching in `action_planner.py`.
5. Implement target-agnostic slot alias resolution in `chat_runtime.py`.
6. Run focused tests, Ruff, forbidden target scan, and patch sanity.
7. Clean DB per the current-thread approval and rerun approved external
   validation through `wagent chat` with API base URL
   `http://127.0.0.1:8001`, target URL `http://127.0.0.1:5177/inventory`,
   approved scenario list `all`, and latest-result-doc update approval `yes`.
8. Update dated/latest reports and parent closeout according to evidence.

## Stop Conditions

- Any direct autonomous-run endpoint usage.
- Target-specific runtime/prompt constants.
- Subagent P0 / P1 findings not resolved.
- Live rerun unavailable or evidence incomplete.
