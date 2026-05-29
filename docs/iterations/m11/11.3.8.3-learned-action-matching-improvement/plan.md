# 实施计划（Plan）

状态：ready_for_implementation

## Documentation Generation Plan

Target package path:

```text
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/
```

Package type: `code`

Parent / child route:

- Parent: `11.3.8-external-black-box-validation-recovery`
- Current route: `create-review-seven-doc-package`.
- Implementation in this goal is allowed only after read-only subagent design / safety review
  records no unresolved P0 / P1 findings and this child `review.md` records
  `implementation_authorized: yes`.
- Required file set: the standard seven child documents.

Source-of-truth inputs read:

- `AGENTS.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `docs/iterations/README.md`
- `docs/product-model.md`
- `docs/scope-boundaries.md`
- Parent `README.md`, `intent.md`, `acceptance.md`, `plan.md`, `GOAL_RUNNER.md`, `CURRENT_STATE.md`
- `11.3.8.1` contract / review
- `11.3.8.2` contract / technical design / test plan / review
- External black-box latest result and PV-CLI-003 triage

Implementation authorization boundary:

- Code changes are forbidden until read-only subagent design review passes and `review.md`
  records `implementation_authorized: yes`.

## Implementation Steps

1. Create the seven-document child package.
2. Run documentation checks:
   - `find ... -maxdepth 1 -type f | sort`
   - required-term `rg`.
3. Dispatch read-only subagent design review:
   - spec / contract reviewer;
   - safety / evidence reviewer.
4. Fix any P0 / P1 design findings.
5. Record `implementation_authorized: yes` only after design reviewers find no P0 / P1 blockers.
6. Add TDD red tests in `test_conversation_chat_runtime.py`.
7. Implement matcher changes in `chat_runtime.py`.
8. Inspect router known-action counting and change `router_agent.py` only if a failing focused test proves it is required.
9. Run required focused tests and checks.
10. Dispatch code / test and evidence / scope subagent review.
11. Fix any P0 / P1 findings and rerun relevant checks.
12. Update child `review.md`, parent `CURRENT_STATE.md`, parent `review.md`, and milestone discoverability docs as needed.

## Verification Commands

```bash
find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f | sort
rg -n "Learned Action Matching Improvement|implementation_authorized|ambiguous|low-confidence|Forbidden Changes|Exit criteria" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/router_agent.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
rg -n "5177|/inventory|inventory item|WebAgentFlow-Validation-Site" apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/router_agent.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py
git diff --check
git status --short
git diff --name-only
```

The target-constant scan is a minimum token scan and is expected to exit `1` with no output.
Code / evidence review must also inspect touched files for selectors, field labels, button
text, placeholders, seed copy, operation aliases, page source, and other Validation-Site
answer keys.

## Exit Criteria

- Child seven-doc package exists.
- Read-only subagent design / safety review records no unresolved P0 / P1 findings.
- `review.md` records `implementation_authorized: yes` before code changes.
- TDD red / green evidence proves positive matcher-consumption behavior.
- Negative / ambiguity / generic-verb guard coverage is recorded as red / green or baseline regression evidence.
- Focused tests, focused ruff, target-constant scan, `git diff --check`, and changed-file scope check are recorded.
- Parent `CURRENT_STATE.md`, parent `review.md`, M11 README, and M11 plan route the campaign to `11.3.8.4` only after this package is `PACKAGE_COMPLETE`.

## Stop Conditions

Stop as `BLOCKED` or `NEEDS_USER_INPUT` if:

- design review finds unresolved P0 / P1;
- implementation requires forbidden target-specific constants;
- matcher cannot distinguish create / search / delete without broad fuzzy matching;
- actual git state conflicts with parent `CURRENT_STATE.md` or this package docs;
- subagent review reports unresolved P0 / P1 that cannot be fixed in scope;
- live validation becomes necessary before `11.3.8.5`.

## Closeout Requirements

Before writing `PACKAGE_COMPLETE`, `review.md` must include:

- subagent tasks launched and outputs reviewed;
- changed files;
- commands run and exit codes;
- commands not run;
- TDD red / green evidence;
- compatibility review;
- scope review;
- unresolved findings by priority;
- final assessment.

## Handoff

If this package reaches `PACKAGE_COMPLETE`, update parent routing so
`11.3.8.4-regression-tests` is the next eligible child. Do not start live external
validation from this package.
