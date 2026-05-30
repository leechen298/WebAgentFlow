# 实施计划（Plan）

状态：ready for review

## 总体说明

本文件是 `11.3.8 External Black-box Validation Recovery` 的 umbrella plan。它只定义总包拆分、边界、实施顺序和 child package handoff，不直接授权 runtime 代码修改。

本文件按 [`docs/iterations/AGENTS.zh.md`](../../AGENTS.zh.md) 的 Planned Package Standard 编写。每个 `11.3.8.x` child package 都必须先创建自己的完整七件套：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

后续实现 Agent 必须先读对应子迭代的 `contract.md`、已审核 `technical-design.md`、`test-plan.md` 和 `plan.md`，不得只凭本总包直接改 matcher、runtime、tests 或 eval runner。

Codex App `/goal` 执行时还必须先读：

- `GOAL_RUNNER.md`
- `CURRENT_STATE.md`

这两个文件只提供当前路由、checkpoint 和 hard-stop 规则，不替代本 `plan.md`
或任何 child package 的七件套。

## Shared Required Reading

所有 `11.3.8.x` child package 在生成七件套前必须先读：

- `AGENTS.md`
- `CLAUDE.md` 或 `CLAUDE.zh.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `docs/product-model.md`
- `docs/scope-boundaries.md`
- `docs/testing/external-black-box-validation-plan.md`
- `docs/testing/results/external-black-box-validation-20260525.md`
- `docs/testing/results/external-black-box-validation-latest.md`
- `docs/testing/results/pv-cli-003-failure-triage-20260525.md`
- `docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval/README.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/README.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/intent.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/acceptance.md`

## Shared Forbidden Changes

所有 `11.3.8.x` child package 均禁止：

- 修改 `External-Fixture-Provider` 源码。
- 修改 `WebAgentFlow-Fixture-Site` 源码。
- 恢复 `apps/fixture-site`。
- 恢复 `apps/fixture-site`。
- 把 `<fixture-port>/target-page` 写入 runtime default、prompt answer key、eval default、package dependency 或 active automated test hard dependency。
- 把 selector、`data-testid`、component、seed copy、field label、button text、placeholder、operation alias 或 page source 写入 product runtime / prompts。
- 把 archived `<fixture-port>/records` eval 恢复成 active default eval。
- 直接调用 `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream` 作为 product validation evidence。
- 用 direct replay API、internal service import、hidden HTTP client 或 ad hoc script 代替 WAgent chat runtime evidence。
- 把 `FAIL`、`BLOCKED`、`UNVERIFIED` 或 `FOLLOW_UP` 通过措辞改成 `PASS`。
- 在 child package 执行过程中顺手修改 `GOAL_RUNNER.md`，除非用户明确要求维护 Goal Runner 规则。

## Codex Goal Runner Routing

默认 `/goal` 模式为 full campaign mode：按 `CURRENT_STATE.md` 和本 parent plan
一次只处理一个 active child package，但在 child 达到 `PACKAGE_COMPLETE` 后，可以继续
下一个 eligible child package。

每个 child package 后都必须 checkpoint；只有当前包状态为 `PACKAGE_COMPLETE`，
且下一包在 `CURRENT_STATE.md` 或本 plan 中明确 eligible 时，才可继续。若用户明确要求
one child package mode，达到当前 child final status 后必须停止。

`CURRENT_STATE.md` 与 child `review.md`、`technical-design.md`、`plan.md` 或实际 git state 冲突时，必须停为 `NEEDS_USER_INPUT`，不得静默选择其中一个来源。

`FINAL_STATUS` 固定字段用于快速路由：

```text
status:
next_action:
parent_authorizes_runtime_implementation:
active_child_package:
do_not_reimplement:
blocking_findings:
last_verified_at:
commands_run:
commands_not_run:
```

## Planned Packages

### 11.3.8.1 Learning Action Goal Preservation

Package name: `11.3.8.1-learning-action-goal-preservation`

Status: implementation_complete_pending_followup

Type: code

Goal: 让学习完成后的 session learned action metadata 保留 intake 中的业务目标，而不是把教学包装句式保存成可复用 action identity。

Why this exists: PV-CLI-002 的 learning intake 已识别 `Create inventory item` / `create_inventory_item`，但学习完成后 action alias 退化为 `Learn how to create`。后续执行无法命中已学 action 的根因之一是 business goal 在 learning result 到 session action metadata 的链路中丢失。

Inputs / required reading:

- Shared Required Reading。
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/intake.py`
- `apps/api/app/schemas/conversation_intake.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_conversation_intake.py`

Allowed changes:

- Review the implemented child iteration package under `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/`.
- Product-level learning result construction in HEAD can prefer `ConversationIntakeResult.action.goal`, `canonical_goal`, useful aliases, and business object over raw `Learn how to ...` wrappers.
- Session learned action metadata in HEAD preserves reusable business identity.
- Focused unit/service tests for business-goal preservation exist in HEAD.
- Add narrowly scoped docs/review updates inside the child package when review findings require them.

Forbidden changes:

- Do not hardcode `inventory item` as a special case.
- Do not hardcode `<fixture-port>/target-page`.
- Do not modify matcher behavior beyond what is necessary to store richer metadata for later packages.
- Do not change replay execution, reporter wording, or external validation result docs in this package.
- Do not add LLM-generated label dependencies.
- Do not run external black-box validation as part of this package.

Expected deliverables:

- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/README.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/intent.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/contract.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/technical-design.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/test-plan.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/plan.md`
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md`
- Focused implementation in `learning_run_service.py`, `chat_runtime.py`, and internal conversation route handoff.
- Focused tests in `test_learning_run_service.py` and `test_conversation_chat_runtime.py`.

Expected tests / verification:

- Documentation stage:
  - `find docs/iterations/m11/11.3.8.1-learning-action-goal-preservation -maxdepth 1 -type f | sort`
  - `rg -n "Learning Action Goal Preservation|canonical_goal|business_object|match_terms|Forbidden changes|Exit criteria" docs/iterations/m11/11.3.8.1-learning-action-goal-preservation`
- Implementation stage:
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q`
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q`
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_intake.py -q` if intake behavior changes.
- No live external validation is expected in this package.

Compatibility constraints:

- Existing Chinese and generic product-level learning flows must remain compatible.
- Existing LearnedPath persistence schema must not require a migration unless the child contract explicitly proves why it is necessary.
- Existing session action consumers must tolerate any new metadata fields.
- Slot values must remain execution parameters, not reusable action identity.

Scope guardrails:

- This package preserves action identity; it does not solve utterance generation, matching policy, or external revalidation.
- If implementation/code review finds metadata preservation requires broader schema/API changes, stop and update the child contract/design before further code work.
- If current code cannot access intake action data safely at the expected boundary, record that as a blocker rather than guessing from raw text.

Exit criteria:

- Child package docs and committed implementation remain aligned before follow-up packages consume the metadata.
- Focused tests prove `Learn how to create an inventory item...` produces learned action metadata that preserves `Create inventory item` / `create_inventory_item` or equivalent business identity.
- No target-specific runtime or prompt constants are introduced.
- `review.md` records changed files, commands run, not-run live validation, compatibility review, scope review, unresolved findings, and final assessment.

Handoff to next package: `11.3.8.2` may use the preserved business identity as input for reusable suggested utterances after implementation/code review confirms the `11.3.8.1` metadata shape in HEAD. If review finds the metadata shape unstable, `11.3.8.2` must remain blocked.

### 11.3.8.2 Suggested Utterance Generation

Package name: `11.3.8.2-suggested-utterance-generation`

Status: PACKAGE_COMPLETE

Type: code

Goal: 生成可复用 utterances，使用户后续可以用业务动作表达命中已学 action，而不是只得到教学句式变体。

Why this exists: PV-CLI-002 生成的 utterances 是 `帮我Learn how to create` / `Learn how to create 一下`，它们没有保留 `inventory item` 这个业务对象。即使 label preservation 完成，如果 utterances 仍然来自 wrapper，用户提示和 matcher 都会继续缺少可复用语义。

Inputs / required reading:

- Shared Required Reading。
- `11.3.8.1` child package `review.md` and final metadata contract.
- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`

Allowed changes:

- Add a child iteration package under `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/`.
- Generate suggested utterances from canonical business goal, original action goal, useful aliases, and stable business object metadata.
- Keep lightweight existing Chinese wrapper behavior only when it does not drop the business object.
- Add focused tests for reusable utterance output and sensitive-value exclusion.

Forbidden changes:

- Do not introduce an LLM utterance-generation dependency.
- Do not build a full multilingual translation system.
- Do not include record_code, item name, quantity, seed data, selectors, or page-specific labels in reusable utterances.
- Do not change action matching thresholds or execution behavior in this package.
- Do not update external black-box validation result docs.

Expected deliverables:

- Full seven-doc child package under `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/`.
- Focused implementation in `learning_run_service.py` / `chat_runtime.py` if approved by the child design.
- Focused tests for business-object utterances and slot-value exclusion.

Expected tests / verification:

- Documentation stage:
  - `find docs/iterations/m11/11.3.8.2-suggested-utterance-generation -maxdepth 1 -type f | sort`
  - `rg -n "Suggested Utterance Generation|Forbidden changes|slot values|sensitive" docs/iterations/m11/11.3.8.2-suggested-utterance-generation`
- Implementation stage:
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q`
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q`
- No live external validation is expected in this package.

Compatibility constraints:

- Existing public response wording can be improved only within the child contract.
- Existing Chinese product-level test expectations must either remain valid or be intentionally updated with a compatibility note.
- Utterance output must remain deterministic and reviewable.
- Private payloads, slot overrides, and sensitive values must not appear in public suggested utterances.

Scope guardrails:

- This package produces reusable utterances; it does not alter matcher confidence policy.
- If utterance generation needs new persisted fields, the child technical design must describe compatibility and no-migration behavior.
- If useful aliases are absent, fall back to preserved business goal rather than raw `Learn how to ...`.

Exit criteria:

- Child seven-doc package exists and is review-ready before code changes.
- Focused tests prove learned action suggestions include business object terms and exclude slot values.
- Existing relevant Chinese/generic tests remain compatible.
- `review.md` records commands, not-run live validation, compatibility review, scope review, unresolved findings, and final assessment.

Handoff to next package: `11.3.8.3` may use preserved metadata and reusable utterances as match terms. If utterances still lack business-object terms, matching improvement must not proceed by loosening thresholds alone.

### 11.3.8.3 Learned Action Matching Improvement

Package name: `11.3.8.3-learned-action-matching-improvement`

Status: planned after `11.3.8.1` and `11.3.8.2`

Type: code

Goal: 让执行阶段基于 business goal、canonical goal、business object、aliases 和 reusable utterances 匹配已学 action，同时保持低置信度和多候选场景的安全追问。

Why this exists: PV-CLI-003 中 execute intake 和 router 都识别出 `Create inventory item` / `create_inventory_item`，但 runtime `_match_session_action()` 没有绑定具体 learned action。当前 literal alias / utterance intersection 对 wrapper label 过于敏感。

Inputs / required reading:

- Shared Required Reading。
- `11.3.8.1` final metadata contract and review.
- `11.3.8.2` final utterance contract and review.
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/router_agent.py`
- `apps/api/app/services/conversation/intake.py`
- `apps/api/app/schemas/conversation_router.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_conversation_router_agent.py`

Allowed changes:

- Add a child iteration package under `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/`.
- Extend session action matching to compare canonical goal, normalized business goal, business object, aliases, and reusable utterances.
- Preserve or add safety behavior for ambiguous / low-confidence matches.
- Add focused positive and negative matching tests.
- Update router known-action counting only if required to stay aligned with runtime matching terms.

Forbidden changes:

- Do not match solely on shared verbs such as `create`, `open`, `update`, or `delete`.
- Do not auto-execute when multiple learned actions plausibly match.
- Do not bypass `_match_session_action()` or equivalent concrete session action binding.
- Do not call direct replay API as a product pass substitute.
- Do not introduce target-specific answer keys or route constants.
- Do not run external black-box validation as part of this package unless a later child design explicitly changes scope.

Expected deliverables:

- Full seven-doc child package under `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/`.
- Focused matcher implementation in `chat_runtime.py`, and `router_agent.py` only if needed.
- Focused tests in `test_conversation_chat_runtime.py` and `test_conversation_router_agent.py`.

Expected tests / verification:

- Documentation stage:
  - `find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f | sort`
  - `rg -n "Learned Action Matching Improvement|ambiguous|low-confidence|Forbidden changes|Exit criteria" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement`
- Implementation stage:
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q`
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q`
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_intake.py -q` if intake match-term derivation changes.
- No live external validation is expected in this package.

Compatibility constraints:

- Existing known-action and unknown-action behavior must not regress.
- Ambiguous matches must remain choice / clarification, not silent execution.
- Unknown-page cases must not be contaminated by global old LearnedPath state.
- Private ids, private maps, slot overrides, and execution payloads must not leak into public responses or committed artifacts.

Scope guardrails:

- Matching improvement must consume metadata from 11.3.8.1 / 11.3.8.2, not compensate for missing metadata with broad fuzzy matching.
- If a proposed matcher change would alter planner-backed choice behavior, the child design must include explicit regression coverage.
- If confidence cannot be determined, choose clarification over execution.

Exit criteria:

- Child seven-doc package exists and is review-ready before code changes.
- Tests prove:
  - learn `Create inventory item` -> execute `Create inventory item with new values` matches.
  - learn `Create inventory item` -> execute `Search inventory item` does not direct-match.
  - multiple plausible actions require choice.
  - generic `Create` does not overmatch richer business-object requests.
- `review.md` records commands, not-run live validation, compatibility review, scope review, unresolved findings, and final assessment.

Handoff to next package: `11.3.8.4` may combine the preserved metadata, utterance generation, and matcher behavior into an integration-ish regression. If matching still relies on target-specific constants, 11.3.8.4 must block rather than encode those constants.

### 11.3.8.4 Regression Tests

Package name: `11.3.8.4-regression-tests`

Status: planned after `11.3.8.1` through `11.3.8.3`

Type: code

Goal: 把 PV-CLI-003 的失败模式固化成 automated regression，覆盖 learn-create-inventory -> execute-new-values 的语义链路，同时不依赖外部站点运行或源码。

Why this exists: 11.3.8.1-11.3.8.3 的单点 tests 不能替代一个跨 learning output、session action metadata、matcher 和 replay handoff 的回归。这个包把外部黑盒失败抽象成 target-agnostic automated regression，防止后续再次丢失业务对象或过度匹配。

Inputs / required reading:

- Shared Required Reading。
- `11.3.8.1` / `11.3.8.2` / `11.3.8.3` final reviews.
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_conversation_router_agent.py`
- Existing fake replay handler / session action helper patterns in nearby conversation tests.

Allowed changes:

- Add a child iteration package under `docs/iterations/m11/11.3.8.4-regression-tests/`.
- Add focused automated regression tests that use synthetic URLs and fake replay handlers.
- Add helper cleanup only when it reduces duplication and does not change runtime behavior.
- Update test documentation and child `review.md`.

Forbidden changes:

- Do not require `External-Fixture-Provider` to run.
- Do not include `<fixture-port>/target-page` as a hard dependency.
- Do not use external site selector, `data-testid`, component, seed copy, or page source.
- Do not restore archived `<fixture-port>/records` eval as active default.
- Do not modify runtime code in this package unless a missing test seam is explicitly approved in the child technical design.
- Do not run live external validation in this package.

Expected deliverables:

- Full seven-doc child package under `docs/iterations/m11/11.3.8.4-regression-tests/`.
- Focused tests in `test_learning_run_service.py`, `test_conversation_chat_runtime.py`, and/or `test_conversation_router_agent.py`.
- Optional reusable test helper updates if approved by child design.

Expected tests / verification:

- Documentation stage:
  - `find docs/iterations/m11/11.3.8.4-regression-tests -maxdepth 1 -type f | sort`
  - `rg -n "Regression Tests|external site|synthetic|Forbidden changes|Exit criteria" docs/iterations/m11/11.3.8.4-regression-tests`
- Implementation stage:
  - `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q`
  - `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest <child-target-manifest-if-created> --root /Users/leechen/projects/WebAgentFlow/v0.1` if the child package creates a target manifest.
- No live external validation is expected in this package.

Compatibility constraints:

- Tests must be target-agnostic and repo-local.
- Existing behavior tests for unknown / vague / choice cases must remain meaningful.
- Test fixtures must avoid private payload leakage and hardcoded external-site answer keys.
- New helper abstractions must not obscure evidence boundaries.

Scope guardrails:

- This package proves non-live regression coverage only; it cannot mark external black-box validation as pass.
- If tests require product services or browser operation, split that into 11.3.8.5 instead.
- If a test needs external site semantics, rewrite it as synthetic business-object semantics or block.

Exit criteria:

- Child seven-doc package exists and is review-ready before test changes.
- Focused regression tests pass and fail for the right reason before implementation where applicable.
- No external site source / selector / route dependency appears in active runtime or tests.
- `review.md` records commands, not-run live validation, compatibility review, scope review, unresolved findings, and final assessment.

Handoff to next package: `11.3.8.5` may perform external black-box revalidation only after non-live regression coverage is in place. If regression tests are missing or target-coupled, revalidation must be blocked.

### 11.3.8.5 External Black-box Revalidation / Closeout

Package name: `11.3.8.5-external-black-box-revalidation-closeout`

Status: planned after `11.3.8.4`

Type: mixed

Goal: 修复后重跑外部黑盒验证，证明 product-like path 是否改善，并如实更新 result docs 和 closeout 状态。

Why this exists: Unit / service / integration-ish tests 只能证明 repo-local behavior。M11.3.8 的产品目标来自外部黑盒验证失败，最终必须通过 approved WAgent product surface 重新验证，并保留可复核 evidence。若仍失败，必须继续记录 `FAIL` / `FOLLOW_UP` / `UNVERIFIED`，不能用文案改成 pass。

Inputs / required reading:

- Shared Required Reading。
- Final reviews for `11.3.8.1` through `11.3.8.4`.
- `docs/testing/external-black-box-validation-plan.md`
- `docs/testing/results/external-black-box-validation-latest.md`
- `docs/testing/results/pv-cli-003-failure-triage-20260525.md`
- `.agents/skills/webagentflow-eval-integrity/SKILL.md`
- `apps/cli/wagent/chat.py`
- `package.json` eval scripts, especially `eval:wagent:user-behavior` for boundary comparison.

Allowed changes:

- Add a child iteration package under `docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout/`.
- Run external black-box validation through approved WAgent CLI / product surface when services are available and the user has approved or requested the live validation.
- Update `docs/testing/results/external-black-box-validation-YYYYMMDD.md`.
- Update `docs/testing/results/external-black-box-validation-latest.md` only with actual current-session evidence.
- Add redacted review / closeout notes in the child package.
- Run integrity scans and artifact redaction checks.

Forbidden changes:

- Do not modify runtime code or tests in this package except for explicitly scoped observability fixes approved by the child contract.
- Do not call `/exploration/autonomous-runs` or `/exploration/autonomous-runs/stream` directly.
- Do not use service imports, hidden HTTP clients, or direct replay API as WAgent pass evidence.
- Do not mark `PV-CLI-003` pass unless execution starts for the matching learned action and the evidence supports the gate.
- Do not hide manual smoke limitations or DB-state caveats.

Expected deliverables:

- Full seven-doc child package under `docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout/`.
- New dated external black-box validation result if validation runs:
  `docs/testing/results/external-black-box-validation-YYYYMMDD.md`.
- Updated latest result only if validation runs:
  `docs/testing/results/external-black-box-validation-latest.md`.
- Child `review.md` with operator surface, commands, result status, not-run items, integrity checks, and final assessment.

Expected tests / verification:

- Documentation stage:
  - `find docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout -maxdepth 1 -type f | sort`
  - `rg -n "External Black-box Revalidation|operator surface|PASS|FAIL|FOLLOW_UP|UNVERIFIED|Forbidden changes" docs/iterations/m11/11.3.8.5-external-black-box-revalidation-closeout`
- Pre-live checks when validation is approved:
  - `git status --short --branch`
  - `curl -i http://127.0.0.1:8001/health`
  - `curl -i http://127.0.0.1:<fixture-port>/target-page`
  - forbidden-target scan using a child-owned or temp manifest for Fixture-Site answer keys.
- Product validation surface:
  - `.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300 --headless`
  - Required scenarios: `PV-CLI-002`, `PV-CLI-003`, `PV-CLI-004`, `PV-INTEGRITY-001`, `PV-INTEGRITY-002`.
  - Optional scenarios: `PV-SITE-001`, `PV-CLI-001`.
- Report integrity:
  - redaction scan for public result artifacts if artifacts are generated.

Compatibility constraints:

- Validation must preserve external-site separation: the target URL remains operator-provided, not a runtime default.
- Existing 11.3.6 / 11.3.7 results remain historical evidence and must not be rewritten as 11.3.8 pass evidence.
- Old DB state must be either cleaned or explicitly documented.
- `pass_gate` / eval status vocabulary must follow evidence: `PASS`, `FAIL`, `FOLLOW_UP`, `BLOCKED`, or `UNVERIFIED`.

Scope guardrails:

- This package validates and closes out; it does not invent new runtime recovery behavior.
- Before live validation, explicit approval must include API base URL, target URL,
  whether DB state has been cleaned or intentionally preserved, approved
  scenario list, and whether latest result docs may be updated after actual
  evidence.
- If live services are unavailable, record `BLOCKED` or `not_run` rather than simulating pass.
- If PV-CLI-003 still fails, keep latest report failed and hand off a new follow-up; do not widen into unplanned matcher fixes inside closeout.
- If integrity scan fails, stop and treat the package as blocked until target-specific leakage is removed or explicitly recorded.

Exit criteria:

- Child seven-doc package exists and is review-ready before validation.
- Required rerun outcomes are recorded with operator surface and evidence.
- `external-black-box-validation-latest.md` is updated only after actual revalidation.
- Integrity scan and redaction checks are recorded.
- `review.md` records commands, results, compatibility review, scope review, unresolved findings, and final assessment.

Handoff to next package: If all required gates pass, hand off to M11.3 / M11 runtime status sync. If any required gate fails, hand off to a new narrowly scoped follow-up package under the appropriate milestone; do not silently roll the failure into M12 recovery unless the product model and roadmap are updated.

## 实施顺序

1. Review `11.3.8.1-learning-action-goal-preservation` 的已提交 goal preservation implementation 和文档记录。
2. 生成并审核 `11.3.8.2-suggested-utterance-generation` 七件套，再实现 reusable utterances。
3. 生成并审核 `11.3.8.3-learned-action-matching-improvement` 七件套，再实现 safe matching。
4. 生成并审核 `11.3.8.4-regression-tests` 七件套，再补非 live 回归。
5. 生成并审核 `11.3.8.5-external-black-box-revalidation-closeout` 七件套，再执行外部黑盒重验和 closeout。

Stop conditions:

- 子包缺少七件套或缺少 reviewed technical design。
- 子包缺少 required planned-package 字段。
- `CURRENT_STATE.md` 与 child package review / technical design / plan 或实际 git state 冲突。
- 设计需要修改 product model、Agent role、milestone boundary 或 live-run evidence semantics。
- 实现需要引入 target-specific route、selector、seed、answer key 或 direct endpoint validation。
- 当前证据不足以支撑 `PASS`。
- `11.3.8.5` 需要 live validation，但当前线程没有提供 API base URL、target URL、DB state policy、approved scenario list 和 latest-result update approval。

Review update step:

- 每个 child package 必须在 `review.md` 记录 changed files、commands run、test results、compatibility review、scope review、unresolved P1/P2/P3、final assessment。
- 没有真实运行的命令必须写成 `not run` / `not executed` / `blocked`，不得写成 passed。
