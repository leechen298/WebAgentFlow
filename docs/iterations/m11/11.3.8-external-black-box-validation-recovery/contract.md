# Contract

Status: ready for review

## Public Concepts

`11.3.8 External Black-box Validation Recovery` is an umbrella planning package for M11.3 post-closeout recovery. It converts the recorded external black-box validation failure into a sequenced set of child packages:

- `11.3.8.1-learning-action-goal-preservation`
- `11.3.8.2-suggested-utterance-generation`
- `11.3.8.3-learned-action-matching-improvement`
- `11.3.8.4-regression-tests`
- `11.3.8.5-external-black-box-revalidation-closeout`

The parent package is documentation-only. It is not a code implementation package, not a live validation package, and not a pass/fail evidence package for the external target.

## Allowed Changes

This parent package may change only:

- umbrella planning docs under `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/`;
- the M11 milestone index entry for this package in `docs/iterations/m11/README.md`.

Child packages may later propose runtime, test, or validation changes only after they create their own full seven-document package and complete review.

## Forbidden Changes

The parent package must not:

- modify runtime, schema, API, frontend, fixture, migration, or test implementation files;
- modify `WebAgentFlow-Validation-Site` or `WebAgentFlow-Fixture-Site`;
- restore `apps/product-test-site` or `apps/validation-site`;
- update external black-box latest results as if validation has been rerun;
- mark `PV-CLI-003` fixed, passed, or verified;
- call `/exploration/autonomous-runs` or `/exploration/autonomous-runs/stream`;
- use direct replay, service imports, hidden HTTP clients, or ad hoc scripts as product validation evidence;
- introduce target-specific selectors, `data-testid`, seed copy, component details, route constants, or answer keys into product runtime, prompts, active eval defaults, or child-package implementation instructions.

## Evidence / Verification Contract

This package can only claim documentation verification performed in the current session. It cannot claim runtime, CLI, UI smoke, autonomous-run, `verify-scenario`, or external black-box validation pass unless those actions are actually run and recorded in `review.md`.

For this parent package:

- documentation inspection may be marked complete when file existence and required text checks pass;
- runtime/test/build/live validation must be marked `not run`;
- `external-black-box-validation-latest.md` remains the authoritative current `FAIL` record until a later approved revalidation package updates it with current evidence.

## Compatibility Requirements

The umbrella plan must preserve:

- existing product lifecycle stages L1 / L2 / L3;
- existing internal Agent roles and legacy aliases;
- existing M11 closeout caveats;
- current WAgent chat and Conversation API evidence boundaries;
- separation between deterministic Fixture-Site, external Validation-Site, and product runtime;
- historical 11.3.6 / 11.3.7 eval results as historical evidence only.

No public API, database schema, replay status semantics, reporter boundary, recovery boundary, or abort boundary changes are authorized by this parent package.

## Scope Guardrails

Child implementation packages must not compensate for missing business metadata by broad fuzzy matching or target-specific constants. They must preserve the product principle that the LLM may understand language, while code decides whether and how WebAgentFlow acts.

M12 recovery / retry / abort / interruption remains out of scope. If a child package discovers that the fix requires M12 behavior, it must stop and record a blocker instead of widening 11.3.8.

## Out-of-scope Follow-ups

- Full page-wide automatic capability discovery.
- Full learn-then-execute across arbitrary domains.
- L2 guided teaching or Teaching Guide Agent work.
- External validation-site automation as CI default.
- Console UI smoke for this specific recovery package.
- M12 recovery / retry / abort / interruption.

## Assumptions

- The 2026-05-25 external validation report and PV-CLI-003 triage are accepted as the current failure baseline.
- The external Validation-Site remains outside this repository and is operator-provided during revalidation.
- Child packages can use synthetic repo-local tests for non-live regression without copying external site implementation details.

## Open Risks

- The current runtime may not expose intake business goal at the exact learning-result boundary expected by `11.3.8.1`.
- Matching improvements may accidentally overmatch generic verbs unless negative tests are strong.
- External black-box revalidation may remain blocked by local services, LLM provider availability, browser availability, or stale DB state.
- A partial fix could make repo-local tests pass while product-like validation still fails; `11.3.8.5` must keep that result honest.
