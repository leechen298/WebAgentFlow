# 11.1.5 Regression Verification Report

Date: 2026-05-12
Commit: `df85aba7d1d0ad4c385dbaf7c9c8d6cd105f13ea`
Working tree before report: clean

## Scope

This run verifies 11.1.5 Plan Confirmation and Consent Gate after
`df85aba7d1d0ad4c385dbaf7c9c8d6cd105f13ea`
(`fix(11.1.5): route slash decisions through confirmation gate`).

This is a regression verification report. It did not add E2E cases, did not run
Agent-operated UI exploratory, and did not trigger live autonomous exploration.

## Commands And Results

| Area | Command | Result |
|---|---|---|
| Commit | `git rev-parse HEAD` | PASS — `df85aba7d1d0ad4c385dbaf7c9c8d6cd105f13ea` |
| Working tree | `git status --short` | PASS — clean before report creation |
| API targeted | `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_confirmation.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py -q` | PASS — `113 passed in 0.58s` |
| Conversation replay hook | `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_replay_hook.py -q` | PASS — `18 passed in 0.11s` |
| Task planning preview | `cd apps/api && ../../.venv/bin/pytest tests/test_task_planning_preview.py -q` | PASS — `9 passed in 0.03s` |
| Alembic heads | `cd apps/api && ../../.venv/bin/alembic heads` | PASS — single head: `df9ed1494afd (head)` |
| CLI conversation | `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -q` | PASS — `15 passed in 0.06s` |
| Deterministic E2E, sandbox | `pnpm run test:e2e` | BLOCKED — exit 1 due sandbox-localhost and Chromium permissions: `connect EPERM 127.0.0.1:8001`; `bootstrap_check_in ... Permission denied` |
| Deterministic E2E, non-sandbox rerun | `pnpm run test:e2e` | PASS — `19 passed (14.0s)` |
| git diff --check | `git diff --check` | PASS — clean |

## 11.1.5 Behaviors Covered

- `/confirm` routes through confirmation gate: yes. Covered by
  `test_classify_confirm_keywords`, `test_process_confirm_result`,
  `test_confirm_from_awaiting_confirmation_moves_to_plan_confirmed`, and
  `test_slash_confirmation_commands_use_confirmation_gate`.
- `/cancel` routes through confirmation gate: yes. Covered by
  `test_classify_cancel_keywords`, `test_process_cancel_result`,
  `test_cancel_from_awaiting_confirmation_returns_to_task_intake`, and
  `test_slash_confirmation_commands_use_confirmation_gate`.
- `/abort` routes through confirmation gate: yes. Covered by
  `test_classify_cancel_keywords` and
  `test_slash_confirmation_commands_use_confirmation_gate`.
- `/stop` routes through confirmation gate: yes. Covered by
  `test_classify_cancel_keywords` and
  `test_slash_confirmation_commands_use_confirmation_gate`.
- `/reject` routes through confirmation gate: yes. Covered by
  `test_classify_reject_keywords`, `test_process_reject_result`,
  `test_reject_from_awaiting_confirmation_returns_to_task_intake`, and
  `test_slash_confirmation_commands_use_confirmation_gate`.
- `/replay` while awaiting confirmation is blocked: yes. Covered by
  `test_replay_blocked_while_awaiting_confirmation` in orchestrator and API
  tests.
- Replay handler not called by confirmation input: yes. Confirmation service
  boundary test asserts no replay/autonomous/LLM imports, and confirmation gate
  tests keep confirmation decisions in the consent gate instead of replay
  execution.
- Confirmation events include `replay_executed: false`: yes. Covered by
  `test_confirm_from_awaiting_confirmation_moves_to_plan_confirmed`,
  `test_slash_confirmation_commands_use_confirmation_gate`,
  `test_confirmation_gate_records_no_replay_executed`, and API dispatch
  confirmation tests.

## Boundaries

- New E2E added: no
- Agent-operated UI run: no
- Live autonomous run triggered: no
- `/exploration/autonomous-runs` called: no
- `/exploration/autonomous-runs/stream` called: no
- Product-side LLM provider triggered: no
- Product code modified: no
- E2E spec modified: no
- 11.1.6 touched: no
- Execution via replay implemented: no
- Note: an untracked `docs/iterations/m11/11.1.6-execution-via-replay/`
  directory was present after this verification run was complete. It was not
  created, edited, or used by this 11.1.5 regression verification.

## Failures / Blockers

- The first `pnpm run test:e2e` attempt was blocked by the local sandbox:
  - `apiRequestContext.post: connect EPERM 127.0.0.1:8001`
  - `wagent conversation: cannot reach API at http://127.0.0.1:8001`
  - Chromium launch failure:
    `bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer... Permission denied`
- The same deterministic E2E command passed outside the sandbox with
  `19 passed (14.0s)`. This indicates an environment permission blocker, not a
  product regression.

## Conclusion

11.1.5 targeted API regression, optional replay hook / task planning preview
baselines, CLI conversation regression, Alembic head check, and current
deterministic E2E keep-running all passed after rerunning E2E outside the local
sandbox. No Agent-operated UI or live autonomous smoke was performed.
