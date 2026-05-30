# 测试计划（Test Plan）

状态：ready_for_implementation

## Boundaries

本包只运行 repo-local deterministic tests 和 static checks。

不运行：

- live external black-box validation；
- `wagent chat` live product validation；
- `verify-scenario`；
- autonomous run；
- browser / UI smoke；
- direct autonomous-run endpoint；
- direct replay API product validation。

## Required Commands

### D1 - Seven-doc package existence

```bash
find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f | sort
```

Expected: exit `0`, listing exactly these package files with the directory prefix:

```text
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/README.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/contract.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/intent.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/plan.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/review.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/technical-design.md
docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/test-plan.md
```

### D2 - Required documentation terms

```bash
rg -n "Learned Action Matching Improvement|implementation_authorized|ambiguous|low-confidence|Forbidden Changes|Exit criteria" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement
```

Expected: exit `0`, required terms found in child docs. The package must also contain
an explicit `Exit Criteria` section; command text alone is not sufficient evidence.

### T1 - Chat runtime focused tests

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
```

Expected: exit `0`. Coverage must include:

- same business action with new slot values matches;
- action-side `business_goal` / `canonical_goal` / `business_object` / `match_terms`
  are consumed;
- different action on same business object does not direct-match;
- multiple plausible matches require choice / clarification;
- generic verb-only learned action does not overmatch a richer request;
- existing alias / utterance matching remains compatible.

### T2 - Router focused tests, if router changes

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q
```

Expected if router changes: exit `0`, known-action counting aligns with runtime matching terms.

If router does not change, record this command as `not run` with reason.

### T3 - Focused ruff

```bash
cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/router_agent.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
```

Expected: exit `0`, `All checks passed!`.

### T4 - Forbidden target constants scan

```bash
rg -n "<fixture-port>|/target-page|inventory item|External-Fixture-Provider" apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/router_agent.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py
```

Expected: exit `1`, no output.

This scan intentionally covers touched runtime and focused tests. It is a minimum
token scan, not the whole review: code / evidence reviewers must also inspect
touched files for selectors, field labels, button text, placeholders, seed copy,
operation aliases, page source, and other Fixture-Site answer keys. Mentions may
still exist in docs and historical result records.

### T5 - Whitespace / patch sanity

```bash
git diff --check
```

Expected: exit `0`, clean.

### T6 - Closeout consistency

```bash
git status --short
git diff --name-only
```

Expected:

- created / modified in-scope files are listed in child `review.md`;
- parent `CURRENT_STATE.md` and parent review are aligned with child final status;
- no external result docs are listed;
- no external Fixture-Site / Fixture-Site source is listed.

## Red / Green Requirement

Before implementation, add focused tests and run them before implementation. At minimum,
positive matcher-consumption tests must fail red before implementation:

- same business action with new values fails to match before action-side identity terms are consumed;

Safety / negative tests may already pass under the current stricter matcher. Record them as
red tests if they fail today, or as explicit regression baselines if they are already green:

- create learned action does not overmatch search / delete;
- multiple plausible actions remain multiple candidates and trigger existing choice path;
- generic verb-only learned action does not match a richer business-object request.

Record red commands and failure summaries in `review.md`.

## Subagent Review Requirement

Design stage:

- Spec / contract reviewer checks child docs against parent plan and prior package contracts.
- Safety / evidence reviewer checks forbidden changes, target constants, and live-run boundaries.

Implementation closeout:

- Code / test reviewer checks matcher correctness and maintainability.
- Evidence / scope reviewer checks commands, not-run items, redaction / target-scan posture, and changed-file scope.

## Commands Not Run

| Item | Reason | Required wording |
|---|---|---|
| live external black-box validation | Owned by `11.3.8.5` and requires explicit live validation approval | `not run` |
| `wagent chat` live product validation | This package is repo-local matcher implementation only | `not run` |
| `verify-scenario` / autonomous run | Repository boundary prohibits casual live runs | `not run` |
| browser / UI smoke | No UI change | `not run` |
| external black-box result docs update | Owned by `11.3.8.5` after actual evidence | `not modified` |

## Blocker Recording Rule

Stop as `BLOCKED` if implementation requires:

- target-specific constants;
- DB migration;
- external validation result updates;
- direct autonomous-run or replay endpoint evidence;
- broad fuzzy matching that cannot distinguish action intent;
- changing product lifecycle stage or internal Agent roles.

Stop as `NEEDS_USER_INPUT` if `CURRENT_STATE.md`, child `review.md`, parent `plan.md`,
subagent findings, or actual git state conflict.

## No Unverified Claims Rule

Unit / service tests may prove matcher behavior. They do not prove PV-CLI-003 passes.
Do not write `PV-CLI-003 fixed`, `external validation passed`, or `live product pass`
unless `11.3.8.5` actually reruns approved external validation and updates result docs with evidence.
