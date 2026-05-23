# 测试计划（Test Plan）

状态：draft_for_review（planner-backed choice eval 设计稿，未实现代码）

## Test Strategy

本迭代测试分五层：

- runner unit tests：验证 planner-backed gates、redaction 和 setup manifest。
- runtime integration tests：仅在新增 eval-only planner setup hook 时验证 hook 默认关闭和 opt-in。
- case tests：验证 `planner_backed_choice` artifact / exit code。
- safety tests：验证不调用 autonomous-run / direct replay endpoint，不泄露 private planner payload。
- optional live eval：只有服务可用且明确执行时才记录 live evidence。

## Unit Tests

| ID | Test | Expected |
|---|---|---|
| UT-1 | setup manifest missing | `setup_planner_candidates_current_eval=fail` |
| UT-2 | setup has fewer than 3 candidates | `setup_planner_candidates_current_eval=fail` |
| UT-3 | planner candidates event missing | `planner_candidates_generated=fail` |
| UT-4 | planner choice event missing | `planner_choice_created=fail` |
| UT-5 | only non-planner pending choice event present | `non_planner_choice_not_used=fail` |
| UT-6 | public choice missing expected options | `public_choices_abc_visible=fail` |
| UT-7 | public choice payload contains `learned_path_id` | `planner_public_payload_sanitized=fail` |
| UT-8 | planner event contains full `learned_path_id` | `planner_event_sanitized=fail` |
| UT-9 | planner event contains selector / slot overrides | `planner_event_sanitized=fail` |
| UT-10 | warning count > 0 but visible text leaks raw warning | `planner_warning_wording_safe=fail` |
| UT-11 | planner top choice not publicly observable | `planner_top_choice_observable=not_observable` |
| UT-12 | selection dispatch missing | `select_planner_choice_dispatched=fail` |
| UT-13 | `planner_choice_selected` missing | `planner_choice_selected=fail` |
| UT-14 | selected choice executes wrong path | `execution_uses_selected_choice_path=fail` |
| UT-15 | pending choice remains after selection | `pending_choice_cleared=fail` |
| UT-16 | reporter not verified | `execution_verified=fail` |
| UT-17 | raw request log contains direct replay endpoint | `no_autonomous_or_direct_replay=fail` |
| UT-18 | artifact response text contains private planner payload | artifact writer redacts it |

## Single-path Regression Tests

| ID | Test | Expected |
|---|---|---|
| REG-1 | one current-session learned action, explicit execute request | direct replay, no planner events |
| REG-2 | planner event appears during single-path execution | `no_planner_choice_created=fail` |
| REG-3 | execution uses old global learned path | `execution_uses_current_learned_path=fail` |

## Integration Tests

Only required if implementation adds eval-only planner candidate setup hook.

| ID | Test | Expected |
|---|---|---|
| IT-1 | hook metadata absent | runtime behavior unchanged |
| IT-2 | `client != wagent_eval` | hook ignored |
| IT-3 | invalid case id | hook ignored |
| IT-4 | fake learned path id in live setup | hook rejected or case blocked |
| IT-5 | valid setup ids | learned actions prepared, no public id leak |
| IT-6 | hook event payload | no full learned path id / private map / selector |
| IT-7 | hook attempts to create planner choice directly | rejected by tests |
| IT-8 | alias binding reuses one path | artifact states `planner_distinct_path_capability=false` |

## Runner Case Tests

| ID | Test | Expected |
|---|---|---|
| CASE-1 | invalid API preflight | status `blocked`, exit `2`, artifact written |
| CASE-2 | synthetic planner-backed evidence all required gates pass | status `pass`, exit `0` for non-live evaluator test |
| CASE-3 | planner event leak | status `fail`, exit `1` |
| CASE-4 | selected choice executes wrong learned path | status `fail`, exit `1` |
| CASE-5 | timeout during planner choice dispatch | status `timeout`, exit `3` |
| CASE-6 | live setup cannot produce candidates and no approved binding exists | status `blocked` or `not_run`, no live pass claim |
| CASE-7 | eval-only planner binding pass | status may pass as planner branch coverage, Markdown states capability flags |

## Safety Checks

Run source grep before review:

```bash
rg -n "autonomous-runs|run_autonomous_exploration|learned-paths/.*/replay|TaskPathPlanner\\(\\)\\.plan" \
  scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py docs/testing/wagent-runtime-eval.md
```

Expected:

- No runner-initiated autonomous run.
- No direct replay API usage in runner.
- No runner direct call to `TaskPathPlanner().plan`.
- Test-only negative fixtures may mention prohibited endpoints, but review must call them out explicitly.

## Verification Commands

Expected non-live commands:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q -k "planner"
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
pnpm run eval:wagent:planner-choice --api-base http://127.0.0.1:9
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
- planner events observed。
- JSON artifact path。
- Markdown result path。
- exit code。
- required gate summary。

If live eval is not run, review must explicitly say:

```text
Live Conversation eval: not run
```
