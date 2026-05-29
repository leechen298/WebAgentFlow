# 验收标准（Acceptance）

状态：ready for review

## Functional Acceptance

1. Learning action metadata preserves business goal。
   - 学习 `Create inventory item` 后，session learned action metadata 必须包含可匹配的业务目标。
   - 可接受字段形态由后续子迭代 contract 定义，但必须能表达 `Create inventory item` / `create_inventory_item` / business object。

2. Suggested utterances contain business object。
   - suggested utterances 不能只包含 `Learn how to create` 或其 wrapper。
   - 至少应包含可复用业务表达，例如 `Create inventory item` 或等价 normalized phrase。

3. Execute matching works for same business action with new slot values。
   - 学习 create inventory item 后，执行 `Create an inventory item with new values` 必须能匹配已学 action。
   - 新 slot values 应作为执行参数进入 replay / execution path，而不是成为新的 action identity。

4. Mismatched business action does not execute。
   - 学习 `Create inventory item` 后，`Search inventory item`、`Delete inventory item` 或其他不同业务动作不得被直接误匹配为 create。
   - 共享动词或共享对象不足以自动执行。

5. Ambiguous learned actions require choice。
   - 如果多个 learned actions 都可能匹配，runtime 必须进入 pending choice / planner choice / clarification。
   - 不允许低置信度自动猜一个 action 执行。

## Safety Acceptance

1. No hardcoded `5177/inventory` in runtime。
   - `5177/inventory` 只能作为 operator-provided URL 出现在 docs、result records、eval plan 或外部验证操作记录中。
   - 它不得成为 runtime default、prompt answer key、eval default、package dependency 或 internal route constant。

2. No Validation-Site answer key in runtime / prompt。
   - 不允许把外部 Validation-Site selector、`data-testid`、component、seed copy、field label、button text、placeholder、operation alias 或 page source 写入 product runtime / prompts。

3. No external site source modification。
   - 11.3.8 修复不得修改 `WebAgentFlow-Validation-Site` 或 `WebAgentFlow-Fixture-Site` 源码。
   - 外部站点只作为 operator-provided validation target 或 deterministic fixture provider。

4. Removed embedded sites stay removed。
   - 不恢复 `apps/product-test-site`。
   - 不恢复 `apps/validation-site`。
   - 不恢复内嵌 validation API。

5. Archived `5176/items` eval remains archived。
   - 旧 `5176/items` eval 可作为历史证据保留。
   - 不得重新作为 active default eval 或新的产品能力 pass 依据。

6. No direct autonomous-run endpoint for product validation。
   - 外部黑盒产品验证不得由 operator 直接调用 `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream` 产生。
   - 如通过 `wagent chat` learning flow 间接触发产品内部 exploration，必须在 evidence 中明确记录 operator surface 和产品请求边界。

7. No direct replay or service-import pass substitution。
   - direct replay API、internal service import、hidden HTTP client 或 ad hoc script 不能替代 WAgent chat runtime pass evidence。

## Test Acceptance

1. Focused unit / service tests pass。
   - learning label preservation。
   - suggested utterance generation。
   - match term normalization。
   - chat runtime action matching。
   - router known learned action counting where applicable。

2. Integration-ish regression passes without external site dependency。
   - Automated regression must not require `WebAgentFlow-Validation-Site` running。
   - It should use synthetic URLs, fake replay handlers, or existing test helpers。
   - It must not depend on external site selector, `data-testid`, component, seed copy, or `5177/inventory` as a hard dependency。

3. Negative matching tests pass。
   - same business action with new values matches。
   - different business action does not execute。
   - ambiguous candidate requires choice。
   - generic action label does not overmatch a richer business-object request unless the business object is present in learned metadata。

4. External black-box revalidation report exists after implementation。
   - New dated report exists under `docs/testing/results/external-black-box-validation-YYYYMMDD.md`。
   - `docs/testing/results/external-black-box-validation-latest.md` is updated only after actual revalidation。
   - The report records operator surface, preconditions, scenario outcomes, integrity checks, and any not-run / blocked / unverified items。

5. Integrity checks remain pass。
   - Forbidden target scan for product runtime / prompts returns pass for Validation-Site answer keys。
   - Public artifacts and result docs do not expose private ids, private maps, selectors, slot override internals, execution payloads, credentials, tokens, cookies, or secrets。

## Documentation Acceptance

1. 11.3.8 docs explain root cause and repair path。
   - `learning_action_label_too_generic`。
   - `business_object_not_preserved`。
   - `execution_action_match_too_literal`。

2. 11.3.8 is not described as site migration。
   - Docs must state that Fixture-Site and Validation-Site separation is already completed。
   - Docs must state that this package fixes runtime chat product capability exposed by external black-box validation。

3. Child iteration requirement is explicit。
   - Any code implementation under 11.3.8.x must first create the complete seven-document package required by `docs/iterations/README.md`。
   - This umbrella package does not replace child `contract.md`、`technical-design.md`、`test-plan.md` or `review.md`。
   - Parent `plan.md` must describe each 11.3.8.x child package using the planned-package fields required by `docs/iterations/AGENTS.md` / `AGENTS.zh.md`。

4. External validation reports remain honest。
   - `PASS`、`FAIL`、`FOLLOW_UP`、`UNVERIFIED` and `BLOCKED` must reflect evidence。
   - A partial fix must not be written as full product capability pass。
   - `PV-CLI-003` cannot be claimed fixed unless implementation and external black-box revalidation actually complete。

## Current Non-Acceptance

At the time this umbrella package is created:

- Runtime code has not been changed.
- Tests have not been changed or run.
- External black-box validation has not been rerun.
- `PV-CLI-003` remains failed in the latest recorded external black-box validation result.
- `external-black-box-validation-latest.md` must remain an honest `FAIL` record until a real revalidation updates it.
