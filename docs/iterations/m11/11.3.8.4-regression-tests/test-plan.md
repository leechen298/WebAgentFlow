# 测试计划（Test Plan）

状态：ready_for_design_review

## Boundaries

本包只运行 repo-local deterministic tests 和 static checks。

不运行：

- live external black-box validation；
- live `wagent chat`；
- `verify-scenario`；
- autonomous run；
- browser / UI smoke；
- direct autonomous-run endpoint；
- direct replay API product validation。

## Required Commands

### D1 - Seven-doc package existence

```bash
find docs/iterations/m11/11.3.8.4-regression-tests -maxdepth 1 -type f | sort
```

Expected: exit `0`, exactly seven child docs listed.

### D2 - Required documentation terms

```bash
rg -n "Regression Tests|external site|synthetic|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.4-regression-tests
```

Expected: exit `0`, required terms found in package docs.

### T1 - Focused regression tests

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q
```

Expected: exit `0`. Coverage must include:

- positive synthetic learn -> execute same business action with new values;
- learned action business identity persisted in session action;
- session learned action `utterances` and `match_terms` include the full reusable
  business action / canonical goal / useful alias / business object, not only the
  teaching wrapper or truncated label;
- slot values are absent from reusable `utterances` and `match_terms`;
- replay handler receives learned path id, synthetic URL, and new slot overrides;
- replay handoff uses the same current-session action whose reusable `utterances`
  and `match_terms` were asserted;
- different action same object does not direct-execute;
- ambiguous candidates require choice;
- generic verb-only does not overmatch richer request.

### T2 - Focused ruff

```bash
cd apps/api && ../../.venv/bin/python -m ruff check tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
```

Expected: exit `0`, `All checks passed!`.

### T3 - Forbidden target constants scan

```bash
rg -n "<fixture-port>|/target-page|inventory item|External-Fixture-Provider" apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py apps/api/app/services/conversation apps/api/app/services/learning apps/api/app/services/task_planning apps/api/app/prompts
```

Expected: exit `1`, no output.

This scan covers touched focused tests plus relevant product runtime / prompt roots.
It is still a minimum token scan; reviewers must also inspect for external site
selectors, labels, button text, placeholders, seed copy, page source, and operation
aliases.

### T4 - Patch sanity

```bash
git diff --check
git status --short
git diff --name-only
```

Expected: changed files are in scope and no whitespace errors.

## Red / Baseline Requirement

Because `11.3.8.4` starts after `11.3.8.1` through `11.3.8.3` fixes, the new
regression may pass immediately on current HEAD. Record honestly:

- If a new regression fails before test helper adjustment, record red evidence.
- If it passes immediately, record it as post-fix regression baseline, not as a
  new production-code red/green cycle.
- Do not fabricate red evidence by reverting production code.

## Subagent Review Requirement

Design stage:

- Spec / regression reviewer checks that proposed regression truly combines
  11.3.8.1 / 11.3.8.2 / 11.3.8.3.
- Safety / evidence reviewer checks target-agnostic scope and live-run boundaries.

Closeout:

- Test / coverage reviewer checks regression quality and guard coverage.
- Evidence / scope reviewer checks commands, changed files, forbidden target scan,
  and not-run live validation wording.

## Commands Not Run

| Item | Required status | Reason |
|---|---|---|
| live external black-box validation | `not run` | Owned by `11.3.8.5` and requires explicit approval |
| live `wagent chat` | `not run` | This package is repo-local regression only |
| `verify-scenario` / autonomous run | `not run` | Repository boundary prohibits casual live runs |
| browser / UI smoke | `not run` | No UI change |
| external latest result docs | `not modified` | Owned by `11.3.8.5` after actual evidence |

## Blocker Recording Rule

Stop as `BLOCKED` if regression needs external site source, target route, selector,
seed copy, page source, live browser execution, or runtime changes not approved by
this design.

Stop as `NEEDS_USER_INPUT` if parent `CURRENT_STATE.md`, child docs, subagent findings,
or git state conflict.
