# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未实现代码）

## 设计摘要

本包做最小代码修复，不重写 runner 或 runtime 架构。修复分三条线：

```text
pending choice public/private separation
planner choice selection -> execution continuation
runner artifact redaction hardening
```

实现必须先补 regression tests，再改代码。

## 影响文件

主要文件：

- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/conversation/history.py`
- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_conversation_chat_runtime.py`
- `apps/api/tests/test_wagent_runtime_eval.py`

按需更新：

- `docs/testing/wagent-runtime-eval.md`
- `docs/testing/results/*` only after live eval rerun pass。

禁止修改：

- DB migrations。
- public route list。
- TaskPathPlanner ranking algorithm。
- autonomous exploration endpoints。

## Pending Choice Public Payload Fix

Current failure:

```text
public_choice_payload_sanitized failed:
private pending choice token learned_path_id observed in public messages/session/events
```

Implementation requirements:

- Audit public surfaces consumed by `_pending_choice_public_surface()`:
  - `session.metadata.pending_choice`
  - `history.session.metadata.pending_choice`
  - `pending_choice_created` / `pending_choice_retry` events
  - `eval_candidate_setup_applied` events
  - agent messages
- Ensure public pending choice payloads never include `learned_path_id` or `pending_choice_private_map`.
- If private state stays in session metadata, public serializers must strip the whole private map and any
  nested `learned_path_id` keys before returning session / history payloads.
- Do not fix this by weakening runner gates. The runtime payload must become safe.
- Add tests that use real runtime APIs / service outputs, not only synthetic gate fixtures.

Implementation hint:

- `_build_pending_choice()` and `_build_planner_pending_choice()` already produce safe public `choices`.
  The likely leak is from storing / replaying private metadata or eval setup events; fix public serialization
  and event payloads rather than adding private fields to public choices.

## Planner Choice Execution Fix

Current failure:

```text
planner candidates and planner choices created
choice A dispatch succeeded
planner_choice_selected observed
chat_execution_started missing after selection
execution_uses_selected_choice_path / execution_verified / final_response_verified failed
planner_single_path_bypass_regression passed
```

Implementation requirements:

- Keep `planner_choice_selected` event when selected private choice kind is `planner_route_choice`.
- After selection, resolve the selected learned action from the current session's validated learned actions or
  eval-only candidate binding.
- If `_learned_action_by_path_id()` cannot find the action but the selected private choice contains a path id
  that was validated for the current session, build the minimal execution action from the private choice and
  `LearnedPathRepository.get()`; otherwise return the existing unavailable-choice path.
- Call the same execution path as learned action selection: `_execute_matched_action(...)` with selected
  slot overrides.
- Clear pending choice and active clarify state before execution, but preserve events list so
  `planner_choice_selected` and `chat_execution_started` are both observable.
- Do not route single-candidate / explicit direct replay through Planner.

## Runner Artifact Redaction Fix

Current failure:

```text
raw planner rerun output contained a full private path id
raw artifacts were not committed
```

Implementation requirements:

- Redact before artifact write, not only in Markdown summaries.
- Continue redacting static sensitive keys: `pending_choice_private_map`, `slot_overrides`, credentials,
  cookies, authorization, raw `response_text`, planner private payloads.
- Add dynamic private-id redaction:
  - collect full learned path ids from session metadata, setup manifests, events, history, learned path details,
    and raw API responses before writing artifacts;
  - replace exact string occurrences with a stable hash or `[REDACTED]`;
  - never emit full path ids in gate evidence.
- Keep internal evaluator comparisons unchanged; only public artifact / Markdown output is redacted.
- Add a test that fails when a full private path id appears anywhere in serialized artifact text.

## Contract Alignment

- pass / fail remains determined by hard gates.
- Conversation API remains the only runtime driver for eval commands.
- direct replay endpoints and autonomous-run endpoints remain prohibited.
- eval-only candidate binding remains labeled as eval-only; no full live multi-action capability claim.
- blocked / failed artifacts remain historical evidence and are not rewritten.

## Failure Handling

- If pending choice still leaks private fields after fix, do not mark 11.3.6.3 complete.
- If planner choice selection still does not start execution, do not mark 11.3.6.4 complete.
- If artifact redaction catches a leak, fail the implementation review and do not commit unsafe artifacts.
- If services are unavailable during final eval, record blocked but do not close M11.3.6.
