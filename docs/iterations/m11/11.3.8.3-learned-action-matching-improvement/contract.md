# 契约（Contract）

状态：ready_for_implementation

## Public Concepts

本包不新增 public API、database schema、Agent role 或 lifecycle stage。

它细化一个 internal runtime concept：

- `learned action match terms`：当前 session learned action 上可用于匹配的 target-agnostic
  business identity terms，来源包括 `alias`、`utterances`、`business_goal`、
  `canonical_goal`、`action_aliases`、`business_object` 和 `match_terms`。

这些 terms 只是 matcher input，不是 replay authorization；最终仍必须绑定当前 session 内
的具体 learned action，并保持 scope / ambiguity / safety gates。

## Allowed Changes

允许改动：

- `apps/api/app/services/conversation/chat_runtime.py`
  - 扩展 `_matching_actions()` 或其私有 helper，使 action-side terms 消费 11.3.8.1 /
    11.3.8.2 metadata。
  - 保留现有 normalized exact / intersection matching 兼容性。
  - 增加 generic verb / weak match 保护。
  - 保持多候选进入 existing pending choice / clarification path。
- `apps/api/app/services/conversation/router_agent.py`
  - 仅当 required tests 证明 router known-action counting 与 runtime matcher 不一致时，
    同步 target-agnostic term counting。
- Focused tests:
  - `apps/api/tests/test_conversation_chat_runtime.py`
  - `apps/api/tests/test_conversation_router_agent.py` only if router behavior changes
- 本 child package docs。
- Parent routing / closeout docs when required by `GOAL_RUNNER.md` closeout:
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`
  - `docs/iterations/m11/README.md`
  - `docs/iterations/m11/m11-plan.md`

## Forbidden Changes

本包不得：

- 修改 learning result metadata preservation。
- 修改 deterministic suggested utterance generation。
- 修改 replay execution、Task Result Reporter、recovery、abort、frontend、worker、
  DB migration、public API endpoint、eval runner 或 external result docs。
- 修改 `External-Fixture-Provider` / `WebAgentFlow-Fixture-Site`。
- 恢复 `apps/fixture-site` / `apps/fixture-site`。
- 运行 live external validation、`verify-scenario`、browser smoke 或 direct
  autonomous-run endpoint。
- 用 direct replay API、internal service import、hidden HTTP client 或 ad hoc script 作为
  WAgent product pass evidence。
- 在 runtime / prompts / active eval defaults 中写入 `<fixture-port>/target-page`、external target
  selectors、`data-testid`、component names、seed copy、field labels、button text、
  placeholder、operation aliases 或 page source。
- 仅凭共享动词 `create`、`open`、`update`、`delete` 直接匹配并执行。
- 在多个 plausible learned actions 同时匹配时静默选择一个执行。

## Match Semantics

Matcher may consider a learned action only when:

- the action is already in the current session learned action list;
- existing target URL / site origin / page template scope logic allows it;
- action-side target-agnostic terms overlap with user input or intake terms strongly enough
  to identify the same business action.

Positive match examples:

- action has `canonical_goal=create_inventory_item` and execute intake has
  `canonical_goal=create_inventory_item`;
- action has `business_goal=Create inventory item` and execute user goal normalizes to
  the same business phrase;
- action has `business_object=inventory item` plus action verb `create`, and execute request
  also expresses create + inventory item.

Negative / weak match examples:

- `Create inventory item` must not direct-match `Search inventory item` or
  `Delete inventory item`;
- action with only `Create` / `Open` / `Update` / `Delete` must not match a richer request;
- shared business object without compatible action intent is insufficient.

## Schema / API Contract

No public API endpoint or DB migration is planned.

Existing optional session metadata keys remain backward-compatible:

- `business_goal`
- `canonical_goal`
- `action_aliases`
- `business_object`
- `match_terms`
- `utterances`
- `alias`

Existing learned actions without these keys must remain valid and keep current alias /
utterance matching behavior.

## Evidence / Verification Contract

Allowed evidence:

- TDD red / green focused pytest output for chat runtime matcher behavior.
- Focused router tests only if router code changes.
- Focused ruff on touched Python files.
- Forbidden target scan over touched runtime / tests.
- `git diff --check`.
- Subagent design / safety / code / evidence review notes recorded in `review.md`.

Not allowed as pass evidence:

- external black-box validation rerun;
- `wagent chat` live product validation;
- `verify-scenario`;
- autonomous-run endpoint;
- direct replay API or internal service import as WAgent product evidence.

## Compatibility Requirements

- Existing login / Chinese / generic known-action behavior must not regress.
- Existing session actions without new identity fields keep matching by alias / utterances.
- Existing pending choice, no-path, vague-input, cancellation, recovery, reporter, and replay
  semantics remain unchanged.
- No private ids, private maps, slot overrides, execution payloads, credentials, tokens,
  cookies, selectors, or private trace data may leak into user responses or committed artifacts.

## Out-of-scope Follow-ups

- Cross-chain automated regression coverage: `11.3.8.4`.
- External black-box revalidation and latest result updates: `11.3.8.5`.
- Replay execution, reporter, recovery, abort, frontend, worker, DB schema, and public API changes.
- Full arbitrary-domain learn-then-execute and M12 recovery / retry / interruption behavior.

## Product Model / Scope / Roadmap Alignment

- Product model alignment: stays within L3 runtime chat learned action reuse; code decides
  whether WebAgentFlow acts.
- Scope boundary alignment: LLM may parse intent, but code binds learned actions.
- Roadmap / milestone alignment: M11.3 post-closeout recovery follow-up under 11.3.8.
- Changes lifecycle stage / Agent role / milestone boundary: No.
- If Yes, authoritative docs to update first: N/A.

## Status Contract

| Status | Meaning |
|---|---|
| `ready_for_design_review` | Seven docs exist; implementation not authorized. |
| `ready_for_implementation` | Read-only subagent design / safety review passed and `implementation_authorized: yes` is recorded. |
| `PACKAGE_COMPLETE` | Implementation, required verification, subagent code / evidence review, and P0 / P1 fixes are complete. |
| `FOLLOW_UP_REQUIRED` | Non-blocking P2 / P3 or deferred scope remains, but package cannot honestly close as complete. |
| `BLOCKED` | Required matching cannot be implemented without forbidden changes. |
| `NEEDS_USER_INPUT` | Source-of-truth conflict, missing approval, or live-run requirement prevents valid closeout. |

## Open Risks

- Too-broad normalization can make unrelated learned actions look equivalent.
- Matching only `business_object` can overmatch create / search / delete variants.
- Router known-action count may need alignment if runtime matcher becomes stricter or richer.
