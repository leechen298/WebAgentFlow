# 实施计划（Plan）

状态：ready_for_design_review

## Documentation Generation Plan

Target package path:

```text
docs/iterations/m11/11.3.8.4-regression-tests/
```

Package type: `code`

Parent / child route:

- Parent: `11.3.8-external-black-box-validation-recovery`
- Current route: `create-review-seven-doc-package`.
- Implementation is allowed only after read-only design / safety review has no
  unresolved P0 / P1 and this child `review.md` records
  `implementation_authorized: yes`.

Source-of-truth inputs read:

- `AGENTS.md`
- `docs/iterations/README.md`
- Parent `plan.md`, `acceptance.md`, `CURRENT_STATE.md`
- `11.3.8.1` / `11.3.8.2` / `11.3.8.3` package reviews and contracts
- Existing focused test helpers in chat runtime, router, and learning service tests

## Implementation Steps

1. Create seven-document child package.
2. Run documentation checks.
3. Dispatch read-only design / safety review subagents.
4. Fix P0 / P1 design findings.
5. Record `implementation_authorized: yes` only after review approval.
6. Add target-agnostic regression tests.
7. Run focused pytest / ruff / target scan / diff sanity.
8. Dispatch closeout test / evidence subagent reviews.
9. Fix P0 / P1 findings.
10. Update child review and parent routing to `11.3.8.5` only if this package
    reaches `PACKAGE_COMPLETE`.

## Verification Commands

```bash
find docs/iterations/m11/11.3.8.4-regression-tests -maxdepth 1 -type f | sort
rg -n "Regression Tests|external site|synthetic|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.4-regression-tests
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q
cd apps/api && ../../.venv/bin/python -m ruff check tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
rg -n "5177|/inventory|inventory item|WebAgentFlow-Validation-Site" apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py apps/api/app/services/conversation apps/api/app/services/learning apps/api/app/services/task_planning apps/api/app/prompts
git diff --check
git status --short
git diff --name-only
```

## Exit Criteria

- Seven-doc package exists.
- Read-only design / safety review has no unresolved P0 / P1.
- `review.md` records `implementation_authorized: yes` before tests are added.
- Regression tests are target-agnostic and focused.
- Focused pytest, ruff, target scan, and diff sanity pass.
- Closeout subagents approve or all P0 / P1 findings are fixed.
- Parent route advances to `11.3.8.5` only after this package reaches
  `PACKAGE_COMPLETE`.

## Stop Conditions

Stop as `BLOCKED` or `NEEDS_USER_INPUT` if:

- tests require external site source or live browser operation;
- tests require `5177/inventory` or external selectors / labels / seed copy;
- runtime changes appear necessary without design update;
- subagent review reports unresolved P0 / P1;
- live validation becomes necessary before `11.3.8.5`;
- actual git state conflicts with child / parent routing docs.

## Handoff

If this package reaches `PACKAGE_COMPLETE`, `11.3.8.5` may create its validation
package. It must still stop before live validation until the user supplies API base
URL, target URL, DB state policy, scenario list, and latest-result-doc update
approval.
