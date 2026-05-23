# 测试计划（Test Plan）

状态：draft_for_review（pending choice eval 设计稿，未实现代码）

## Test Strategy

本迭代测试分五层：

- runner unit tests：验证 pending choice gates、redaction 和 setup manifest。
- runtime integration tests：仅在新增 eval-only setup hook 时验证 hook 默认关闭和 opt-in。
- case tests：验证 `pending_choice_multi_candidate` artifact / exit code。
- safety tests：验证不调用 autonomous-run / direct replay endpoint，不泄露 private payload。
- optional live eval：只有服务可用且明确执行时才记录 live evidence。

## Unit Tests

| ID | Test | Expected |
|---|---|---|
| UT-1 | setup manifest has fewer than 3 candidates | `setup_multi_candidate_current_eval=fail` |
| UT-2 | pending choice event missing | `pending_choice_created=fail` |
| UT-3 | public choices missing C | `public_choices_abc_visible=fail` |
| UT-4 | public payload contains `learned_path_id` | `public_choice_payload_sanitized=fail` |
| UT-5 | public event contains `pending_choice_private_map` | `public_choice_payload_sanitized=fail` |
| UT-6 | planner event present | `planner_not_invoked=fail` |
| UT-7 | A turn executes B path | `execution_uses_choice_A_path=fail` |
| UT-8 | pending choice remains after A selection | `pending_choice_cleared=fail` |
| UT-9 | reporter not verified | `execution_verified=fail` |
| UT-10 | raw request log contains direct replay endpoint | `no_autonomous_or_direct_replay=fail` |

## Integration Tests

Only required if implementation adds eval-only candidate setup hook.

| ID | Test | Expected |
|---|---|---|
| IT-1 | hook metadata absent | runtime behavior unchanged |
| IT-2 | `client != wagent_eval` | hook ignored |
| IT-3 | invalid case id | hook ignored |
| IT-4 | fake learned path id | hook rejected or case blocked |
| IT-5 | valid setup ids | learned actions bound, no public id leak |
| IT-6 | hook event payload | no learned path id / private map / selector |

## Runner Case Tests

| ID | Test | Expected |
|---|---|---|
| CASE-1 | invalid API preflight | status `blocked`, exit `2`, artifact written |
| CASE-2 | synthetic pending choice evidence all gates pass | status `pass`, exit `0` for non-live evaluator test |
| CASE-3 | choice A executes wrong learned path | status `fail`, exit `1` |
| CASE-4 | public payload leak | status `fail`, exit `1` |
| CASE-5 | timeout during choice dispatch | status `timeout`, exit `3` |

## Safety Checks

Run source grep before review:

```bash
rg -n "autonomous-runs|run_autonomous_exploration|learned-paths/.*/replay|/replay" \
  scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py docs/testing/wagent-runtime-eval.md
```

Expected: no matches for runner-initiated autonomous run or direct replay API usage. If `/replay` appears only
as documentation of a prohibited endpoint, review must call that out explicitly.

## Verification Commands

Expected non-live commands:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q -k "pending_choice"
cd ../..
uv run ruff check \
  scripts/evals/wagent_runtime_eval.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/tests/test_wagent_runtime_eval.py \
  apps/api/tests/test_conversation_chat_runtime.py
uv run ruff format --check \
  scripts/evals/wagent_runtime_eval.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/tests/test_wagent_runtime_eval.py \
  apps/api/tests/test_conversation_chat_runtime.py
git diff --check
.venv/bin/python scripts/evals/wagent_runtime_eval.py --help
```

If package script is added:

```bash
pnpm run eval:wagent:pending-choice --api-base http://127.0.0.1:9
```

Expected for invalid API: blocked result, exit `2`, artifact written.

## Live Eval

Live Conversation eval is optional for this iteration review unless the user explicitly asks to run it and the
required services are available.

If live eval is run, review must include:

- command。
- API base。
- product URL。
- session id。
- setup manifest summary。
- JSON artifact path。
- Markdown result path。
- exit code。
- required gate summary。

If live eval is not run, review must explicitly say:

```text
Live Conversation eval: not run
```
