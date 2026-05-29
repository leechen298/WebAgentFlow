# 契约（Contract）

状态：ready_for_design_review

## Public Concepts

本包不新增 public API、DB schema、runtime status、Agent role 或 lifecycle stage。

它新增的是 test-level concept：

- `target-agnostic learned-action regression`：不依赖外部站点的 repo-local automated
  regression，用 synthetic URL、fake handlers 和 session metadata 覆盖 learn-then-execute
  semantic chain。

## Allowed Changes

允许改动：

- Focused tests in:
  - `apps/api/tests/test_learning_run_service.py`
  - `apps/api/tests/test_conversation_chat_runtime.py`
  - `apps/api/tests/test_conversation_router_agent.py`
- Test helper cleanup in those files only when it reduces duplication and does not change runtime behavior.
- Child package docs.
- Parent routing / closeout docs after package closeout:
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`
  - `docs/iterations/m11/README.md`
  - `docs/iterations/m11/m11-plan.md`

Runtime code changes are forbidden by default. If a missing test seam is found,
stop and update this contract / technical design before implementation.

## Forbidden Changes

本包不得：

- 修改 learning, matcher, router, replay, reporter, recovery, abort, frontend, worker,
  DB migration, public API, eval runner, or prompt behavior.
- 修改 `WebAgentFlow-Validation-Site` / `WebAgentFlow-Fixture-Site`。
- 恢复 `apps/product-test-site` / `apps/validation-site`。
- 依赖 `5177/inventory`、external target URL、selector、`data-testid`、component name、
  seed copy、field label、button text、placeholder、operation alias 或 page source。
- 运行 live external validation、`wagent chat` live validation、`verify-scenario`、
  browser / UI smoke、direct autonomous-run endpoint 或 direct replay API product validation。
- 更新 `docs/testing/results/external-black-box-validation-*`。
- 把 repo-local regression 结果写成 external product pass。

## Regression Semantics

Positive regression must prove:

- learning result / session action has reusable business identity;
- suggested utterances / match terms include the business action, not only teaching wrapper;
- the test asserts `utterances` / `match_terms` on the same current-session action
  that is later replayed, so the chain cannot pass by canonical goal alone;
- execute request with new values matches the learned action;
- replay handler receives new slot values as execution parameters, not action identity.

Negative regression must prove:

- different action on same object does not direct-execute;
- multiple plausible matches require pending choice / clarification;
- generic verb-only action does not overmatch richer request;
- tests remain synthetic and target-agnostic.

## Evidence Contract

Allowed evidence:

- Documentation checks.
- Focused repo-local pytest.
- Focused ruff.
- Target-constant scan over touched runtime/tests.
- `git diff --check`, `git status --short`, `git diff --name-only`.
- Subagent review notes.

Not allowed as pass evidence:

- external black-box validation rerun;
- live `wagent chat`;
- `verify-scenario`;
- browser / UI smoke;
- direct autonomous-run endpoint;
- direct replay API product validation.

## Compatibility Requirements

- Existing 11.3.8.1 / 11.3.8.2 / 11.3.8.3 focused tests must remain valid.
- New tests must not make external site details an active dependency.
- Public user responses and committed docs must not leak private ids, selectors,
  private maps, slot override internals, execution payloads, credentials, tokens,
  cookies, or secrets.

## Status Contract

| Status | Meaning |
|---|---|
| `ready_for_design_review` | Seven docs exist; implementation not authorized. |
| `ready_for_implementation` | Read-only design / safety review passed and `implementation_authorized: yes` is recorded. |
| `PACKAGE_COMPLETE` | Tests, required verification, subagent review, and P0 / P1 fixes are complete. |
| `FOLLOW_UP_REQUIRED` | Regression exists but caveats remain that prevent clean closeout. |
| `BLOCKED` | Regression requires forbidden live/site/runtime dependency. |
| `NEEDS_USER_INPUT` | Source conflict or approval requirement prevents valid closeout. |

## Open Risks

- A regression that reuses too much implementation detail may miss the real chain.
- A regression that uses external target nouns / routes can become a hidden answer key.
- Current HEAD may already pass the new regression, so red evidence may be limited to
  assertion-level or historical failure reasoning; this must be recorded honestly.
