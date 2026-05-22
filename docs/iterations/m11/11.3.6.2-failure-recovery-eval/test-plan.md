# 测试计划（Test Plan）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## Test Strategy

本迭代测试分五层：

- runner unit tests：验证 gate evaluator 和 redaction。
- runtime integration tests：仅在新增 eval-only hook 时验证 hook 生效条件和默认关闭。
- case tests：验证 `failure_recovery_menu_safety` artifact / exit code。
- safety tests：验证不调用 autonomous-run / direct replay endpoint，不泄露 private payload。
- optional live eval：只有服务可用且明确执行时才记录 live evidence。

## Unit Tests

| ID | Test | Expected |
|---|---|---|
| UT-1 | recovery menu A/B/C detected | `recovery_menu_shown=pass` |
| UT-2 | retry wording is generic `重试` | `retry_wording_safe=fail` |
| UT-3 | side-effect warning missing for `needs_review` | conditional gate fails or warns according to contract |
| UT-4 | relearn option missing | `relearn_option_shown=fail` |
| UT-5 | cancel option missing | `cancel_option_shown=fail` |
| UT-6 | visible payload contains `learned_path_id` | `private_payload_not_visible=fail` |
| UT-7 | event payload contains `slot_overrides` | `recovery_events_sanitized=fail` |
| UT-8 | happy path contains recovery menu | `verified_happy_path_no_recovery=fail` |
| UT-9 | fixture-only case tries to mark live pass | fail or explicit not-run warning |

## Integration Tests

Only required if implementation adds eval-only fault injection hook.

| ID | Test | Expected |
|---|---|---|
| IT-1 | hook metadata absent | runtime behavior unchanged |
| IT-2 | `client != wagent_eval` | hook ignored |
| IT-3 | invalid fault class | request rejected or hook ignored safely |
| IT-4 | `needs_review` hook | recovery menu path entered |
| IT-5 | hook event payload | no private retry payload / selector / slot overrides |

## Runner Case Tests

| ID | Test | Expected |
|---|---|---|
| CASE-1 | invalid API preflight | status `blocked`, exit `2`, artifact written |
| CASE-2 | synthetic recovery evidence all gates pass | status `pass`, exit `0` for non-live evaluator test |
| CASE-3 | recovery menu missing | status `fail`, exit `1` |
| CASE-4 | private payload leak | status `fail`, exit `1` |
| CASE-5 | timeout during evidence collection | status `timeout`, exit `3` |

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
cd ../..
uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py
uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py
git diff --check
.venv/bin/python scripts/evals/wagent_runtime_eval.py --help
```

If package script is added:

```bash
pnpm run eval:wagent:failure-recovery --api-base http://127.0.0.1:9
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
- JSON artifact path。
- Markdown result path。
- exit code。
- required gate summary。

If live eval is not run, review must explicitly say:

```text
Live Conversation eval: not run
```
