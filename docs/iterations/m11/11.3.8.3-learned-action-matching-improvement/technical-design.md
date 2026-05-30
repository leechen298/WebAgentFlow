# 技术设计（Technical Design）

状态：ready_for_implementation

## Current State

Current `chat_runtime.py` matching builds action terms mainly from:

- `action["utterances"]`
- `action["alias"]`

It compares those terms with raw user input and intake terms (`goal`, `canonical_goal`,
aliases). After `11.3.8.1` and `11.3.8.2`, session actions may also carry:

- `business_goal`
- `canonical_goal`
- `action_aliases`
- `business_object`
- `match_terms`

Those identity terms are preserved / generated but are not yet fully consumed as
action-side matcher terms.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test entry | Notes |
|---|---|---|---|
| Same business action with new values matches | Include action-side identity terms and compare normalized action intent | T1 / T2 | Slot values remain execution parameters |
| Different action on same object does not direct-match | Require compatible action verb / canonical action, not object-only overlap | T3 | Search / delete must not match create |
| Multiple plausible actions require choice | Existing candidate list may contain >1; preserve choice path | T4 | Do not silently rank one |
| Generic verb-only action does not overmatch | Filter weak generic terms and require business-object signal | T5 | `create` alone is insufficient |
| Existing alias / utterance behavior remains | Keep old action term path as fallback | T6 | Backward compatibility |
| No target-specific constants | No route / selector / seed terms in runtime or active tests | T8 | Scan touched files |

## Proposed Implementation

### Chat runtime matcher

Add private helpers near `_matching_actions()`:

```text
_action_match_terms(action) -> set[str]
_strong_action_match(action_phrases, input_phrases) -> bool
_split_action_intent(phrase) -> (verb, object_phrase)
_is_weak_action_term(phrase) -> bool
```

Use these principles:

1. Build action terms from `utterances`, `alias`, `business_goal`, `canonical_goal`,
   `action_aliases`, `business_object`, and `match_terms`.
2. Normalize terms with existing `_normalize_action_match_phrase()` for compatibility.
3. Keep exact / normalized phrase equality and term intersection for full business phrases.
4. Add an intent-aware check for verb + business object compatibility.
5. Filter weak terms where normalized phrase is only a generic verb.
6. Do not let business-object-only overlap produce a match unless action intent also matches.

### Intake terms

Keep `_intake_match_terms()` as the source of user-side semantic terms. It already includes
intake aliases, goal, and canonical goal. If implementation finds it lacks a needed term that is
already available in `ConversationIntakeResult`, add it only with tests and without exposing
private payloads.

### Router alignment

Inspect `router_agent.py` known-action counting after chat runtime matcher tests are defined.
Only change router counting if a focused test demonstrates mismatch between router context and
runtime matcher.

## Affected Surfaces

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No endpoint changes | N/A |
| API response schema | No | No public schema changes | N/A |
| Database schema / migration | No | Existing JSON metadata only | Optional keys remain optional |
| CLI | No command change | Behavior may improve through runtime matching | No new CLI contract |
| Console UI | No | N/A | N/A |
| Conversation events | No expected schema change | Existing events continue | N/A |
| Replay execution | No | Replay handler untouched | Matcher only selects session action |
| Reporter | No | N/A | N/A |
| Worker / async jobs | No | N/A | N/A |
| Tests / fixtures | Yes | Focused runtime / optional router tests | No external site source |
| Docs | Yes | Child package docs and closeout records | N/A |

## Data / Schema Changes

No public schema or DB migration.

Internal action metadata is read-only input for this package. Existing action JSON without
identity keys continues to match by alias / utterances.

## Service / Module Design

`apps/api/app/services/conversation/chat_runtime.py`

- Extend `_matching_actions()` by adding action identity terms.
- Preserve existing public behavior by retaining current alias / utterance comparisons.
- Add deterministic filtering for generic verb-only terms.
- Keep helper functions private and unit-test through runtime behavior.

`apps/api/app/services/conversation/router_agent.py`

- No default change.
- If required, align learned-action counting with the same target-agnostic identity terms
  without adding target constants.

## Data Flow

```text
user execute request
  -> Conversation Intake Agent goal / canonical_goal / aliases / slots
  -> chat runtime current-session learned_actions[]
  -> action-side match terms from alias / utterances / business identity metadata
  -> scoped matching and ambiguity handling
  -> concrete session action binding
  -> existing replay handoff or existing no-path / choice response
```

## Compatibility

- Existing learned actions with only alias / utterances retain current matching.
- Existing pending-choice and vague-request behavior remains authoritative for ambiguity.
- Existing no-path response remains valid when no action matches.
- Existing slot override and replay handoff are not changed.

## Failure / Edge Cases

- Empty metadata: fall back to existing alias / utterance matching.
- Generic verb-only action: do not match richer business-object request.
- Object-only overlap: no direct execution.
- Multiple actions with compatible identity: return multiple candidates and rely on existing
  choice / clarification path.
- Low-confidence or missing intent: choose no match / clarification over execution.
- Target-specific temptation: block rather than add route / selector / seed / page-source constants.

## Non-goals

- No LLM prompt changes.
- No learning service changes.
- No suggested utterance generation changes.
- No replay, reporter, recovery, abort, frontend, worker, DB, or public API changes.
- No live external validation.

## Exit Criteria

- Child seven-doc package exists and design review records no unresolved P0 / P1 findings.
- `review.md` records `implementation_authorized: yes` before code changes.
- TDD evidence shows positive matcher-consumption tests fail before implementation and pass after implementation.
- Negative / ambiguity / generic-verb guards are covered as red tests when they fail today, or as explicit regression baselines when already green.
- Focused tests, focused ruff, target-constant scan, and `git diff --check` are recorded in `review.md`.
- Parent routing is updated to make `11.3.8.4-regression-tests` the next eligible package only after this package reaches `PACKAGE_COMPLETE`.

## Test Matrix

| ID | Area | Coverage |
|---|---|---|
| T1 | Chat runtime positive | Same canonical goal and business object matches with new slot values |
| T2 | Chat runtime positive | Stored `match_terms` / `business_goal` can match even when alias is generic wrapper |
| T3 | Chat runtime negative | Create learned action does not match search / delete request for same object |
| T4 | Chat runtime ambiguity | Multiple plausible matching actions require choice / clarification |
| T5 | Chat runtime safety | Generic verb-only learned action does not overmatch richer request |
| T6 | Compatibility | Existing alias / utterance matching remains green |
| T7 | Router optional | Router known-action count aligns if router code changes |
| T8 | Integrity | Touched runtime / tests contain no external target constants |

## Validation Commands

```bash
find docs/iterations/m11/11.3.8.3-learned-action-matching-improvement -maxdepth 1 -type f | sort
rg -n "Learned Action Matching Improvement|implementation_authorized|ambiguous|low-confidence|Forbidden Changes|Exit criteria" docs/iterations/m11/11.3.8.3-learned-action-matching-improvement
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_router_agent.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/router_agent.py tests/test_conversation_chat_runtime.py tests/test_conversation_router_agent.py
rg -n "<fixture-port>|/target-page|inventory item|External-Fixture-Provider" apps/api/app/services/conversation/chat_runtime.py apps/api/app/services/conversation/router_agent.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_conversation_router_agent.py
git diff --check
```

The target-constant scan is a minimum token scan and is expected to exit `1`
with no output. Code / evidence review must also inspect touched files for
selectors, field labels, button text, placeholders, seed copy, operation aliases,
page source, and other Fixture-Site answer keys.
