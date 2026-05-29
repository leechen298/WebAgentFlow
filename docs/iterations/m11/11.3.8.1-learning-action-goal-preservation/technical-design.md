# 技术设计（Technical Design）

状态：ready for review

## Current State

Relevant current code:

- `apps/api/app/services/learning/learning_run_service.py`
  - `LearningRunRequest` carries `goal`, `fill_values`, `product_level`, but no structured intake action.
  - `LearningRunResult` returns `action_label` and `suggested_utterances`, but no business goal metadata.
  - `_product_action_label_for()` strips learning noise and named values, then truncates label to 20 chars.
- `apps/api/app/services/conversation/chat_runtime.py`
  - `_action_from_learning_result()` stores session learned actions with `alias`, `utterances`, `learned_path_id`,
    `target_url`, `site_origin`, `page_template`, and `scenario`.
  - `_matching_actions()` currently compares raw input / intake terms against action `alias` and `utterances`.
- `apps/api/app/schemas/conversation_intake.py`
  - `ConversationIntakeAction` already exposes `goal`, `canonical_goal`, and `aliases`.

Failure baseline:

- PV-CLI-002 learned a product-level operation but returned action label `Learn how to create`.
- PV-CLI-003 execute intake identified `Create inventory item` / `create_inventory_item`, but session action metadata did not preserve those terms.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Preserve business identity from learning intake | Add internal optional metadata from intake action into learning request/result or chat runtime learning handoff | `test_learning_run_service.py`, `test_conversation_chat_runtime.py` | No target constants |
| Keep old session actions compatible | New session action keys are optional; existing `alias` / `utterances` consumers keep working | focused chat runtime regression | No DB migration |
| Do not change matcher policy | Do not update `_matching_actions()` criteria except tests may assert metadata exists for later package | review diff scope, no matcher behavior tests required here | Matching belongs to 11.3.8.3 |
| Do not update external validation result | Review records live validation as not run | `review.md` | 11.3.8.5 owns revalidation |
| Avoid slot values as identity | Metadata builder excludes `fill_values` / slot values from match terms unless they are structural action names | focused unit tests | SKU / names / quantities are parameters |

## Proposed Implementation

After documentation / design review passes, the implementation should use a minimal internal metadata path:

1. Capture the structured intake action near the existing learning dispatch path.
   - Preferred: pass an optional action identity payload into `LearningRunRequest`, such as
     `action_goal`, `canonical_goal`, and `action_aliases`, or equivalent fields approved in review.
   - Alternative: build session metadata in `chat_runtime.py` by combining `LearningRunResult` with the intake object already available during learning.
2. Extend `LearningRunResult` or `_action_from_learning_result()` to preserve optional metadata:
   - `business_goal`
   - `canonical_goal`
   - `action_aliases`
   - `business_object` or equivalent extracted match term
   - `match_terms`
3. Improve label source order for product-level learning:
   - Prefer structured business goal when present.
   - Fall back to canonical goal converted to a readable phrase when business goal is missing.
   - Fall back to current `_product_action_label_for(request)` behavior.
   - Keep existing login special case.
4. Ensure match terms are target-agnostic:
   - Include business goal, canonical goal, aliases, and normalized object terms.
   - Exclude URLs, credentials, SKU / item names / quantities, selectors, field labels, and page-source details.
5. Keep `suggested_utterances` behavior compatible in this package.
   - 11.3.8.2 may improve utterance generation after metadata shape is stable.

## Affected Surfaces

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | No route changes | N/A |
| API response schema | No | No public response contract change planned | Internal metadata may appear in session metadata only if existing serializers expose it safely |
| Database schema / migration | No | Session metadata JSON may gain optional keys | Existing rows remain valid |
| CLI | No | No CLI command changes | CLI behavior improvement is indirect after later matcher package |
| Console UI | No | No UI changes | N/A |
| Conversation events | Yes, optional | `chat_learning_completed` may include preserved business identity if existing event payload mirrors action metadata | Must not leak slot values |
| Replay execution | No | No execution behavior changes | N/A |
| Reporter | No | No reporter changes | N/A |
| Worker / async jobs | No | No worker changes | N/A |
| Tests / fixtures | Yes | Focused API service tests only | No external target dependency |
| Docs | Yes | Update package `review.md` after implementation | No status inflation |

## Data / Schema Changes

No DB migration or public schema change is planned.

Internal dataclass options are acceptable if review approves:

```text
LearningRunRequest.action_goal: str | None
LearningRunRequest.canonical_goal: str | None
LearningRunRequest.action_aliases: list[str]

LearningRunResult.business_goal: str
LearningRunResult.canonical_goal: str | None
LearningRunResult.action_aliases: list[str]
LearningRunResult.business_object: str | None
LearningRunResult.match_terms: list[str]
```

Exact names may change during implementation, but the semantic contract must remain:
preserve business identity separately from `alias` / `utterances`, keep fields optional,
and do not require migration.

## Service / Module Design

Planned module responsibilities:

- `conversation/chat_runtime.py`
  - Pass structured intake action metadata into learning result construction, or enrich `_action_from_learning_result()`.
  - Save optional metadata into session `learned_actions`.
  - Keep `_scope_action_key()` compatible; do not change dedupe semantics unless review explicitly approves a metadata-aware key.
- `learning/learning_run_service.py`
  - Prefer structured business goal when deriving product-level `action_label`.
  - Build deterministic action identity terms without LLM calls.
  - Continue stripping named values from labels.
- `conversation/intake.py` / `conversation_intake.py`
  - Only touched if needed for a small shared helper or optional field. No broad intake redesign.

## Data Flow

```text
user learn input
  -> Conversation Intake Agent output: action.goal / canonical_goal / aliases / slots
  -> chat runtime learning request
  -> LearningRunService result
  -> _action_from_learning_result()
  -> session.metadata_json.learned_actions[]
       alias
       utterances
       learned_path_id / target_url / page_template
       business_goal / canonical_goal / action_aliases / business_object / match_terms
```

This package stops at metadata persistence. Execution-time matching still follows the pre-existing matcher until 11.3.8.3.

## Compatibility Strategy

- All new fields are optional.
- Existing action metadata readers continue using `alias` when they do not understand richer fields.
- Existing tests expecting Chinese labels should remain unchanged unless the old expected output was already a wrapper regression.
- If public session / history surfaces expose metadata, they must expose only business identity and not private ids beyond existing behavior.

## Anti-drift Rules

- Do not add strings from `WebAgentFlow-Validation-Site` implementation.
- Do not mention `5177/inventory` outside docs or test comments that describe the historical failure.
- Do not make `inventory item` a branch condition.
- Do not loosen `_matching_actions()` in this package.
- Do not update `external-black-box-validation-latest.md`.
- Do not claim a product validation pass from unit tests.

## Failure / Edge Cases

- If intake metadata is absent, fall back to current label derivation and leave optional metadata empty.
- If business goal includes sensitive values, reuse existing named-value stripping and exclude slot values from match terms.
- If canonical goal is snake_case, store it as canonical metadata and optionally derive a readable object phrase.
- If multiple aliases duplicate normalized forms, de-duplicate while preserving deterministic order.
- If implementation cannot access intake action safely, mark blocked rather than deriving from page-specific labels or external target details.

## Non-goals

- No matcher improvement.
- No suggested utterance redesign.
- No external black-box rerun.
- No UI / CLI / API / DB migration.
- No recovery / retry / abort behavior.

## Test Matrix

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Learning service unit | Product-level English learning preserves business label and metadata without slot values | `test-plan.md` T1 |
| Chat runtime service | Learning completion stores metadata under session learned action | `test-plan.md` T2 |
| Compatibility regression | Existing login / Chinese create-record learning remains compatible | `test-plan.md` T3 |
| Scope guard | No external target constants in changed runtime / tests | `test-plan.md` T4 |
| Docs / review | Status and not-run evidence are honest | `test-plan.md` D1-D3 |

## Validation Commands

Implementation-stage minimum:

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_learning_run_service.py -q
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_chat_runtime.py -q
cd apps/api && ../../.venv/bin/python -m ruff check app/services/learning/learning_run_service.py app/services/conversation/chat_runtime.py tests/test_learning_run_service.py tests/test_conversation_chat_runtime.py
git diff --check
```

Documentation-stage checks are listed in `test-plan.md` and recorded in `review.md`.
