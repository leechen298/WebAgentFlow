# 实施计划（Plan）

状态：PACKAGE_COMPLETE

## Phase 0 - Source-of-truth and Workspace Check

1. Read:
   - `AGENTS.md`
   - `docs/iterations/README.md`
   - `docs/iterations/AGENTS.md`
   - `docs/iterations/AGENTS.zh.md`
   - `docs/product-model.md`
   - parent `GOAL_RUNNER.md`
   - parent `CURRENT_STATE.md`
   - parent `plan.md`
   - `11.3.8.1` `review.md`
2. Confirm `CURRENT_STATE.md` active package is `11.3.8.2-suggested-utterance-generation`.
3. Confirm no live external validation or external result-doc update is authorized.
4. Run `git status --short --branch` and preserve unrelated existing changes.

## Phase 1 - Child Package Docs

1. Create seven docs under:
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/README.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/intent.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/contract.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/technical-design.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/test-plan.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/plan.md`
   - `docs/iterations/m11/11.3.8.2-suggested-utterance-generation/review.md`
2. Sync milestone discoverability in `docs/iterations/m11/README.md`.
3. Sync milestone status summary in `docs/iterations/m11/m11-plan.md` if needed.
4. Run documentation checks D1 and D2 from `test-plan.md`.
5. Dispatch read-only subagent review for spec/design.
6. Fix any P0/P1 design findings.
7. If approved, update `review.md` with `implementation_authorized: yes`.

## Phase 2 - TDD Tests

1. Add failing learning service test for structured English business identity:
   - expected utterances include full business phrase and English help phrase;
   - expected utterances include useful alias;
   - expected utterances exclude slot value.
2. Run the targeted test and record the red failure.
3. Add failing learning service negative test proving verb-only aliases such as `create` are excluded.
4. Run the targeted test and record the red failure.
5. Add failing chat runtime test for stale learning-wrapper utterance repair.
6. Run the targeted test and record the red failure.
7. Add failing chat runtime test for stale truncated-label wrapper repair, for example
   `帮我Create purchase orde` / `Create purchase orde一下`.
8. Run the targeted test and record the red failure.

## Phase 3 - Implementation

1. Update `apps/api/app/services/learning/learning_run_service.py`:
   - keep login special case;
   - add product-level identity-aware utterance builder;
   - generate full business-object utterances from business identity;
   - de-duplicate and exclude slot values.
   - exclude verb-only / generic aliases.
2. Update `apps/api/app/services/conversation/chat_runtime.py`:
   - repair empty / wrapper-only utterances using business identity before storing session learned action;
   - repair truncated-label wrappers using business identity before storing session learned action;
   - keep existing non-wrapper business utterances unchanged;
   - do not edit `_matching_actions()`.

## Phase 4 - Verification

Run required commands from `test-plan.md`:

1. `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q`
2. `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q`
3. `cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py`
4. target-constant scan over touched runtime / tests
5. `git diff --check`
6. `git status --short`
7. `git diff --name-only`

Do not run live external validation.

## Phase 5 - Subagent Code / Test / Evidence Review

1. Dispatch read-only subagent review with:
   - child docs;
   - implementation diff;
   - test output;
   - forbidden target scan result;
   - external-validation not-run boundary.
2. Fix P0/P1 findings.
3. Re-run affected tests / checks after fixes.
4. Record unresolved P2/P3 caveats in `review.md`.

## Phase 6 - Closeout

1. Update child `review.md` with:
   - design review;
   - implementation summary;
   - changed files;
   - red / green test evidence;
   - commands run;
   - commands not run;
   - compatibility review;
   - scope review;
   - unresolved findings;
   - final status.
2. Update parent `CURRENT_STATE.md`:
   - active child remains `11.3.8.2` until package complete;
   - once complete, mark 11.3.8.2 `PACKAGE_COMPLETE`;
   - route `11.3.8.3` as next eligible, but do not start it.
3. Optionally update parent `review.md` FINAL_STATUS summary to align with current child status.
4. Run closeout consistency checks.
5. Stop. Do not start `11.3.8.3`.

## Stop Conditions

Stop as `BLOCKED` if:

- implementation needs LLM utterance generation;
- implementation needs matcher policy changes;
- tests require external Fixture-Site source or live target;
- target-specific constants would enter runtime / prompts;
- required verification cannot produce reviewable evidence.

Stop as `NEEDS_USER_INPUT` if:

- `CURRENT_STATE.md` conflicts with child docs or actual git state;
- an out-of-scope runtime/test/eval/external result file appears in `git diff --name-only`;
- P0/P1 review findings cannot be fixed within this package.
