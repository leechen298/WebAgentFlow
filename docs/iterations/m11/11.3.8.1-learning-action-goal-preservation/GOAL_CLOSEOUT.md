# 11.3.8.1 Review-Closeout Plan

## Summary

- Scope is only `11.3.8.1-learning-action-goal-preservation` review closeout. Do not reimplement it and do not create/start `11.3.8.2`.
- The decision is whether existing HEAD can serve as a stable metadata contract input for `11.3.8.2`.
- If successful, mark only `11.3.8.1` as `PACKAGE_COMPLETE`. Keep parent `11.3.8` active / in progress with next action `11.3.8.2`; do not mark the parent campaign complete.

## Contract To Confirm

- Internal metadata contract only:
  - `LearningRunRequest`: optional `action_goal`, `canonical_goal`, `action_aliases`.
  - `LearningRunResult`: optional `business_goal`, `canonical_goal`, `action_aliases`, `business_object`, `match_terms`.
  - Session `metadata_json.learned_actions[]`: optional `business_goal`, `canonical_goal`, `action_aliases`, `business_object`, `match_terms`.
- No public API, DB migration, frontend, fixture, worker, replay, reporter, recovery, abort, matcher policy, or external validation result change.
- `11.3.8.2` may consume these metadata fields only after this closeout confirms they are stable.

## Required Closeout Checks

1. Git and routing consistency:
   - Run `git status -sb`.
   - Run `git diff --name-status 86d3c5a..HEAD -- apps/api`; expected: no API/runtime/test drift after the last code-review checkpoint.
   - Confirm `CURRENT_STATE.md`, parent `review.md`, child `review.md`, M11 README, and M11 plan agree this is `11.3.8.1` review-closeout, not `11.3.8.2`.

2. Implementation diff review:
   - Review only the 11.3.8.1 implementation range:
     ```bash
     git diff 45ed70d^..86d3c5a -- apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/app/routers/conversation.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py
     ```
   - Confirm changes are limited to metadata preservation, internal learning handler handoff, and focused tests.
   - Confirm `_matching_actions()` is not broadened to consume the new metadata in this package.

3. Metadata behavior review:
   - Confirm structured intake identity reaches `LearningRunRequest`.
   - Confirm slot-bearing values are excluded from `business_goal`, `alias`, and `match_terms`.
   - Confirm `business_object` and object-only match terms are derived when identity comes from intake.
   - Confirm old learned actions without new metadata keys remain valid.

4. Verification commands:
   - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q`
   - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q`
   - `cd apps/api && ../../.venv/bin/python -m ruff check app/routers/conversation.py app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py`
   - `git diff --check`

5. Scope and target-constant scan:
   - Run:
     ```bash
     rg -n "5177|/inventory|inventory item|WebAgentFlow-Validation-Site|data-testid" apps/api/app/routers/conversation.py apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py
     ```
   - Every match must be classified.
   - Target URL, route, selector, seed data, page-source, runtime default, prompt answer key, or eval-default references in changed runtime code are blockers.
   - Business-language examples such as `inventory item` are allowed only in focused tests or docs when they are not runtime special cases.

## Allowed Docs Updates

Only update closeout/routing records if executing this plan:

- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`

Do not edit `GOAL_RUNNER.md`, parent `plan.md`, or any `11.3.8.2` docs unless explicitly asked.

## Do Not Run

- No `wagent chat` external black-box validation.
- No `verify-scenario`.
- No browser/UI smoke.
- No direct `/exploration/autonomous-runs` or `/stream`.
- No external result doc update.
- No 11.3.8.2 implementation or package creation.

## Decision Rule

- `PACKAGE_COMPLETE`: all required checks pass, no P0/P1 findings, and child `review.md` records a stable metadata contract plus exact evidence.
- `FOLLOW_UP_REQUIRED`: focused tests or review expose an in-scope defect.
- `BLOCKED`: completion would require matcher policy, public schema/API, migration, target-specific constants, or external validation evidence.
- `NEEDS_USER_INPUT`: `CURRENT_STATE.md`, child docs, review evidence, or git state conflict in a way read-only review cannot resolve.
