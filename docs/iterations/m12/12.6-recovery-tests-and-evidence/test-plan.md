# 12.6 Recovery Tests and Evidence Test Plan

Status: proposed
Milestone: M12
Type: mixed

## 适用条件

This file is required because 12.6 closes recovery / abort / proposal /
retry-policy / conversation-flow evidence for M12.

## Test Scope

- Unit: required in the later evidence-closure submission for the full M12
  recovery suite.
- Integration: conditional, only if existing conversation integration surfaces
  are intentionally scoped.
- API: N/A by default.
- Console UI: N/A by default.
- E2E: not run / out of scope by default.
- Agent / Reporter / Recovery: required evidence review.
- Codex / AI External Operator: review only unless explicitly scoped.
- Live autonomous run: explicitly excluded by default.

## Required Later Commands

M12 recovery deterministic suite:

```bash
cd apps/api && .venv/bin/python -m pytest \
  tests/test_recovery_classifier.py \
  tests/test_user_abort_handler.py \
  tests/test_recovery_proposal.py \
  tests/test_retry_policy.py \
  tests/test_recovery_conversation_flow.py \
  tests/test_recovery_exports.py \
  -q
```

Recovery ruff check:

```bash
cd apps/api && .venv/bin/ruff check \
  app/schemas/recovery.py \
  app/services/recovery \
  tests/test_recovery_classifier.py \
  tests/test_user_abort_handler.py \
  tests/test_recovery_proposal.py \
  tests/test_retry_policy.py \
  tests/test_recovery_conversation_flow.py \
  tests/test_recovery_exports.py
```

Static diff check:

```bash
git diff --check
```

## Test Matrix

| Layer | Scenario | Evidence | Required later? |
|---|---|---|---|
| Unit | M12 recovery deterministic suite pass | pytest result summary | Yes |
| Unit | M12 recovery exports pass | included in recovery suite | Yes |
| Unit/static | forbidden dependency scan pass | focused tests and ruff | Yes |
| Unit/static | no execution fields pass | focused tests | Yes |
| Unit/static | `non_executable` boundaries pass | focused tests | Yes |
| Unit/static | event payload not executed pass | focused tests | Yes |
| Static | no API / CLI / DB / frontend changes in evidence pass | git status / diff review | Yes |
| Evidence | E2E / UI smoke / `verify-scenario` / autonomous run not-run table | review table | Yes |

## Boundary Coverage Requirements

The later evidence report must explicitly cover:

- 12.1 classifier states and recommendations;
- 12.2 abort stop boundary and inflight caveat;
- 12.3 proposal non-execution and no selected option;
- 12.4 retry policy non-execution and denial behavior;
- 12.5 conversation response / event payload non-execution markers.

## Not Run Defaults

The following are not run by default and must be recorded as `not run /
unverified`, not pass:

- API tests;
- CLI tests;
- Console UI smoke;
- E2E;
- `verify-scenario`;
- autonomous run;
- product-driven browser execution;
- live retry / replan / takeover / teaching execution.

## Acceptance Criteria for Evidence Closure

- Required recovery suite command exits 0.
- Required ruff command exits 0.
- `git diff --check` is clean.
- Not-run table is complete and does not present unrun items as pass.
- No blocker / P1 / P2 findings remain for M12 boundaries.
- Completion decision follows `contract.md`.

This design package does not execute the required later commands.
