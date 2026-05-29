# 契约（Contract）

状态：PACKAGE_COMPLETE

## Public Concepts

本包不新增 public API、database schema、Agent role 或 lifecycle stage。

它明确一个 internal learned action concept：

- `suggested_utterances`：用户可以在后续轮次自然表达同一业务动作的 reusable phrases。
  这些 phrases 可用于提示用户、保存 session learned action metadata，并可被后续 matcher
  包消费。它们不是 replay authorization，也不是 external validation pass evidence。

## Allowed Changes

允许改动：

- `apps/api/app/services/learning/learning_run_service.py`
  - 用 `business_goal`、readable `canonical_goal`、useful aliases 和 `business_object`
    生成 deterministic utterances。
  - 保持 `login` spec utterances 和 existing Chinese wrapper behavior 兼容。
- `apps/api/app/services/conversation/chat_runtime.py`
  - 在保存 learned action metadata 时，如果 learning result 仍只返回 wrapper utterances，
    可用 business identity 生成 safer reusable utterances。
  - 不改变 matcher threshold、confidence、candidate selection 或 replay execution。
- Focused tests:
  - `apps/api/tests/test_learning_run_service.py`
  - `apps/api/tests/test_conversation_chat_runtime.py`
- 本 child package docs 和 M11 discoverability docs。
- Parent routing / closeout docs only when required by `GOAL_RUNNER.md` closeout:
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
  - `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`

## Forbidden Changes

本包不得：

- 新增 LLM utterance generation dependency。
- 新增完整翻译系统、语言模型 prompt 或 provider call。
- 修改 `_matching_actions()` policy、candidate threshold、多候选选择、pending choice、
  replay execution、Task Result Reporter、router decision policy 或 recovery / abort 行为。
- 修改 public API endpoint、DB migration、frontend UI、worker flow、fixture site 或 eval runner。
- 修改 `WebAgentFlow-Validation-Site` / `WebAgentFlow-Fixture-Site`。
- 恢复 `apps/product-test-site` / `apps/validation-site`。
- 更新 external black-box result docs。
- 运行 live external validation、`verify-scenario`、browser smoke 或 direct autonomous-run endpoint。
- 在 runtime / prompts / active eval defaults 中写入 `5177/inventory`、external target selectors、
  `data-testid`、component names、seed copy、field labels、button text、placeholder、
  operation aliases 或 page source。
- 把 slot values、sensitive values、private ids、slot override payload、credentials、tokens、
  cookies、SKU、商品名、数量或 page-specific values 写入 reusable utterances。

## Input / Output Semantics

Input sources:

- `LearningRunRequest.action_goal`
- `LearningRunRequest.canonical_goal`
- `LearningRunRequest.action_aliases`
- `LearningRunRequest.fill_values`
- `LearningRunResult.business_goal`
- `LearningRunResult.business_object`
- chat runtime `ConversationIntakeResult.action`
- chat runtime `ConversationIntakeResult.slots`

Output rules:

- For login spec behavior, preserve existing utterances: `帮我登录`, `登录一下`。
- For existing Chinese product-level labels such as `创建记录`, preserve existing Chinese wrappers
  where they keep the business object.
- For English / generic business identity, include a direct business phrase and an English help phrase,
  for example `Create purchase order` and `Help me create purchase order`.
- Include useful aliases when they are deterministic, non-duplicate, and do not contain slot values.
- Exclude verb-only or generic aliases such as `create`, `add`, `open`, `update`, or `delete`
  unless they are part of a phrase with a business object.
- Do not include pure business object alone as the first reusable utterance unless no action phrase exists.
- De-duplicate by normalized lowercase phrase while preserving deterministic order.

## Compatibility Requirements

- Existing session actions without new identity fields remain valid.
- Existing display consumers can keep showing `alias`.
- Existing Chinese learning tests must not regress unless the old expected utterance dropped the business object.
- Existing `login` spec behavior must remain unchanged.
- New utterances are optional metadata-level changes; no DB migration is allowed in this package.
- Backward compatibility must allow learning handlers that return older wrapper utterances.

## Evidence / Verification Contract

Allowed evidence:

- Focused pytest for learning service utterance generation.
- Focused pytest for chat runtime action metadata preservation.
- Focused ruff on touched Python files.
- Target-constant scan over touched runtime / tests.
- `git diff --check`.
- Child docs existence / content checks.

Not allowed as pass evidence:

- external black-box validation rerun;
- `wagent chat` live product validation;
- `verify-scenario`;
- autonomous-run endpoint;
- direct replay API or internal service import as WAgent product evidence.

## Product Model / Scope / Roadmap Alignment

- Product lifecycle stage changes: No.
- Internal Agent role changes: No.
- Milestone boundary changes: No.
- Public API / DB / replay status / reporter / recovery / abort contract changes: No.
- This package stays within M11.3 runtime chat learned-action metadata quality.

## Out-of-scope Follow-ups

- Learned action matching improvement: `11.3.8.3`.
- Cross-chain regression package: `11.3.8.4`.
- External black-box revalidation / latest result update: `11.3.8.5`.
- Full learn-then-execute for arbitrary domains.
- M12 recovery / retry / abort / interruption.

## Status Contract

| Status | Meaning |
|---|---|
| `ready_for_design_review` | Seven docs exist; code implementation not authorized yet. |
| `ready_for_implementation` | Read-only spec / design review passed and `review.md` records `implementation_authorized: yes`. |
| `PACKAGE_COMPLETE` | Implementation, required verification, subagent code/test/evidence review, and P0/P1 fixes are complete. |
| `FOLLOW_UP_REQUIRED` | Non-blocking P2/P3 or deferred scope remains, but package cannot honestly close as complete. |
| `BLOCKED` | Required scope cannot be implemented without forbidden changes. |
| `NEEDS_USER_INPUT` | Source-of-truth conflict or missing approval prevents a valid package closeout. |

## Open Risks

- Improving utterances may indirectly make existing matcher behavior match more cases because matcher already consumes utterances. This is allowed only as a data-quality effect, not as a matcher policy change.
- The action label remains short and may truncate English phrases; utterances must use full business identity rather than the truncated label.
- Generic aliases such as `create` alone could overmatch later; this package should not generate verb-only utterances.
