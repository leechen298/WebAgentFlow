# Review

状态：PACKAGE_COMPLETE

## FINAL_STATUS

status: PACKAGE_COMPLETE
parent_package: 11.3.12-bounded-learning-composable-capability-assets
active_child_package: 11.3.12.3-page-understanding-capability-hints
implementation_authorized: yes
do_not_start_next_package: false
blocking_findings: none
last_verified_at: 2026-06-06
commands_run: source inspection; document generation; read-only design review; document static checks; scoped pytest; scoped ruff; hardcoding scan; read-only code review
commands_not_run: migration, live validation, `verify-scenario`, `wagent chat`
next_action: Do not extend this child. Parent campaign is responsible for final closeout and any future validation route.

## 2026-06-06 Code Review Handoff Fixes

- Fixed P2 combobox support semantics: Page Understanding capability hints now mark
  combobox controls as `unsupported` until the full ingest / executor chain supports
  them, instead of letting them enter supported scenario planning and fail later.
- Fixed matching capability discovery fallback behavior so combobox fillable controls
  are placed in `unsupported_capabilities`.
- Verification: 164 scoped pytest passed, scoped ruff passed, hardcoding scan reviewed.

## Design Review

- Reviewer: Russell (read-only subagent), parent follow-up
- Decision: PASS
- Notes:
  - This child consumes 11.3.12.2 bounded learning batch lifecycle.
  - P1 fixed in docs: public serialized hints are now explicitly redacted refs, while executable selectors / element
    bindings stay in a private resolver outside `CapabilityHintSet`.
  - P2 fixed in docs: `sample_value_sources` now has allowed source kinds and redaction / execution semantics.
  - P2 fixed in parent plan: the 11.3.12.3 planned package entry now includes allowed / forbidden changes,
    deliverables, tests, compatibility, guardrails, exit criteria, and handoff.
- Re-review found no new P0 / P1 / P2 blockers and cleared implementation authorization.

## Code Review

- Reviewer: Franklin (read-only subagent), parent follow-up
- Decision: NEEDS_FIX, then fixed locally
- Findings:
  - P1 fixed: closeout/status docs now mark 11.3.12.3 `PACKAGE_COMPLETE` and parent routing advances to 11.3.12.4
    package creation.
  - P2 fixed: public hint schemas now validate redacted refs directly and reject raw selector refs, with regression
    coverage in `test_public_hint_schema_rejects_raw_selector_refs`.
  - Checked OK by reviewer: builder redaction, current-analysis resolver, hint-only dependency pairs, additive
    PageAnalysis field, and scoped hardcoding boundary.

## Actual Delivery

- Created seven-document child package for `11.3.12.3-page-understanding-capability-hints`.
- Defined capability hint concepts, target-agnostic region / control / terminal / dependency boundaries, and
  no-live-validation scope.
- Proposed implementation around capability hint schemas, deterministic hint builder, PageAnalysis additive
  field, PageAnalyzer integration, and capability discovery consumption.
- Clarified the dual-reference contract: serialized hints carry only redacted refs, while execution can resolve those
  refs through private current-analysis bindings.
- Defined sample value source kinds and which kinds may materialize runtime probe values from serialized hints.
- Added `CapabilityHintSet` schemas and deterministic PageAnalysis capability hint builder.
- Integrated `analyze_page()` so live PageAnalysis output receives redacted capability hints as an additive field.
- Updated capability discovery to prefer hints when present while preserving old fallback behavior when hints are absent
  or empty.
- Implemented current-analysis resolver behavior so serialized hint refs stay redacted while generated scenarios keep
  executable bindings internally.
- Made hint-mode dependency-pair scenario generation depend on explicit dependency groups; legacy no-hints scenario
  generation remains compatible.

## Changed Files

- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/README.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/intent.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/contract.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/technical-design.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/test-plan.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/plan.md`
- `docs/iterations/m11/11.3.12.3-page-understanding-capability-hints/review.md`
- `apps/api/app/schemas/capability_hints.py`
- `apps/api/app/schemas/page_analysis.py`
- `apps/api/app/services/learning/capability_hints.py`
- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/tests/test_capability_hints.py`
- `apps/api/tests/test_filter_capability_discovery.py`

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| Source inspection | Parent / previous child context understood | Completed | 0 | pass | local file reads | No runtime execution |
| Initial design review | Independent review approves or requests changes | Russell found P1/P2 doc gaps | 0 | fail | subagent review | Docs updated |
| Design re-review | Independent review approves or requests changes | PASS; no new P0/P1/P2 blockers | 0 | pass | Russell read-only re-review | Implementation authorized |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_capability_hints.py tests/test_filter_capability_discovery.py -v` | New hint schema / discovery tests pass | 12 passed | 0 | pass | local pytest | Non-live |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_page_analyzer_selector.py tests/test_learning_run_service.py tests/test_bounded_learning_batch_lifecycle.py -v` | Analyzer / learning regressions pass | 45 passed | 0 | pass | local pytest | Non-live |
| Combined scoped pytest | Required scoped tests still pass after static fixes | 58 passed | 0 | pass | local pytest | Non-live |
| Scoped ruff | Changed schema / service / tests pass lint | All checks passed | 0 | pass | `uv run ruff check ...` | Scoped files |
| Hardcoding scan | No new runtime target hardcoding | Only existing generic `data-testid` redaction / evidence hits | 0 | pass | `rg -n ... apps/api/app` | No `/users`, Alice/Bob, validation-site, or user-management example wording |
| Code review | Read-only implementation review | NEEDS_FIX: stale closeout docs; schema redaction validator caveat | 0 | pass | Franklin read-only review | P1/P2 fixed and retested |
| Migration | Not expected | Not run | N/A | skip | N/A | No migration planned |
| Live validation | Not authorized | Not run | N/A | skip | N/A | No `verify-scenario`, no autonomous run |

## Not Run / Unverified

| Item | Reason | Follow-up |
|---|---|---|
| Live validation | Not authorized for this child | Requires explicit future approval |

## Compatibility Review

- Planned compatibility: existing PageAnalysis, capability discovery fallback, LearningBatch, LearnedCapability,
  LearnedPath, and ExplorationRun behavior remain compatible.
- PageAnalysis change is additive; callers constructing old PageAnalysis payloads receive default empty hints.
- `build_filter_inventory()` preserves legacy no-hints / empty-hints behavior.
- Hint-mode scenario generation keeps executable selector bindings internal and does not serialize selectors in
  `CapabilityHintSet`.
- Public hint schemas reject non-redacted refs during direct model validation.

## Scope Review

- In scope: Page Understanding capability hint docs/design.
- Out of scope: runtime capability composition, Console UI, live validation, direct autonomous endpoints.
