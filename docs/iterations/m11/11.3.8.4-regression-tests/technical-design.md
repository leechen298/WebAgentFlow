# 技术设计（Technical Design）

状态：ready_for_design_review

## Current State

`11.3.8.1` added learned action identity metadata.
`11.3.8.2` generated reusable utterances / match terms.
`11.3.8.3` consumed those fields in chat runtime matching and router known-action
counting.

Current focused tests cover each package locally, but there is not yet a single
regression that exercises the combined learn-to-execute chain.

## Contract Alignment / Invariants

| Requirement | Design mechanism | Test entry |
|---|---|---|
| Positive chain is target-agnostic | synthetic URL + fake handlers + business terms unrelated to external target | R1 |
| New values are execution parameters | assert replay `slot_overrides` and evidence target text | R1 |
| Business identity survives learning output | inspect session `learned_actions` after fake learning result | R1 |
| Different action same object does not execute | search/delete style execute request with same object | R2 |
| Ambiguous learned actions require choice | two plausible current-session learned actions | R3 |
| Generic verb-only does not overmatch | learned action alias/utterance only `Create` | R4 |
| No external target dependency | target-token scan over touched runtime/tests | S1 |

## Proposed Implementation

Add focused regression tests in `apps/api/tests/test_conversation_chat_runtime.py`
unless design review requests a different file split.

Suggested test shape:

1. Create an interactive chat session.
2. Use a fake intake service for learning request with:
   - `goal="Create purchase order"` or another synthetic business action;
   - `canonical_goal="create_purchase_order"`;
   - useful alias such as `add purchase order`;
   - slot value `Alpha`.
3. Use a fake learning handler that returns a wrapper label such as
   `Learn how to create` plus a learned path id from existing helper ingestion.
   The handler should either return the same business identity metadata produced
   by the 11.3.8.1 / 11.3.8.2 path or force the chat runtime to derive it from
   intake; the test must not rely on wrapper terms to pass.
4. Assert session learned action stores reusable identity and specifically:
   - `alias` is the full business action, not only `Learn how to create`;
   - `utterances` include the full business action / useful alias from 11.3.8.2;
   - `match_terms` include the full business action, canonical goal, useful alias,
     and business object;
   - slot values are absent from reusable `utterances` / `match_terms`.
5. Dispatch execute request with new value `Beta`.
6. Assert replay handler is called once with the same learned path id, synthetic URL,
   and `slot_overrides` containing the new value.
7. Assert the replayed learned action is the same current-session action whose
   `utterances` / `match_terms` were checked above, proving the chain does not
   bypass 11.3.8.2 reusable terms.

Negative / guard tests may reuse helpers from `11.3.8.3` tests if present.

## Affected Surfaces

| Surface | Changed? | Description |
|---|---|---|
| Runtime code | No by default | Regression-only package |
| API / DB / schema | No | No public contract change |
| CLI / Console / Worker | No | No surface change |
| Tests | Yes | Focused repo-local regression |
| Docs | Yes | Child docs and closeout routing |

## Data / Schema Changes

None.

## Service / Module Design

No service code change is planned.

If tests cannot express the regression without changing product code, stop and
update this technical design before editing runtime.

## Data Flow

```text
synthetic learn request
  -> fake intake result with business identity
  -> fake learning result with learned_path_id and identity metadata
  -> session learned_actions[]
  -> synthetic execute request with new values
  -> matcher / router existing runtime path
  -> fake replay handler
  -> assertions on learned_path_id, URL, slot_overrides, and events
```

## Compatibility

- Current chat runtime tests remain the primary compatibility suite.
- New regression should use existing test helpers rather than new fixtures or external files.
- Any helper extraction must stay local to tests and preserve existing test semantics.

## Failure / Edge Cases

- If the regression passes immediately on current HEAD, record it as post-fix
  regression baseline, not as red/green production-code evidence.
- If a negative case fails, fix only tests or package design unless a runtime bug
  is explicitly in scope after review.
- If live site behavior is needed to prove the scenario, stop and route to `11.3.8.5`.

## Non-goals

- No external black-box validation.
- No live `wagent chat`.
- No browser / UI smoke.
- No autonomous-run endpoint.
- No runtime matcher changes unless design is updated.
- No external result docs update.

## Test Matrix

| ID | Area | Coverage |
|---|---|---|
| R1 | Positive chain | learn create business action -> execute same business action with new value -> replay handoff |
| R2 | Negative action | create learned action does not direct-match search/delete same object |
| R3 | Ambiguity | multiple plausible learned actions require pending choice |
| R4 | Generic guard | generic verb-only action does not overmatch richer request |
| S1 | Integrity | no forbidden target constants in touched runtime/tests |

## Validation Commands

```bash
find docs/iterations/m11/11.3.8.4-regression-tests -maxdepth 1 -type f | sort
rg -n "Regression Tests|external site|synthetic|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.4-regression-tests
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q
cd apps/api && ../../.venv/bin/python -m ruff check tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
rg -n "<fixture-port>|/target-page|inventory item|External-Fixture-Provider" apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py apps/api/app/services/conversation apps/api/app/services/learning apps/api/app/services/task_planning apps/api/app/prompts
git diff --check
git status --short
git diff --name-only
```

The target scan is a minimum token scan. Reviewers must also inspect for external
site selectors, labels, button text, placeholders, seed copy, page source, and
operation aliases.

## Exit Criteria

- Seven-doc package exists and design review has no unresolved P0 / P1.
- `review.md` records `implementation_authorized: yes` before test changes.
- Focused regression tests pass and are target-agnostic.
- Focused ruff, target scan, and diff sanity pass.
- Subagent closeout review has no unresolved P0 / P1.
- Parent routing advances to `11.3.8.5` only after this package reaches
  `PACKAGE_COMPLETE`, and live validation approval is still required.
