# 实施计划（Implementation Plan）

状态：implementation_complete_pending_followup

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

Implementation files already present in HEAD:

- `apps/api/app/services/learning/learning_run_service.py` - carry and derive product-level action identity.
- `apps/api/app/services/conversation/chat_runtime.py` - pass intake action metadata and store it in session learned action metadata.
- `apps/api/app/routers/conversation.py` - internal learning handler metadata handoff, without public route contract change.
- `apps/api/tests/test_learning_run_service.py` - focused action identity tests.
- `apps/api/tests/test_conversation_chat_runtime.py` - focused session metadata tests.
- `apps/api/tests/test_conversation_intake.py` - only if intake behavior changes.
- `docs/iterations/m11/11.3.8.1-learning-action-goal-preservation/review.md` - actual implementation and verification record.

Forbidden implementation files:

- runtime route files, frontend files, fixture files, migration files, worker files, external site files, external validation result docs.

## Phase Boundaries

### Phase 0 · Documentation Review Gate

Completed historically. Current checkpoint note: runtime implementation already exists in HEAD from
earlier commits. This documentation revision reconciles the package record with that committed
implementation and should be followed by implementation/code review rather than a fresh
implementation pass.

### Phase 1 · Metadata Path

1. The committed implementation identifies where the learning flow has both `ConversationIntakeResult` and `LearningRunResult`.
2. The committed implementation carries `business_goal`, `canonical_goal`, aliases, and match terms through optional internal fields / runtime enrichment.
3. Old behavior remains preserved when intake metadata is absent.

Review stop condition: if metadata cannot be accessed without broad API/schema changes, mark blocked and update design before further code work.

### Phase 2 · Label And Session Action Preservation

1. Product-level `action_label` prefers structured business goal.
2. Session `learned_actions[]` saves optional business identity fields.
3. Terms are de-duplicated deterministically and slot values are excluded.
4. Matcher behavior remains unchanged by this package.

Review stop condition: if follow-up work needs target-specific strings or looser matcher thresholds, stop and re-review.

### Phase 3 · Focused Tests

1. Learning service tests cover English business identity and slot-value exclusion.
2. Chat runtime tests cover session metadata preservation after learning completion.
3. Existing Chinese / login expectations remain compatible.

### Phase 4 · Verification And Review

1. Required focused commands from `test-plan.md` are recorded in `review.md` from the implementation checkpoint.
2. `git diff --check` is recorded for implementation and this documentation revision.
3. `review.md` records changed files, commands, results, not-run live validation, compatibility review, scope review, and unresolved findings.
4. Handoff notes for 11.3.8.2 remain in this package.

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

- Seven-doc package and committed implementation are aligned before code review proceeds.
- Focused implementation preserves `Create inventory item` / `create_inventory_item` or equivalent business identity from intake without hardcoding external target terms.
- Focused tests pass and are recorded.
- No forbidden runtime / prompt constants appear in changed files.
- Package handoff says whether 11.3.8.2 can proceed.

## Handoff To Next Package

If implementation succeeds, `11.3.8.2-suggested-utterance-generation` should consume
`business_goal`, `canonical_goal`, `action_aliases`, `business_object`, and/or `match_terms`
to generate reusable utterances. If these fields are absent or unstable, 11.3.8.2 remains blocked.
