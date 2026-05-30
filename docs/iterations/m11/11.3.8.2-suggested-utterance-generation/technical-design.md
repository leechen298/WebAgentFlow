# 技术设计（Technical Design）

状态：PACKAGE_COMPLETE

## Current State

`11.3.8.1` implemented optional business identity fields:

- `LearningRunRequest.action_goal`
- `LearningRunRequest.canonical_goal`
- `LearningRunRequest.action_aliases`
- `LearningRunResult.business_goal`
- `LearningRunResult.canonical_goal`
- `LearningRunResult.action_aliases`
- `LearningRunResult.business_object`
- `LearningRunResult.match_terms`
- `session.metadata_json.learned_actions[]` optional identity keys

Current gap:

- `learning_run_service._utterances_for()` still derives utterances from `_action_label_for(request)`.
- `_action_label_for()` deliberately keeps labels short and may truncate English business phrases.
- `_action_from_learning_result()` stores `result.suggested_utterances` directly, so a stale learning handler can still save wrapper utterances such as `帮我Learn how to create`.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test entry |
|---|---|---|
| Deterministic utterances from business identity | Add identity-aware utterance builder in learning service | `test_learning_run_service.py` |
| Preserve login and Chinese compatibility | Keep login special case; use Chinese wrappers for CJK phrases | existing and new focused tests |
| Exclude slot / sensitive values | Reuse `fill_values` / intake slot filtering before utterance construction | focused slot-value tests |
| Repair stale wrapper utterances at chat runtime boundary | Add chat-runtime helper that regenerates utterances from saved identity when needed | `test_conversation_chat_runtime.py` |
| Do not change matcher policy | Do not edit `_matching_actions()` or router matching logic | diff review / code review |
| No external validation claims | Record not-run live validation in review | `review.md` |

## Proposed Implementation

### Learning service

Replace product-level `_utterances_for(request)` behavior with:

1. Keep `spec_id == "login"` returning `["帮我登录", "登录一下"]`.
2. For non-product-level learning, keep existing label wrappers.
3. For product-level learning:
   - Call `_action_identity_for(request)`.
   - Select a primary phrase from:
     1. `business_goal`
     2. readable `canonical_goal`
     3. first useful alias
     4. `action_label` fallback
   - Reject terms that contain `fill_values`.
   - If primary phrase contains CJK, return Chinese wrappers such as `帮我{phrase}` and `{phrase}一下`.
   - Otherwise return English / generic phrases such as `{phrase}` and `Help me {lowercase phrase}`.
   - Append useful aliases that are not duplicates and do not contain slot values.
   - De-duplicate in stable order.

The builder must use full business identity, not the short `action_label`, unless no identity exists.

### Chat runtime

Add a small helper near `_action_from_learning_result()`:

```text
_utterances_from_action_identity(...)
```

The helper consumes:

- `result.suggested_utterances`
- `business_goal`
- `canonical_goal`
- `action_aliases`
- `business_object`
- intake slot values

Behavior:

- If existing utterances already include a reusable non-wrapper business phrase, preserve them.
- If existing utterances are empty, learning-wrapper-only, or truncated-label wrappers,
  regenerate from identity. Current stale forms that must be treated as repairable include
  `帮我Learn how to create`, `Learn how to create 一下`, `帮我Create purchase orde`, and
  `Create purchase orde一下`.
- Never include slot values.
- Keep deterministic order and duplicate removal.

`_action_from_learning_result()` then stores the helper output in `action["utterances"]`.

## Affected Surfaces

| Surface | Changed? | Notes |
|---|---|---|
| API route contract | No | No endpoint or response schema change |
| DB schema | No | Session JSON metadata content may improve |
| CLI | No command change | User-visible learned-action hint may improve indirectly |
| Console UI | No | N/A |
| Learning service | Yes | Deterministic suggested utterances |
| Chat runtime | Yes | Save repaired utterances when older handlers return wrappers |
| Matcher policy | No | Do not edit `_matching_actions()` |
| Replay / reporter | No | N/A |
| Tests | Yes | Focused service/runtime tests |
| External result docs | No | Must remain unchanged |

## Data / Schema Changes

No public schema or DB migration.

Internal shape remains:

```text
LearningRunResult.suggested_utterances: list[str]
session.metadata_json.learned_actions[].utterances: list[str]
```

Only the generated content changes.

## Service / Module Design

`apps/api/app/services/learning/learning_run_service.py`

- Add helper(s):
  - `_product_utterances_for(request: LearningRunRequest) -> list[str]`
  - `_utterance_candidates_from_identity(...) -> list[str]` or equivalent
  - `_contains_cjk(text: str) -> bool`
  - `_lower_initial_ascii(text: str) -> str`
- Keep helpers private and deterministic.

`apps/api/app/services/conversation/chat_runtime.py`

- Add helper(s):
  - `_utterances_from_action_identity(...) -> list[str]`
  - reuse existing `_identity_match_terms()`, `_is_learning_wrapper_label()`,
    `_is_reusable_identity_term()`, `_intake_slot_values()`.
- Do not change `_matching_actions()`.

## Data Flow

```text
learn user input
  -> Conversation Intake Agent action.goal / canonical_goal / aliases / slots
  -> LearningRunRequest identity fields
  -> LearningRunService _action_identity_for()
  -> LearningRunResult.suggested_utterances
  -> chat_runtime _action_from_learning_result()
  -> session.metadata_json.learned_actions[].utterances
```

If a custom or older learning handler returns stale wrapper utterances, chat runtime uses the already
available identity fields / intake fields to repair the session metadata before saving.

## Compatibility Strategy

- Login special case remains exact.
- Existing Chinese phrases keep the old `帮我...` and `...一下` style.
- English phrases get full business expression and English help variant.
- Backward-compatible fallback remains existing `_action_label_for(request)` wrappers when no business identity exists.
- All new helper behavior is covered by focused tests.

## Failure / Edge Cases

- If every identity term contains a slot value, fall back to existing label wrappers after removing value-bearing phrases.
- If canonical goal is snake_case, generate readable phrase by replacing `_` / `-` with spaces.
- If aliases duplicate primary phrase case-insensitively, keep the first.
- If alias is verb-only or too generic, do not generate it as a suggested utterance unless it contains an object term.
- If an existing utterance is a wrapper around a truncated prefix of `business_goal`, replace it with full identity utterances.
- If existing utterances contain only learning wrappers, regenerate.
- If existing utterances already contain business object terms, preserve them.

## Non-goals

- No matcher threshold changes.
- No direct execution behavior changes.
- No LLM calls.
- No external live validation.
- No result-doc update.
- No external site source or fixture change.

## Test Matrix

| ID | Area | Coverage |
|---|---|---|
| T1 | Learning service | Structured English business goal generates full reusable utterances including business object |
| T2 | Learning service | Slot-bearing action goal falls back to clean canonical / aliases and excludes slot value |
| T3 | Learning service | Existing login / Chinese behavior remains compatible |
| T4 | Chat runtime | Stale wrapper utterances are repaired from intake / result identity before session storage |
| T5 | Chat runtime | Slot values are excluded from stored utterances |
| T6 | Scope guard | Touched runtime / tests do not contain external target constants |
| D1 | Docs | Seven-doc package exists and required phrases are present |
| D2 | Closeout | `review.md` / `CURRENT_STATE.md` record actual evidence and not-run live validation |

## Validation Commands

```bash
find docs/iterations/m11/11.3.8.2-suggested-utterance-generation -maxdepth 1 -type f | sort
rg -n "Suggested Utterance Generation|implementation_authorized|slot values|sensitive|external black-box" docs/iterations/m11/11.3.8.2-suggested-utterance-generation
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py
rg -n "<fixture-port>|/target-page|inventory item|External-Fixture-Provider" apps/api/app/services/learning/learning_run_service.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py
git diff --check
```

The target-constant scan is expected to exit `1` with no matches.
