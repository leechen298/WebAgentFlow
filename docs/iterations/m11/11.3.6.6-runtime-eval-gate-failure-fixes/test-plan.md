# 测试计划（Test Plan）

状态：draft_for_review

## 测试目标

证明 11.3.6.5 service-available rerun 暴露的 required gate failures 已被修复，并且修复没有破坏
single-path bypass、pending choice private map、artifact redaction 或 existing runner behavior。

## Unit / Targeted Tests

| ID | Test | Expected |
|---|---|---|
| UT-1 | pending choice public payload contains only safe fields | no `learned_path_id`, `pending_choice_private_map`, `slot_overrides`, selector, ReplayAction |
| UT-2 | pending choice private map still resolves selection A | A selection reaches `chat_execution_started` for expected path |
| UT-3 | `eval_candidate_setup_applied` event sanitized | event exposes only case id, setup type, counts, hashes / flags |
| UT-4 | planner route choice selection starts execution | `planner_choice_selected` followed by `chat_execution_started` |
| UT-5 | planner selected choice uses expected path internally | public evidence uses hash / match, not full id |
| UT-6 | planner single-path bypass remains direct replay | no planner candidates / choice events; execution verified |
| UT-7 | artifact writer redacts dynamic private path ids | serialized JSON / Markdown contains no full private path id |
| UT-8 | raw `response_text` with private ids is redacted | output does not contain raw id or private map |

## Required Commands

Run from `apps/api`:

```bash
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q -k "pending_choice or eval_candidate_binding or planner"
```

Run from repo root:

```bash
uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py
uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py
git diff --check
```

## Required Eval Rerun

With API and product-test-site reachable:

```bash
pnpm run eval:wagent:pending-choice
pnpm run eval:wagent:planner-choice
```

Pass criteria:

- Both commands exit `0`.
- `pending_choice_multi_candidate` status is `pass`.
- `planner_backed_choice` status is `pass`.
- `planner_single_path_bypass_regression` status is `pass`.
- JSON / Markdown artifacts are written.
- Artifact grep does not find full private ids or private payload markers.

## Artifact Safety Checks

Run against newly generated pass artifacts:

```bash
rg -n "pending_choice_private_map|private_retry_payload|ReplayAction|authorization|cookie|token|secret|selector|xpath" <new-artifacts>
```

Also run a strict private-id grep using the learned path ids from the eval logs / sessions. Expected result:

```text
no full private learned path id appears in committed JSON / Markdown artifacts
```

If strict private-id grep finds a full id, do not commit the artifact; fix redaction first.

## Not Run / Out of Scope

- `verify-scenario`: not run.
- autonomous-run endpoints: not called.
- Console UI smoke: not required.
- DB migration tests: not applicable unless implementation changes schema, which this contract forbids.

## Acceptance Criteria

The implementation can be considered ready for 11.3.6.5 closeout rerun only when all required commands pass
and both eval commands exit `0`. Passing unit tests without live eval pass is not enough for this fix package.
