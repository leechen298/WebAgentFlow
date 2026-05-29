# 测试计划（Test Plan）

状态：PACKAGE_COMPLETE

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
find docs/iterations/m11/11.3.8.2-suggested-utterance-generation -maxdepth 1 -type f | sort
```

Expected: exit `0`, listing exactly these package files with the directory prefix:

```text
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/README.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/contract.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/intent.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/plan.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/review.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/technical-design.md
docs/iterations/m11/11.3.8.2-suggested-utterance-generation/test-plan.md
```

### D2 - Required documentation terms

```bash
rg -n "Suggested Utterance Generation|implementation_authorized|slot values|sensitive|external black-box" docs/iterations/m11/11.3.8.2-suggested-utterance-generation
```

Expected: exit `0`, required terms found in child docs.

### T1 - Learning service focused tests

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q
```

Expected: exit `0`. Coverage must include:

- business-object utterances from structured identity;
- slot-value exclusion from utterances;
- login / Chinese compatibility.

### T2 - Chat runtime focused tests

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
```

Expected: exit `0`. Coverage must include:

- stale wrapper utterances repaired before session storage;
- slot values excluded from stored utterances;
- existing chat runtime regression coverage remains green.

### T3 - Focused ruff

```bash
cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py
```

Expected: exit `0`, `All checks passed!`.

### T4 - Forbidden target constants scan

```bash
rg -n "5177|/inventory|inventory item|WebAgentFlow-Validation-Site" apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py
```

Expected: exit `1`, no output.

This scan intentionally covers touched runtime and focused tests. Mentions may still exist in docs and historical result records.

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

- in-scope child docs, touched implementation files, touched tests, `CURRENT_STATE.md`, and discoverability docs are listed in child `review.md`;
- no external result docs are listed;
- no external Validation-Site / Fixture-Site source is listed.

## Red / Green Requirement

Before implementation, add focused failing tests for the new behavior and run them to observe the expected failure. At minimum:

- one learning service test where existing code generates wrapper / truncated utterances instead of full business-object utterances;
- one chat runtime test where stale `Learn how to ...` wrapper utterances would be stored without the new repair helper;
- one chat runtime test where stale truncated-label wrapper utterances such as `帮我Create purchase orde`
  / `Create purchase orde一下` would be stored without the new repair helper;
- one negative alias test proving verb-only aliases such as `create` are not generated as reusable
  utterances.

Record the red commands and failure summaries in `review.md`.

## Commands Not Run

| Item | Reason | Required wording |
|---|---|---|
| live external black-box validation | Owned by `11.3.8.5`; user explicitly prohibited it in this goal | `not run` |
| `wagent chat` live product validation | This package is deterministic utterance generation only | `not run` |
| `verify-scenario` / autonomous run | Repository boundary prohibits casual live runs | `not run` |
| browser / UI smoke | No UI change | `not run` |
| external black-box result docs update | User explicitly prohibited it | `not modified` |

## Blocker Recording Rule

Stop as `BLOCKED` if implementation requires:

- LLM utterance generation;
- matcher threshold / candidate policy changes;
- target-specific constants;
- DB migration;
- external validation result updates;
- direct autonomous-run or replay endpoint evidence.

Stop as `NEEDS_USER_INPUT` if `CURRENT_STATE.md`, child `review.md`, parent `plan.md`, or actual git state conflict.

## No Unverified Claims Rule

Unit tests may prove deterministic utterance generation. They do not prove PV-CLI-003 passes.
Do not write `PV-CLI-003 fixed`, `external validation passed`, or `live product pass` unless `11.3.8.5`
actually reruns the approved external validation and updates result docs with evidence.
