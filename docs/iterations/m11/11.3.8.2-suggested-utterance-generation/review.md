# 复盘 / 评审（Review）

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
next_action: stop the original 11.3.8.2 goal; parent CURRENT_STATE owns later 11.3.8.3 routing
parent_authorizes_runtime_implementation: no
active_child_package: 11.3.8.2-suggested-utterance-generation
implementation_authorized: yes
do_not_start_next_package: true
blocking_findings: none
last_verified_at: 2026-05-29 17:59 CST
commands_run: documentation checks; read-only spec/design review; TDD red tests; focused pytest; focused ruff; target-constant scan; git diff --check; read-only code/test/evidence review and code re-review
commands_not_run: live external validation; wagent chat live validation; verify-scenario; browser smoke; direct autonomous-run endpoint; external black-box result docs update

## 2026-05-29 Documentation Authoring

- Author: Codex.
- Decision: ready_for_design_review, later approved for implementation.
- Scope: created the full seven-document child package for `11.3.8.2`.
- Runtime, schema, API, frontend, fixture, migration, worker, eval-runner,
  matcher policy, replay, reporter, external Validation-Site, Fixture-Site,
  and external black-box result docs were not modified during documentation authoring.

### Documentation Changed Files

- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/README.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/intent.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/contract.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/technical-design.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/test-plan.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/plan.md`
- `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/review.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`

Pre-existing modified file preserved but not edited by this child closeout:

- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/GOAL_RUNNER.md`

### Design Review

- Reviewer: Confucius (`019e731a-e735-7d02-ace0-b75ac81216ea`) and Hooke (`019e731b-08d4-7fd0-9b52-5bebfe30a5ae`).
- Decision: approved after P1 design revision.
- implementation_authorized: yes.
- Notes:
  - Confucius found no P0/P1 and said implementation could be authorized from spec perspective, with P2/P3 cleanup suggestions.
  - Hooke found P1: design/test-plan did not explicitly cover stale truncated-label wrappers such as `帮我Create purchase orde` / `Create purchase orde一下`.
  - Hooke found P2: verb-only aliases were forbidden in design but not TDD-pinned.
  - Both reviewers noted D1 expected output did not match the `find` command's path-prefixed output.

### Design Review Finding Response

| Finding | Priority | Response | Status |
|---|---|---|---|
| Parent closeout docs not explicitly included in allowed changes | P2 | Added parent `CURRENT_STATE.md` and parent `review.md` to allowed closeout docs when required by `GOAL_RUNNER.md` | Addressed |
| Stale truncated-label wrappers not covered | P1 | Added technical design and test-plan rules for `帮我Create purchase orde` / `Create purchase orde一下` repair | Addressed |
| Verb-only aliases not TDD-pinned | P2 | Added negative alias test requirement and contract exclusion rule | Addressed |
| D1 expected output used bare filenames | P3 | Updated expected output to include directory-prefixed paths | Addressed |

### Design Re-review

- Reviewer: Hooke (`019e731b-08d4-7fd0-9b52-5bebfe30a5ae`).
- Decision: approved.
- implementation_authorized: yes.
- Notes: no remaining P0/P1 blockers. The reviewer confirmed the docs now cover stale truncated-label wrappers and TDD-pin verb-only alias exclusion. The reviewer did not edit files and did not run live validation.

## 2026-05-29 Implementation

### Actual Delivery

- Added deterministic product-level suggested utterance generation in `learning_run_service.py`.
- Generated English reusable utterances from full business identity rather than truncated `action_label`.
- Preserved existing login and Chinese utterance compatibility.
- Excluded verb-only aliases such as `create` from reusable utterances.
- Updated chat runtime learned-action storage to repair empty / stale learning-wrapper / truncated-label utterances from business identity.
- Filtered existing handler-provided utterances so slot values are not stored when no clean identity utterance can be generated.
- Preserved existing clean business utterances and appended deterministic generated utterances.
- Added focused service/runtime tests for business-object utterances, slot-value exclusion, stale wrapper repair, truncated wrapper repair, verb-only alias exclusion, and clean utterance preservation.

### Implementation Changed Files

- `apps/api/app/services/learning/learning_run_service.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/tests/test_learning_run_service.py`
- `apps/api/tests/test_conversation_chat_runtime.py`

### Relative Deviations

- None from the approved child contract/design/test-plan.
- `_matching_actions()` policy was not changed.
- No external validation result docs were modified.

### TDD Red Evidence

| Command | Expected failure | Actual failure summary | Exit code |
|---|---|---|---:|
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py::test_product_learning_preserves_structured_business_identity -q` | Existing service returns wrapper / truncated utterances | Failed: got `帮我Create purchase orde` / `Create purchase orde一下` instead of full business utterances | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py::test_product_learning_uses_clean_canonical_when_action_goal_contains_slot_value -q` | Existing service returns wrapper / truncated utterances | Failed: got `帮我create purchase orde` / `create purchase orde一下` instead of clean canonical utterances | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py::test_product_learning_excludes_verb_only_alias_from_suggested_utterances -q` | Existing service does not generate requested reusable utterances | Failed: got truncated wrapper utterances and omitted `submit purchase order` | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py::test_product_learning_stores_business_identity_from_intake -q` | Existing chat runtime stores stale wrapper utterance | Failed: got `帮我Learn how to create` instead of business utterances | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py::test_product_learning_repairs_truncated_wrapper_utterances_from_identity -q` | Existing chat runtime stores truncated wrapper utterances | Failed after test narrowing: got `帮我Create purchase orde` / `Create purchase orde一下` | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py::test_product_learning_filters_slot_values_when_identity_utterance_generation_absent -q` | Existing fallback stores slot value in utterance | Failed: got `帮我创建 Alpha-1` instead of an empty safe utterance list | 1 |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py::test_product_learning_preserves_existing_clean_business_utterances -q` | Existing helper drops clean handler utterance | Failed: got generated utterances without `Submit purchase order` | 1 |

### Code / Test / Evidence Review

- Code/test reviewer: Dewey (`019e7325-03b0-7372-bb86-ed84a349391a`).
- Evidence/scope reviewer: Curie (`019e7325-274b-7d40-b11b-e335b172c8ec`).
- Initial decision: changes requested.
- Final code/test re-review: approved; no remaining P0/P1/P2 findings.
- Final evidence/scope re-review: approved; no remaining P0/P1/P2 findings.

Finding responses:

| Finding | Priority | Response | Status |
|---|---|---|---|
| Existing utterance fallback stored unfiltered slot / sensitive values when identity generation was empty | P1 | Added filtering for existing utterances and test `test_product_learning_filters_slot_values_when_identity_utterance_generation_absent` | Addressed; re-review approved |
| Existing clean business utterances were discarded when generated identity utterances existed | P2 | Preserved filtered clean existing utterances before appending generated utterances; added test `test_product_learning_preserves_existing_clean_business_utterances` | Addressed; re-review approved |
| Child review was stale against implementation state | P1/P2 | Updated this `review.md` with changed files, red/green evidence, commands, scope, compatibility, and final status | Addressed in closeout |
| `GOAL_RUNNER.md` current default route still mentions `11.3.8.1` while `CURRENT_STATE.md` selects `11.3.8.2` | P3 | Not changed in this child package because parent plan forbids Goal Runner maintenance during child execution unless explicitly requested; `CURRENT_STATE.md` remains the routing source | Accepted as non-blocking |

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `find docs/iterations/m11/11.3.8.2-suggested-utterance-generation -maxdepth 1 -type f \| sort` | Seven child docs listed | Listed all seven child docs with directory-prefixed paths | 0 | Pass | terminal output | Documentation package existence |
| `rg -n "Suggested Utterance Generation\|implementation_authorized\|slot values\|sensitive\|external black-box" docs/iterations/m11/11.3.8.2-suggested-utterance-generation` | Required terms present | Required terms found | 0 | Pass | terminal output | Documentation content check |
| read-only spec/design subagent review | No P0/P1 blockers before implementation | Initial review found one P1; docs revised; re-review found no remaining P0/P1 | N/A | Pass | subagent output | No live validation run |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q` | Focused learning service tests pass | `11 passed in 0.09s` | 0 | Pass | terminal output | Includes new business utterance and verb-only alias tests |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q` | Focused chat runtime tests pass | `89 passed in 0.80s` | 0 | Pass | terminal output | Includes stale wrapper, truncated wrapper, slot filtering, preservation tests |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py` | Focused lint passes | `All checks passed!` | 0 | Pass | terminal output | Focused touched files |
| `rg -n "5177\|/inventory\|inventory item\|WebAgentFlow-Validation-Site" apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py` | No target constants in touched runtime/tests | No output | 1 | Pass | terminal output | `rg` exit 1 means no matches |
| `git diff --check` | No whitespace errors | Clean | 0 | Pass | terminal output | Patch sanity |
| read-only code/test/evidence subagent review | No unresolved P0/P1 after fixes | Code/test re-review approved; evidence/scope re-review approved with P3 routing-text caveat | N/A | Pass | subagent output + this review | No live validation run |

## Not Run / Unverified

| Item | Reason | Risk / Follow-up |
|---|---|---|
| live external black-box validation | Owned by `11.3.8.5`; user explicitly prohibited it in this goal | Latest result remains `FAIL` |
| `wagent chat` live product validation | This package is deterministic utterance generation only | Not product pass evidence |
| `verify-scenario` / autonomous run | Not authorized for this package | Not run |
| direct autonomous-run endpoint | Prohibited by repository boundary | Not run |
| browser / UI smoke | No UI change | Not run |
| external black-box result docs update | User explicitly prohibited it | Not modified |

## Compatibility Review

- No public API endpoint changed.
- No DB migration changed.
- Existing login utterances remain `帮我登录` / `登录一下`.
- Existing Chinese product-level `创建记录` utterances remain compatible.
- Existing session actions without business identity fields remain valid; unsafe existing utterances containing slot values are filtered when no clean identity generation is available.
- `_matching_actions()` was not changed; any execution-match improvement remains for `11.3.8.3`.
- No replay, reporter, recovery, abort, worker, frontend, fixture, or eval-runner behavior changed.

## Scope Review

- Scope stayed inside deterministic suggested utterance generation and focused tests.
- No LLM utterance-generation dependency was introduced.
- No full multilingual translation system was introduced.
- No target-specific route, selector, seed data, field label, button text, placeholder, operation alias, page source, or Validation-Site answer key was added to runtime/tests.
- No `docs/testing/results/external-black-box-validation-*` file was modified.
- No `11.3.8.3` files were created or modified.

## Unresolved Findings

- P0: None.
- P1: None.
- P2: None.
- P3: Parent `GOAL_RUNNER.md` has a stale current-default-route note for `11.3.8.1`; not changed here because child execution is not Goal Runner maintenance. `CURRENT_STATE.md` is the routing source for the next goal.

## Final Assessment

`11.3.8.2-suggested-utterance-generation` is `PACKAGE_COMPLETE`.

Stop this goal here. The next eligible action is a separate goal to create /
review `11.3.8.3-learned-action-matching-improvement`, unless a later parent
Campaign Goal Runner update explicitly enables full campaign routing from the
parent `CURRENT_STATE.md`.
