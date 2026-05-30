# PV-CLI-003 Failure Triage

Status: triaged
Source validation report: `docs/testing/results/external-black-box-validation-20260525.md`
Source validation commit: `ad6451c`
Conversation session: `9f6c3610-b326-4f8b-887c-285dfaa8699d`

## Boundary

This triage is a read-only failure analysis of the already recorded
PV-CLI-003 run. It did not modify runtime code, prompts, external site source,
or database records. It did not trigger a new autonomous run, did not rerun
external black-box validation, did not call `/exploration/autonomous-runs` or
`/exploration/autonomous-runs/stream`, and did not clear old database state.

Database reads used the current local API database state only to explain the
existing failure. They are not treated as product pass / fail evidence.

## Evidence Table

| Layer | Evidence |
| --- | --- |
| URL-only setup | User input was `http://127.0.0.1:<fixture-port>/target-page`. The session saved a pending target for that URL and returned `还没学过这个页面。你可以先学习这个页面上的操作、查看页面，或取消。`. No learning or execution event started from the URL-only turn. |
| Learning intake | The learn input was parsed as `intent=learn_operation`, `confidence=0.95`, `action.goal=Create inventory item`, `canonical_goal=create_inventory_item`, with aliases such as `add inventory item` / `new inventory item` / `create new item`, and with record_code, name, category, and quantity slots present. |
| Learning request / run | The persisted exploration run was product-level, had target URL `http://127.0.0.1:<fixture-port>/target-page`, and stored the full learning goal text. The run completed and persisted a LearnedPath hash `sha256:3eae41576d79`; the run verdict snapshot was still `failure` because the product-level save rule accepted supervisor-observed DOM mutation despite no URL/title change. |
| Learned action metadata | `chat_learning_completed` recorded alias `Learn how to create `. Session `learned_actions` stored alias `Learn how to create ` and utterances `帮我Learn how to create ` / `Learn how to create 一下`. The stored action did not retain `Create inventory item`, `create_inventory_item`, or the inventory business object as matchable terms. |
| LearnedPath row | The LearnedPath row hash was `sha256:3eae41576d79`, page template `/target-page`, scenario `product_level`, trust `provisional`, provenance `system`, and action count `6`. It did not expose a useful business action label; the reusable session action label came from the runtime learning result, not from the page actions themselves. |
| Execute intake | The execute input was parsed as `intent=execute_operation`, `confidence=0.95`, `action.goal=Create inventory item`, `canonical_goal=create_inventory_item`, and had record_code, name, category, and quantity slots present. The target URL resolved to the same `/target-page` page. |
| Router decision | The router LLM trace selected `recommended_skill=start_replay`, `user_goal=Create inventory item`, and `known_context.has_learned_action=true`. This showed the high-level router considered the action relevant, but it did not bind a concrete session action for runtime execution. |
| Matcher outcome | Runtime `_matching_actions()` compared the execute input and intake terms against action alias / utterances. A pure-function replay of the same terms produced `matches_count=0`: normalized action terms were `learnhowtocreate` / `learnhowtocreate一下`, while execute terms were `Create inventory item` / `create_inventory_item`. |
| Final WAgent response | Runtime entered `chat_no_path` with `reason=target_operation_unmatched`, `learned_action_count=1`, and learned action label `Learn how to create `. The visible response was `我学过这个页面的一些操作：Learn how to create。但还没学过你要做的这个操作。你可以先学习这个新操作，学会后再让我执行，或取消。` |

## Root Cause Classification

- `learning_action_label_too_generic`: confirmed. The learning intake knew the business goal, but the persisted reusable action alias became `Learn how to create `.
- `business_object_not_preserved`: confirmed. `inventory item` / `create_inventory_item` was present in intake and router data but absent from the reusable session action terms.
- `execution_action_match_too_literal`: confirmed. The runtime matcher only matched exact / substring / normalized phrase intersections between user input or intake terms and action alias / utterances; the learned action terms had no overlap with the execute intent terms.

## Static Code Pointers

- `apps/api/app/services/learning/learning_run_service.py:511` derives product-level action labels from `LearningRunRequest.goal`, strips only limited noise / named value clauses, then truncates to 20 characters at line `521`.
- `apps/api/app/services/learning/learning_run_service.py:504` builds suggested utterances directly from that label.
- `apps/api/app/services/conversation/chat_runtime.py:4554` stores the learning result as session action metadata with `alias` and `utterances`.
- `apps/api/app/services/conversation/chat_runtime.py:4603` matches only action alias / utterances against raw user input and intake terms.
- `apps/api/app/services/conversation/router_agent.py:434` uses the same term-intersection style for learned-action counting.
- `apps/api/app/services/conversation/chat_runtime.py:1838` requires a concrete `_match_session_action()` result before replay; if no match exists but target actions exist, it falls through to `target_operation_unmatched`.

## Follow-up Candidates

- Preserve the intake business goal when creating product-level learning action labels.
- Generate suggested utterances that include the business object, not only the raw "learn how to" phrase.
- Let execution matching compare canonical goal / business object overlap, not only literal action alias and utterance terms.
- Add regression coverage for English learn/create/target-page-item normalization, including learn input followed by execute input with new slot values.

## Triage Conclusion

PV-CLI-003 failed after learning completed because the reusable action metadata
lost the business goal. The system learned a path for the page, but the
session action was named and matched as `Learn how to create ` instead of
`Create inventory item`. Execution intake was good enough to express the task,
but runtime could not bind it to the learned action, so it correctly refused to
execute rather than guessing.
