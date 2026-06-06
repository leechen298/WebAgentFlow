# Technical Design

## Current State

`wagent chat` currently can complete learning feedback from a single learned action alias.
When the user selected the control option `开始学习`, that control phrase may leak into the learned action identity,
leading to feedback such as “我学会了开始操作 / 帮我开始”.

This design changes learning completion from alias-template feedback to aggregate-outcome feedback.

## Inputs From Child 1

Child 2 requires child 1 to provide an aggregate learning result with at least:

- `learning_outcome` candidate inputs
- `discovery_batch_id`
- `capability_summaries`
- `learned_path_ids`
- `passed_scenario_summaries`
- `failed_scenario_summaries`
- `unverified_scenario_summaries`
- `unsupported_capability_summaries`
- `evidence_warnings`

If these fields are unavailable, child 2 implementation must stop rather than infer outcome from one alias.

## Aggregate Result Shape

Either extend `LearningRunResult` or add a wrapper such as `LearningBatchResult`.

Required fields:

- `learning_outcome`
- `summary`
- `capabilities_learned`
- `capabilities_failed`
- `capabilities_unverified`
- `capabilities_unsupported`
- `learned_path_ids`
- `run_ids`
- `discovery_batch_id`
- `evidence_warnings`
- `catalog_actions`

`catalog_actions` must contain only passed capabilities that survived control-term filtering.

## Outcome Derivation

Suggested derivation:

```text
passed_count = count(passed capabilities with learned_path_id)
failed_or_unsupported_count = count(failed + unsupported capabilities)
unverified_count = count(unverified capabilities)
systemic_blocker = provider failure, browser failure, page unreachable, no trustworthy observation

if passed_count > 0 and not systemic_blocker and failed_or_unsupported_count == 0 and unverified_count == 0:
  success
elif passed_count > 0:
  partial_success
elif unverified_count > 0 and not passed_count:
  unverified
else:
  failed
```

The exact implementation may differ, but it must preserve the contract semantics.

## Chat Runtime Changes

Expected affected area:

- `apps/api/app/services/conversation/chat_runtime.py`

Change learning completion logic to:

1. consume aggregate learning result
2. derive or accept `learning_outcome`
3. build user-facing feedback from capability summaries
4. generate session learned action metadata only from passed capabilities
5. apply control-term filtering before adding any catalog action

Remove feedback dependency on a single `{alias}` template.

## Control Term Filter

Implement a reusable guard that can be tested independently.

Inputs:

- raw user text
- normalized candidate alias
- generated utterances
- business_goal
- canonical_goal
- match_terms

Output:

- accepted identity fields, or
- rejection reason

The filter should be applied before:

- LearnedPath identity generation where this package touches it
- current session learned action catalog insertion
- suggested utterance generation for chat feedback

## Feedback Builder

Add a deterministic feedback builder for learning outcomes.

Examples:

- success:
  `我学会了按状态搜索、按邮箱搜索。你可以直接告诉我想做什么，比如“搜索启用用户”或“按邮箱查用户”。`
- partial_success:
  `我学会了按状态搜索和按邮箱搜索；地区筛选还没有确认成功。你可以先让我搜索启用用户，详情可在后台查看。`
- failed:
  `这次学习失败了，我还没有学会这个页面上的可执行操作。你可以在后台查看本次学习详情：/conversation/history/<session_id>。`
- unverified:
  `我已经尝试学习，但证据不足，还不能确认学会。详情可在后台查看：/conversation/history/<session_id>。`

Wording should be finalized in code/tests, but must preserve these semantics.

## History / Debug Timeline

Expected affected areas:

- conversation history service
- conversation router schemas if needed
- Console history detail if already exposing timeline fields
- CLI history detail display if applicable

Learning timeline item should show:

- outcome
- discovery batch id
- passed capability count
- failed / unverified / unsupported count
- run ids
- learned path ids
- evidence warnings

Do not dump raw provider request/response bodies to terminal logs as the primary solution.

## CLI Session Start

`wagent chat` session start should include a concrete backend history path:

```text
本次会话 ID：<session_id>。需要调试时可以在后台查看：/conversation/history/<session_id>
```

The exact base URL can remain user-configured; the path must be visible.

## Compatibility

- Existing learned actions remain executable.
- Explicit business learning scenarios can still generate natural aliases such as login or create record.
- Existing conversation history payloads remain readable.
- Failed/unverified runs may appear in history but must not appear as learned actions.

## Non-goals

- No child 1 discovery implementation.
- No observability mega-project beyond learning outcome details.
- No live autonomous run by default.
- No direct autonomous-run endpoint calls from coding agents.
