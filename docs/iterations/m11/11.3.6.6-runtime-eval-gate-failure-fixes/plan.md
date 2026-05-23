# 实施计划（Plan）

状态：ready_for_implementation（design review passed，未实现代码）

## Step 1：复核失败证据

- Read `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T095709Z.md`.
- Read 11.3.6.3 / 11.3.6.4 / 11.3.6.5 `review.md`.
- Confirm current runner cases and package scripts still exist.

## Step 2：先补 red tests

Add targeted tests before implementation:

- pending choice public surface leak regression。
- planner route choice A selection must start execution。
- artifact writer must redact full dynamic private path id。
- single-path bypass must remain pass。

Run the new targeted tests once and confirm they fail for the expected reasons.

## Step 3：修 pending choice public/private separation

- Audit runtime public payload construction and serializers.
- Ensure `pending_choice` public payloads contain no private keys.
- Ensure public session / history strip private map and nested `learned_path_id`.
- Ensure private map still supports A/B/C selection internally.

## Step 4：修 planner choice execution continuation

- Update planner route choice selection path so selected A resolves to executable learned action.
- Preserve `planner_choice_selected` event.
- Ensure `_execute_matched_action(...)` is called for selected planner route choice.
- Preserve direct single-path bypass behavior.

## Step 5：修 runner artifact redaction

- Add dynamic private-id redaction before artifact write.
- Redact raw response text / JSON / gate evidence / events / history / messages.
- Add a final serialized artifact assertion in tests: no full private path id survives.

## Step 6：跑 targeted verification

From `apps/api`:

```bash
PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q
PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q -k "pending_choice or eval_candidate_binding or planner"
```

From repo root:

```bash
uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py
uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py
git diff --check
```

## Step 7：跑 required eval

With services reachable:

```bash
pnpm run eval:wagent:pending-choice
pnpm run eval:wagent:planner-choice
```

If either command returns exit `1`, keep package status `implementation_review_failed` and record the failing
gate. Do not mark M11.3.6 complete.

If either command returns exit `2`, record blocked and rerun after services are available. Do not mark complete.

## Step 8：artifact safety check

- Inspect new JSON / Markdown artifacts.
- Run sensitive grep and strict private-id grep.
- Do not commit raw artifacts that leak full private ids.

## Step 9：review and handoff

- Update this package `review.md` with actual tests, eval outputs, artifacts, and not-run items.
- If both required evals exit `0`, hand off to 11.3.6.5 closeout rerun to update program status.
- If gates still fail, open a follow-up fix package with the new failing gate evidence.

## Commit Boundary

Recommended commit message after implementation passes:

```text
fix: repair runtime eval gate failures
```

Keep generated unsafe raw artifacts out of the commit.
