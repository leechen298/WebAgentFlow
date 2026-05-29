# 实施计划（Implementation Plan）

状态：ready for review

## Inputs

- `AGENTS.md`
- `CLAUDE.md` / `CLAUDE.zh.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/AGENTS.zh.md`
- `docs/product-model.md`
- `docs/scope-boundaries.md`
- `docs/testing/results/external-black-box-validation-latest.md`
- `docs/testing/results/pv-cli-003-failure-triage-20260525.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/README.md`
- `docs/iterations/m11/11.3.8-external-black-box-validation-recovery/plan.md`
- this package's `intent.md`, `contract.md`, `technical-design.md`, `test-plan.md`

## Files / Modules

Expected implementation files after review:

- `apps/api/app/services/learning/learning_run_service.py` - carry and derive product-level action identity.
- `apps/api/app/services/conversation/chat_runtime.py` - pass intake action metadata and store it in session learned action metadata.
- `apps/api/app/services/conversation/intake.py` - optional helper reuse only if necessary.
- `apps/api/app/schemas/conversation_intake.py` - optional backward-compatible field only if approved.
- `apps/api/tests/test_learning_run_service.py` - focused action identity tests.
- `apps/api/tests/test_conversation_chat_runtime.py` - focused session metadata tests.
- `apps/api/tests/test_conversation_intake.py` - only if intake behavior changes.
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md` - actual implementation and verification record.

Forbidden implementation files:

- runtime route files, frontend files, fixture files, migration files, worker files, external site files, external validation result docs.

## Phase Boundaries

### Phase 0 · Documentation Review Gate

1. Review this seven-doc package.
2. If approved, update status to `ready_for_implementation`.
3. Do not edit runtime files before this gate passes.

### Phase 1 · Metadata Path

1. Identify where the learning flow has both `ConversationIntakeResult` and `LearningRunResult`.
2. Add minimal optional internal fields or runtime enrichment to carry `business_goal`, `canonical_goal`, aliases, and match terms.
3. Preserve old behavior when intake metadata is absent.

Stop condition: if metadata cannot be accessed without broad API/schema changes, mark blocked and update design.

### Phase 2 · Label And Session Action Preservation

1. Prefer structured business goal for product-level `action_label`.
2. Save optional business identity fields into session `learned_actions[]`.
3. De-duplicate terms deterministically and exclude slot values.
4. Keep matcher behavior unchanged.

Stop condition: if implementation needs target-specific strings or looser matcher thresholds, stop and re-review.

### Phase 3 · Focused Tests

1. Add learning service tests for English business identity and slot-value exclusion.
2. Add chat runtime tests for session metadata preservation after learning completion.
3. Preserve existing Chinese / login expectations.

### Phase 4 · Verification And Review

1. Run required focused commands from `test-plan.md`.
2. Run `git diff --check`.
3. Update `review.md` with changed files, commands, results, not-run live validation, compatibility review, scope review, and unresolved findings.
4. Leave handoff notes for 11.3.8.2.

## Verification

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.8.1-learning-action-goal-preservation -maxdepth 1 -type f | sort` | Seven package docs exist | Yes | Documentation stage |
| `rg -n "Learning Action Goal Preservation|business_goal|canonical_goal|business_object|match_terms|Forbidden Changes|Exit Criteria" docs/iterations/m11/11.3.8.1-learning-action-goal-preservation` | Required review terms present | Yes | Documentation stage |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q` | Learning result preserves action identity | Yes | Implementation stage |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q` | Session action metadata preserves identity | Yes | Implementation stage |
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_intake.py -q` | Intake compatibility if touched | Yes | Conditional |
| `cd apps/api && ../../.venv/bin/python -m ruff check ...` | Changed Python files lint-clean | Yes | Exact files depend on approved implementation |
| `git diff --check` | No whitespace errors | Yes | Required |

## Review Checklist

- [ ] Implementation still matches `contract.md`.
- [ ] No target-specific constants were introduced.
- [ ] No matcher, replay, reporter, recovery, abort, frontend, API route, DB migration, or external site changes were made.
- [ ] Existing sessions without new metadata remain compatible.
- [ ] Focused tests prove business identity preservation and slot-value exclusion.
- [ ] `review.md` records every command actually run and marks live validation `not run`.

## Exit Criteria

- Seven-doc package has passed documentation / design review before implementation starts.
- Focused implementation, if later done, preserves `Create inventory item` / `create_inventory_item` or equivalent business identity from intake without hardcoding external target terms.
- Focused tests pass and are recorded.
- No forbidden runtime / prompt constants appear in changed files.
- Package handoff says whether 11.3.8.2 can proceed.

## Handoff To Next Package

If implementation succeeds, `11.3.8.2-suggested-utterance-generation` should consume
`business_goal`, `canonical_goal`, `action_aliases`, `business_object`, and/or `match_terms`
to generate reusable utterances. If these fields are absent or unstable, 11.3.8.2 remains blocked.
