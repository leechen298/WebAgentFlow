# Review

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
parent_package: 11.3.12-bounded-learning-composable-capability-assets
active_child_package: 11.3.12.4-capability-composition-runtime
implementation_authorized: yes
do_not_start_next_package: false
blocking_findings: none
last_verified_at: 2026-06-06
commands_run: source inspection; document generation; read-only design review; document static checks; scoped pytest; scoped ruff; hardcoding scan; read-only code review / re-review
commands_not_run: migration, live validation, `verify-scenario`, `wagent chat`
next_action: Do not extend this child. Parent campaign is responsible for final closeout and any future validation route.

## 2026-06-06 Code Review Handoff Fixes

- Fixed P1 page-scope fail-closed semantics: `CapabilityCompositionRequest` now carries
  `query_signature`; candidates and preferred LearnedPath reuse must match page template,
  query signature, and current DOM fingerprint when the policy requires DOM matching.
  Missing current DOM fingerprint now fails closed instead of skipping the check.
- Fixed P1 operation compatibility: composer now validates executable operation support
  separately from ingest adapter names, maps `input` / `text` / `date` / `month` to
  `set_value`, maps `toggle` to `click`, and rejects unsupported operations.
- Fixed P2 public/private serialization risk: `CapabilityCompositionResult.model_dump()`
  and `.model_dump_json()` exclude the service-internal `execution_handoff` by default.
- Fixed P3 `LearnedCapabilityRepository.list_page()` pagination by pushing cursor and
  `limit + 1` into SQL.
- Verification: 164 scoped pytest passed, scoped ruff passed, hardcoding scan reviewed.

## Design Review

- Reviewer: Russell (read-only subagent), parent follow-up
- Decision: PASS
- Notes:
  - This child consumes 11.3.12.1 asset foundation, 11.3.12.2 batch lifecycle, and 11.3.12.3 capability hints.
  - No P0 / P1 blockers found; implementation authorization is cleared after P2 doc consistency fixes.
  - P2 fixed: child `plan.md` allowed files now include focused `learned_path_replay.py` helper updates when needed.
  - P2 fixed: parent `plan.md` 12.4 entry now includes allowed / forbidden changes, deliverables, tests,
    compatibility, guardrails, exit criteria, and handoff.

## Code Review

- Reviewer: Epicurus (read-only subagent), parent follow-up
- Decision: PASS after fixes
- Findings fixed:
  - P1 fixed: promotion guard now verifies terminal evidence kind compatibility with the composition plan.
  - P1 fixed: LearnedPath preference now requires confirmed trust plus matching page template and DOM fingerprint when
    the request provides a DOM fingerprint.
  - P1 fixed: candidate evidence now fails closed unless successful terminal outcome, evidence strength, and
    terminal target kind are present.
  - P2 fixed: public `expected_terminal_target` has recursive raw execution detail validation.
  - P2 fixed: adapter compatibility tests cover existing 12.2 ingest adapter names.
  - P2 fixed: tests now cover DOM mismatch, unsupported status, unsupported version / adapter, terminal failed /
    missing evidence, missing terminal target, conflicting controls, promotion missing source ids, and incompatible
    terminal target.
  - Final re-review found no remaining P0 / P1 / P2.

## Actual Delivery

- Created seven-document child package for `11.3.12.4-capability-composition-runtime`.
- Defined scoped v1 composition runtime boundaries: deterministic plan construction, compatibility checks,
  LearnedPath preference, private execution handoff, and promotion guard.
- Excluded Console UI, new public API, LLM-authored browser steps, live validation, and direct autonomous-run endpoint
  calls.
- Added `CapabilityCompositionPlan` / result / policy / private execution handoff / promotion decision schemas.
- Added deterministic `CapabilityComposer` service with LearnedPath preference, candidate review, fail-closed
  compatibility checks, deterministic ordering, private handoff generation, and promotion guard.
- Added focused tests for missing / unsafe / ambiguous / trust / slot / redaction / handoff / promotion behavior.

## Changed Files

- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/README.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/intent.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/contract.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/technical-design.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/test-plan.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/plan.md`
- `docs/iterations/m11/11.3.12.4-capability-composition-runtime/review.md`
- `apps/api/app/schemas/capability_composition.py`
- `apps/api/app/services/learning/capability_composer.py`
- `apps/api/tests/test_capability_composer.py`

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| Source inspection | Parent / previous child context understood | Completed | 0 | pass | local file reads | No runtime execution |
| Design review | Independent review approves or requests changes | PASS with P2 doc consistency fixes | 0 | pass | Russell read-only review | P2 fixed; no P0/P1 |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_composer.py -v` | Composer unit tests pass | 24 passed | 0 | pass | local pytest | Non-live |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_learned_capabilities_repo.py tests/test_learned_paths_repo.py tests/test_learned_path_replay.py -v` | Asset / path / replay compatibility holds | 81 passed | 0 | pass | local pytest | Non-live |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py -v` | Learning / chat compatibility holds | 122 passed | 0 | pass | local pytest | Non-live |
| Combined scoped pytest | Required scoped tests pass together | 227 passed | 0 | pass | local pytest | Non-live |
| Scoped ruff | Changed schema / service / tests pass lint | All checks passed | 0 | pass | `uv run ruff check ...` | Scoped files |
| Hardcoding scan | No new runtime target hardcoding | Only existing generic `data-testid` redaction / evidence hits | 0 | pass | `rg -n ... apps/api/app` | No `/users`, Alice/Bob, validation-site, or user-management example wording |
| Initial code review | Read-only implementation review | NEEDS_FIX: P1/P2 findings | 0 | fail | Epicurus read-only review | Fixed and retested |
| Code re-review | Read-only implementation review | PASS; no remaining P0/P1/P2 | 0 | pass | Epicurus read-only re-review | Final closeout authorized |
| Migration | Not expected | Not run | N/A | skip | N/A | No migration planned |
| Live validation | Not authorized | Not run | N/A | skip | N/A | No `verify-scenario`, no autonomous run |

## Not Run / Unverified

| Item | Reason | Follow-up |
|---|---|---|
| Live validation | Not authorized for this child | Requires explicit future approval |

## Compatibility Review

- Existing LearnedPath, LearnedCapability, LearningBatch, and ExplorationRun behavior remain compatible.
- Composer does not mutate LearnedPath rows; promotion guard returns metadata only after successful execution evidence.
- No public API or Console surface was added.

## Scope Review

- In scope: capability composition runtime docs/design.
- Out of scope: Console UI, public API, live validation, direct autonomous endpoints, and LLM browser-step execution.
