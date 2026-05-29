# 11.3.8 · External Black-box Validation Recovery

状态：ready for review
里程碑：M11
类型：umbrella planning docs
父迭代：[`11.3-interactive-chat-closed-loop`](../11.3-interactive-chat-closed-loop/)
前置事实：
[`external-black-box-validation-latest.md`](../../../testing/results/external-black-box-validation-latest.md)、
[`pv-cli-003-failure-triage-20260525.md`](../../../testing/results/pv-cli-003-failure-triage-20260525.md)

## 迭代定位

`11.3.8 External Black-box Validation Recovery` 是 M11.3 chat runtime /
product validation closure 的收口补强，不是 M12 recovery，也不是测试站点迁移。

## Scope

本包只交付 umbrella planning documentation。它定义外部黑盒验证失败后的修复拆包、
验收要求、验证边界和 child package gates；它不实现代码、不改测试、不执行 live
validation，也不改变任何 runtime contract。

允许改动范围：

- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/*`
- `docs/iterations/m11/README.md` 中的 11.3.8 索引状态
- `docs/iterations/m11/m11-plan.md` 中的 11.3.8 计划状态

禁止改动范围：

- runtime、schema、API、frontend、fixture、migration 或 test implementation files
- `WebAgentFlow-Validation-Site` / `WebAgentFlow-Fixture-Site`
- external black-box latest result，除非后续 child package 真实重验

## Deliverables

- `README.md` - umbrella package index, status, child package sequence, and scope.
- `intent.md` - product problem, why now, non-goals, and success definition.
- `contract.md` - planning, evidence, compatibility, forbidden-change, and handoff contract.
- `technical-design.md` - documentation structure, affected files, anti-drift strategy, and validation shape.
- `test-plan.md` - docs-only verification commands and no-unverified-claims rules.
- `plan.md` - execution-grade planned-package specs for 11.3.8.1 through 11.3.8.5.
- `acceptance.md` - functional, safety, test, and documentation acceptance criteria.
- `review.md` - documentation authoring record, commands run, not-run items, and final assessment.

## Final Assessment State

Ready for documentation review. This status means the umbrella planning package is complete enough to review;
it does not authorize runtime implementation. Child packages must still create their own full seven-document
sets and pass documentation/design review before any code, test, or validation implementation begins.

## Assumptions

- The 2026-05-25 external black-box validation result and PV-CLI-003 triage are the current failure baseline.
- `11.3.8` remains an M11.3 post-closeout recovery follow-up; it does not reopen M11 final closeout or start M12 recovery.
- Future child packages can add repo-local synthetic tests without copying external Validation-Site source, selectors, seed data, or answer keys.
- External revalidation will be run only by a later approved validation child package through an auditable WAgent product surface.

## Open Risks

- `11.3.8.1` now preserves intake business goal metadata in HEAD, but later packages still need to consume it for utterances, matching, regression, and external revalidation.
- A matcher fix could overmatch generic verbs unless negative tests cover different actions, shared objects, and ambiguous candidates.
- Repo-local tests may pass while external product-like validation still fails; `11.3.8.5` must keep the latest result honest.
- External revalidation may be blocked by local services, browser availability, LLM provider availability, or stale database state.

站点迁移已经完成：

- `WebAgentFlow-Fixture-Site` 是外部 deterministic fixture site，通过
  `WAF_FIXTURE_SITE_URL` / `WAF_PAGE_SPEC_ROOT` 供主仓库验证使用。
- `WebAgentFlow-Validation-Site` 是外部 product-like black-box validation target。
- 主仓库已移除 `apps/product-test-site` 和 `apps/validation-site`，外部 Validation-Site
  不作为 workspace、submodule、dependency 或 runtime default。

本包承接 2026-05-25 外部黑盒产品验证的 `FAIL` 结果。它要修复的不是站点归属，而是外部黑盒验证暴露出的 runtime chat 产品能力缺口：

```text
学会一个外部页面操作后，系统应该能用新的参数执行同一业务动作。
```

## 当前失败摘要

`PV-CLI-002 Learn create inventory item`：

- 学习流程通过 `wagent chat` 启动并完成。
- 输入中的业务目标是 `Create inventory item` / `create_inventory_item`。
- 但学习完成后的可复用 action label 变成 `Learn how to create`。
- suggested utterances 也只围绕教学句式生成，例如 `帮我Learn how to create`。
- 结果状态记录为 `FOLLOW_UP`，不能视为完整通过。

`PV-CLI-003 Execute learned create with new values`：

- 用户输入 `Create an inventory item with SKU MUG-SKY-014...`。
- intake 和 router 都识别出执行意图和已学 action context。
- runtime matcher 无法把执行请求绑定到具体 session learned action。
- WAgent 回复“还没学过你要做的这个操作”，没有启动执行，也没有产生可见 execution evidence。
- 结果状态为 `FAIL`。

## 根因摘要

`learning_action_label_too_generic`：

学习阶段 intake 已经识别出 `Create inventory item` 和 `create_inventory_item`，但最终保存到 session learned action 的 alias 退化为 `Learn how to create`。这说明 product-level action label 生成保留了教学包装词，却截断或丢失了真正的业务对象。

`business_object_not_preserved`：

`inventory item`、`create_inventory_item`、别名和 slots 在 intake / router 数据中存在，但没有进入可复用 session action metadata 或 matchable terms。后续执行阶段因此看不到“库存项”这个业务对象，只看到泛化的教学句式。

`execution_action_match_too_literal`：

执行阶段主要比较 user input / intake terms 与 action alias / utterances 的字面或归一化交集。learned action terms 是 `learnhowtocreate`，execute terms 是 `Create inventory item` / `create_inventory_item`，没有重叠，因此 runtime 拒绝执行。拒绝比乱猜更安全，但暴露出匹配语义不足。

## 子迭代拆分

每个子迭代进入代码实现前，必须按仓库规范生成完整七件套：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

本 11.3.8 总包只提供 umbrella plan 和边界，不替代子迭代的 implementation gate。
但父级 `plan.md` 必须按 `docs/iterations/AGENTS.md` / `AGENTS.zh.md` 的 Planned
Package Standard 把每个子迭代写成准迭代包规格，明确 package name、status、type、
required reading、allowed / forbidden changes、expected deliverables、verification、
compatibility constraints、scope guardrails、exit criteria 和 handoff。

### 11.3.8.1 Learning Action Goal Preservation

Goal：让学习完成后的 session learned action metadata 保留 intake 中的业务目标。

Why：当前 learning intake 知道 `Create inventory item`，但可复用 action alias 退化为 `Learn how to create`，导致后续执行无法复用。

Expected output：学习结果优先保存 normalized business goal、canonical goal、business object 和有价值 aliases；教学包装词不再成为主要 action identity。当前 HEAD 已包含该 scoped preservation work，后续包负责消费这些 metadata。

Non-goals：不硬编码 `inventory item`、不硬编码 `5177/inventory`、不读取或复制外部 Validation-Site 源码。

### 11.3.8.2 Suggested Utterance Generation

Goal：生成可复用 utterances，而不是只生成教学句式变体。

Why：`帮我Learn how to create` 无法帮助后续 `Create an inventory item...` 这类自然执行请求命中已学 action。

Expected output：suggested utterances 至少包含业务对象和 normalized business action，例如 `Create inventory item` / `Help me create inventory item`；可以保留轻量中文 wrapper，但不能丢失英文业务对象。

Non-goals：不引入完整多语言翻译系统，不引入 LLM utterance generation 新依赖，不把 slot values 或外部站点字段写死为 action identity。

### 11.3.8.3 Learned Action Matching Improvement

Goal：执行阶段基于 business goal、canonical goal、aliases、business object 等 match terms 匹配已学 action，而不是只靠 literal alias / utterances。

Why：PV-CLI-003 中 router 高层判断已有 learned action context，但 runtime 没有绑定具体 session action。

Expected output：同一业务动作的新参数执行请求能匹配已学 action；低置信度、多候选或仅共享动词的场景必须追问或进入 choice，不能自动猜。

Non-goals：不因为共享 `create` / `open` / `update` 就匹配，不把 eval-only binding 冒充完整 live product capability。

### 11.3.8.4 Regression Tests

Goal：把 PV-CLI-003 的失败模式固化成 automated regression。

Why：只修一次 matcher 容易变成“当前输入能过”，但无法防止未来重新丢失业务对象或过度匹配。

Expected output：覆盖 learning label preservation、suggested utterances、match term normalization、chat runtime action matching、router known-action counting，以及 learn-create-inventory -> execute-new-values 的 synthetic integration-ish path。

Non-goals：不要求 `WebAgentFlow-Validation-Site` 运行，不依赖外部站点源码、selector、`data-testid`、seed copy 或 `5177/inventory`。

### 11.3.8.5 External Black-box Revalidation / Closeout

Goal：修复后重跑外部黑盒验证，证明产品路径改善，并更新 latest result。

Why：unit / integration tests 只能证明语义链路和 matcher 行为，不能替代 product-like black-box validation。

Expected output：至少重跑 `PV-CLI-002`、`PV-CLI-003`、`PV-CLI-004`、`PV-INTEGRITY-001`、`PV-INTEGRITY-002`，新增日期结果并更新 latest report；如果仍然失败，必须如实记录 `FAIL` 或 `FOLLOW_UP`。

Non-goals：不通过直接调用 autonomous-run endpoint、service import、hidden HTTP client 或 direct replay API 伪造产品验证 pass。

## 总体禁止事项

- 不修改 `WebAgentFlow-Validation-Site` 源码。
- 不修改 `WebAgentFlow-Fixture-Site` 源码。
- 不恢复 `apps/product-test-site`。
- 不恢复 `apps/validation-site`。
- 不把 `5177/inventory` 写入 runtime 默认值、prompt answer key、eval default 或 package dependency。
- 不把 selector、`data-testid`、component、seed copy、页面源码、字段标签或内部状态复制进主仓库 runtime / prompt。
- 不把 archived `5176/items` eval 恢复成 active 默认 eval。
- 不通过直接调用 `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream` 来伪造产品验证 `PASS`。
- 不把 direct replay API 或内部 service import 的结果当作 WAgent chat runtime pass evidence。
- 不在后续 matcher 修复中用目标站点 answer key 代替通用业务语义匹配。

## 当前状态

本包是修复计划总包，不是 external black-box 修复结果。`11.3.8.1` 已完成 metadata preservation
scoped work，但 `PV-CLI-003` 尚未通过外部黑盒重验，`external-black-box-validation-latest.md`
仍应保留当前真实 `FAIL` 结论，直到后续子迭代实现、测试和外部黑盒重验完成。
