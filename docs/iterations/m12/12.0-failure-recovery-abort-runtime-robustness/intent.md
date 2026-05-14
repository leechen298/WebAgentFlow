# 12.0 Failure Recovery / Abort / Runtime Robustness Intent

Status: documentation initialized.

## Goal

Initialize the M12 documentation boundary for handling failed, blocked,
uncertain, needs-review, and user-aborted runtime outcomes.

## Motivation

M11.1 closed the task-to-path MVP with conservative reporting: replay
completion is not task success, blocked execution is explicit, failed replay is
not repaired automatically, and uncertain results require review. M12 exists
to define the next product layer after those outcomes: safe recovery proposal,
abort handling, retry policy, user clarification, and evidence preservation.

Without this boundary, WebAgentFlow could drift into hidden recovery or hidden
relearning, which would make runtime behavior harder to inspect and less safe
for the operator.

## Boundary

- Do not implement code.
- Do not run API / CLI / E2E / `verify-scenario` tests.
- Do not create `12.1-*` or later detail directories.
- Do not modify `docs/iterations/m11/` history documents except through
  roadmap / milestone index status references outside that tree.
- Do not design M11.2 Runtime Observation / Wait-for-change.
- Do not introduce autonomous recovery, hidden relearning, teaching mode, slot
  binding, account systems, remote triggers, WeChat, or Feishu integration.

## Success Criteria

- The M12 and 12.0 document skeleton exists.
- The docs explicitly answer what counts as `failure`, `blocked`,
  `uncertain`, and `needs_review`.
- The docs define when to retry, stop, ask user, or suggest re-teach / update
  LearnedPath.
- The docs state that recovery proposals require user confirmation and that
  recovery is not automatic by default.
- The docs describe user abort handling and evidence retention.
- The docs forbid hidden recovery, hidden relearning, and continuing browser
  operation without user consent.
