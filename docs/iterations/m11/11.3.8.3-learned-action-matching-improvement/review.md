# 复盘 / 评审（Review）

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
next_action: create and review 11.3.8.4-regression-tests seven-document package
parent_authorizes_runtime_implementation: no
active_child_package: 11.3.8.3-learned-action-matching-improvement
implementation_authorized: yes
do_not_reimplement: true
blocking_findings: none
last_verified_at: 2026-05-29 implementation closeout
commands_run: documentation checks; TDD red focused pytest; focused chat runtime pytest; focused router pytest; focused ruff; forbidden target scan; git diff --check; git status --short; git diff --name-only; read-only design/safety/code/evidence subagent reviews and re-reviews
commands_not_run: live external validation; wagent chat live validation; verify-scenario; browser smoke; direct autonomous-run endpoint; external black-box result docs update

## 2026-05-29 Implementation Closeout

- Author: Codex.
- Decision: `PACKAGE_COMPLETE` for `11.3.8.3-learned-action-matching-improvement`.
- Scope: implemented current-session learned action matching consumption of
  `business_goal`, `canonical_goal`, `action_aliases`, `business_object`,
  `match_terms`, and reusable `utterances`; synchronized router known-action
  counting; added focused runtime and router tests.
- Product-evidence boundary: this is repo-local matcher evidence only. It does
  not prove `PV-CLI-003`, does not update external black-box latest reports, and
  does not run live `wagent chat`, `verify-scenario`, browser smoke, or
  autonomous-run endpoints.

### Implementation Changed Files

- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/router_agent.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_conversation_router_agent.py`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/README.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/intent.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/contract.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/technical-design.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/test-plan.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/plan.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/review.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/CURRENT_STATE.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/review.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`

### Runtime / Router Changes

- `chat_runtime.py` now builds action-side matcher terms from `utterances`,
  `alias`, `business_goal`, `canonical_goal`, `action_aliases`,
  `business_object`, and `match_terms`.
- Generic verb-only and object-only terms are weak terms and do not direct-match
  richer requests.
- Object + verb compatibility uses token-sequence boundaries, so `order` does
  not match `border` by substring.
- Multiple plausible business-identity matches continue through the existing
  pending-choice path.
- `router_agent.py` mirrors the target-agnostic term counting so router
  `known_context.has_learned_action` aligns with runtime matching without
  authorizing replay or exposing `learned_path_id`.

### TDD Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q -k "business_identity_when_alias_is_wrapper or different_action_on_same_object or business_identity_ambiguity_requires_choice or generic_verb_only_action_does_not_overmatch"` | Positive matcher-consumption and generic guard fail before implementation | `3 failed, 2 passed, 89 deselected` after narrowing no-path allowed assertion to behavior | 1 | Expected red | terminal output | Positive metadata match, ambiguity, and generic verb-only guard failed against old matcher |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q -k "business_identity_metadata"` | Router metadata count fails before router sync | `1 failed, 10 deselected` | 1 | Expected red | terminal output | Router did not count action-side business identity |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q -k "object_phrase_does_not_match_substring_object or different_action_on_same_object_as_learned or generic_verb_only_action_as_learned"` | Object-boundary regression fails before boundary fix | `2 failed, 3 passed, 105 deselected` | 1 | Expected red | terminal output | `order` incorrectly matched `border` by substring before token-boundary fix |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q -k "object_phrase_does_not_match_substring_object or different_action_on_same_object_as_learned or generic_verb_only_action_as_learned or business_identity_when_alias_is_wrapper or business_identity_ambiguity_requires_choice"` | Targeted red cases pass after implementation and P2 fix | `7 passed, 103 deselected` | 0 | Pass | terminal output | Targeted green |

### Verification Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f \| sort` | Seven child docs listed | Listed all seven child docs | 0 | Pass | terminal output | Package existence |
| `rg -n "Learned Action Matching Improvement\|implementation_authorized\|ambiguous\|low-confidence\|Forbidden Changes\|Exit Criteria\|Out-of-scope Follow-ups" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement` | Required terms present | Required terms found | 0 | Pass | terminal output | Documentation term check |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q` | Focused chat runtime tests pass | `95 passed in 0.79s` | 0 | Pass | terminal output | Runtime matcher and compatibility coverage |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q` | Focused router tests pass | `15 passed in 0.07s` | 0 | Pass | terminal output | Router known-action counting coverage |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py -q` | Combined focused suite passes | `110 passed in 0.77s` | 0 | Pass | terminal output | Combined focused regression |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/router_agent.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py` | Ruff passes | `All checks passed!` | 0 | Pass | terminal output | Focused lint |
| `rg -n "<fixture-port>\|/target-page\|inventory item\|External-Fixture-Provider" apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/router_agent.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py` | No target constants in touched runtime/tests | No output | 1 | Pass | terminal output | Minimum target-token scan |
| `git diff --check` | No whitespace errors | Clean | 0 | Pass | terminal output | Patch sanity |
| `git diff --name-only` | Only in-scope files listed | Runtime, router, focused tests, child docs, and parent routing docs listed | 0 | Pass | terminal output | Scope check |
| `git status --short` | Only in-scope files dirty/untracked | Runtime, router, focused tests, child docs, and parent routing docs listed | 0 | Pass | terminal output | Scope check |

### Implementation Subagent Review

- Code / test reviewer: Mendel (`019e73c2-a501-75a3-8e0a-8e29c58340a3`).
  - Initial decision: `CHANGES_REQUESTED`.
  - P2: router coverage only had positive metadata count. Response: added
    router same-object search / delete negative coverage and generic verb-only
    negative coverage.
  - P2: object containment used substring matching. Response: added runtime and
    router `order` / `border` tests and changed object matching to token
    sequence boundaries.
  - Re-review decision: `APPROVE`; no remaining P0 / P1 / P2.
- Evidence / scope reviewer: Lovelace (`019e73c2-ce6f-7e70-b21a-2ddc1424aeab`).
  - Decision: `APPROVE`; no P0 / P1 / P2 / P3 evidence-boundary or scope
    violations.
  - Required caveat recorded: repo-local matcher tests passed; live external
    validation, `wagent chat`, `verify-scenario`, browser smoke,
    autonomous-run endpoint, direct replay product validation, and external
    latest result docs update were not run / not modified. `PV-CLI-003` remains
    unverified until `11.3.8.5`.

### Commands Not Run / Not Modified

| Item | Status | Reason |
|---|---|---|
| live external black-box validation | not run | Owned by `11.3.8.5` and requires explicit approval fields |
| `wagent chat` live product validation | not run | This package is repo-local matcher implementation only |
| `verify-scenario` / autonomous run | not run | Repository boundary prohibits casual live runs |
| browser / UI smoke | not run | No UI change |
| direct autonomous-run endpoint | not run | Forbidden by repository execution boundary |
| direct replay API product validation | not run | Not valid WAgent product evidence for this package |
| external black-box latest result docs | not modified | Owned by `11.3.8.5` after actual evidence |

### Compatibility / Scope Review

- Existing alias / utterance matching remains covered by the focused chat runtime
  suite.
- Same business action with new values now matches through action-side business
  identity metadata.
- Search / delete on the same business object does not direct-match a create
  learned action.
- Multiple plausible matches enter pending choice.
- Generic verb-only actions do not overmatch richer business-object requests.
- No external site source, fixture source, eval-runner, replay execution,
  reporter, recovery, abort, frontend, worker, DB migration, or public API files
  were modified.

### Unresolved Findings

- P0: None.
- P1: None.
- P2: None after code/test re-review.
- P3: None blocking package closeout.

### Handoff

`11.3.8.4-regression-tests` is the next eligible child package. It must create
and review its own seven-document package before implementation. It may consume
the 11.3.8.1 metadata contract, 11.3.8.2 reusable utterances, and this package's
matcher behavior. It must not run live external validation; that remains owned
by `11.3.8.5` after explicit approval.

## 2026-05-29 Documentation Authoring

- Author: Codex.
- Decision: created the seven-document child package for read-only design review.
- Scope: documentation only. No runtime, schema, API, frontend, fixture, migration,
  worker, eval-runner, replay, reporter, recovery, abort, external validation result,
  or external site source files were modified during documentation authoring.

### Documentation Changed Files

- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/README.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/intent.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/contract.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/technical-design.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/test-plan.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/plan.md`
- `docs/iterations/m11/11.3.8.3-learned-action-matching-improvement/review.md`

### Subagent Plan

Design review subagents to launch before implementation:

- Spec / contract reviewer: check child docs against parent plan, 11.3.8.1 metadata contract,
  and 11.3.8.2 utterance contract.
- Safety / evidence reviewer: check forbidden target constants, live-run boundaries,
  direct replay / autonomous-run prohibitions, and evidence vocabulary.

Implementation closeout subagents to launch after code and focused tests:

- Code / test reviewer.
- Evidence / scope reviewer.

### Design Review

- Spec / contract reviewer: Wegener (`019e73b0-8944-7520-bc59-8d88aff69be9`).
- Safety / evidence reviewer: Pasteur (`019e73b0-b539-7871-b9a3-e0f9675f672a`).
- Initial spec / contract decision: changes requested.
- Spec / contract re-review decision: approved; implementation_authorized justified from spec / contract perspective.
- Safety / evidence decision: approved.
- Safety / evidence re-review decision: approved; implementation_authorized justified from safety / evidence perspective.

Finding responses:

| Finding | Priority | Response | Status |
|---|---|---|---|
| Authorization boundary said the current user request could proceed through implementation before review recorded authorization | P1 | Reworded README to say implementation may proceed only after read-only design review has no unresolved P0 / P1 and `review.md` records `implementation_authorized: yes` | Addressed; spec re-review approved |
| Parent / milestone routing still described 11.3.8.3 as not yet created | P2 | Updated parent `CURRENT_STATE.md`, parent review, M11 README, and M11 plan to route `11.3.8.3` as the active design-review child | Addressed; spec re-review approved |
| Child `plan.md` still implied implementation could follow `create-review-seven-doc-package` solely because the user requested full campaign implementation | P1 | Reworded `plan.md` route text so implementation is allowed only after read-only design / safety review has no unresolved P0 / P1 and child `review.md` records `implementation_authorized: yes` | Addressed; spec re-review approved |
| `contract.md` missing `Out-of-scope Follow-ups` | P2 | Added explicit follow-up section for 11.3.8.4, 11.3.8.5, and out-of-scope runtime areas | Addressed; spec re-review approved |
| Required docs term check could match command text instead of a real Exit Criteria section | P3 | Added explicit `Exit Criteria` sections and tightened test-plan wording | Addressed; spec re-review approved |
| Red / green requirement overstated negative tests that may already pass today | P3 | Reworded positive matcher-consumption tests as required red; negative / ambiguity / generic guards may be recorded as red failures or already-green baselines | Addressed; spec re-review approved |
| Target scan should make clear it is only a minimum scan | P3 | Added reviewer inspection requirement for selectors, field labels, button text, placeholders, seed copy, operation aliases, page source, and Fixture-Site answer keys | Addressed; safety re-review approved |

### Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f \| sort` | Seven child docs listed | Listed all seven child docs with directory-prefixed paths | 0 | Pass | terminal output | Documentation package existence |
| `rg -n "Learned Action Matching Improvement\|implementation_authorized\|ambiguous\|low-confidence\|Forbidden Changes\|Exit Criteria\|Out-of-scope Follow-ups" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement` | Required terms present | Required terms found | 0 | Pass | terminal output | Documentation content check |
| read-only spec / contract subagent review | No unresolved P0 / P1 before implementation | Initial review requested changes; re-review approved | N/A | Pass | subagent output | No live validation run |
| read-only safety / evidence subagent review | No unresolved P0 / P1 before implementation | Initial review approved; re-review approved | N/A | Pass | subagent output | No live validation run |
| `git diff --check` | No whitespace errors | Clean | 0 | Pass | terminal output | Patch sanity |

### Not Run / Unverified

| Item | Reason | Risk / Follow-up |
|---|---|---|
| runtime tests | implementation not authorized yet | run after design review and TDD implementation |
| `wagent chat` live product validation | owned by later validation package | not product pass evidence |
| `verify-scenario` / autonomous run | not authorized for this package | not run |
| browser / UI smoke | no UI change | not run |
| external black-box validation | owned by `11.3.8.5` | latest result remains `FAIL` |

### Compatibility Review

Design review compatibility posture:

- no public API / DB / frontend change;
- old alias / utterance matching remains valid;
- existing ambiguity / choice / no-path behavior remains valid.

### Scope Review

Design review scope:

- matcher consumption only;
- no external site source;
- no target-specific constants;
- no live validation.

### Unresolved Findings

- P0: None.
- P1: None.
- P2: None.
- P3: None after design re-review.
