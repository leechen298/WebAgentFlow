# 测试计划（Test Plan）

状态：ready_for_implementation（design review passed，未开始实现）

## 适用条件

本包涉及 runtime failure handling、pending choice recovery、retry / relearn / cancel
状态流转，必须维护 `test-plan.md`。

## 测试范围（Test Scope）

- Unit：failure classification、recovery choice payload、private map sanitizer。
- Integration：InteractiveChatRuntime + mocked replay / learning handler。
- API：只在 public sanitizer 变化时补 session / history API 回归。
- Console UI：N/A。
- E2E：N/A，本包默认不要求 live `wagent chat`。
- Live autonomous run：N/A，明确禁止。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | FC-1 replay failed classification | helper | `failure_class=replay_failed` | Yes | no LLM |
| Unit | FC-2 evidence missing classification | helper | `failure_class=evidence_missing` | Yes | replay succeeded but no verified evidence |
| Unit | FC-3 reporter needs_review | helper | `failure_class=needs_review` | Yes | no success claim |
| Unit | RC-1 recovery visible payload | helper | A/B/C only, no private id | Yes | no `learned_path_id` |
| Unit | RC-2 recovery private map | helper | retry / relearn / cancel payload exists internally | Yes | metadata only |
| Integration | FR-1 replay failed offers recovery | chat runtime | response has failure explanation + A/B/C | Yes | mocked replay failed |
| Integration | FR-2 evidence missing offers recovery | chat runtime | response does not say success, offers A/B/C | Yes | Reporter `needs_review` / `uncertain` |
| Integration | FR-3 blocked offers recovery | chat runtime | blocked wording + A/B/C | Yes | drift / URL mismatch |
| Integration | RT-1 choose A retry | chat runtime | replay called again with same learned path / slot overrides | Yes | no Planner；文案提示会再次执行 |
| Integration | RT-2 retry preserves evidence target | chat runtime | `record_name` evidence target rebuilt | Yes | `/records` regression |
| Integration | RT-3 retry failure does not loop | chat runtime | no automatic retry loop | Yes | may offer recovery again |
| Integration | RL-1 choose B relearn | chat runtime | learning branch starts, no immediate replay | Yes | `learn_then_execute` remains blocked |
| Integration | RL-2 relearn missing info | chat runtime | writes pending and asks missing info | Yes | target / goal missing |
| Integration | CAN-1 choose C cancel | chat runtime | clears pending choice / active task | Yes | same as 11.3.5.7 cleanup |
| Integration | CAN-2 Chinese cancel | chat runtime | clears recovery state | Yes | “算了” |
| Security | SEC-1 WAgent reply no id | output text | no `learned_path_id` / private map | Yes | visible only |
| Security | SEC-2 Router / LLM trace no private map | trace payload | no recovery private map | Yes | if trace path touched |
| Security | SEC-3 recovery events no private payload | conversation events | no path id / slot overrides / evidence targets / private retry payload | Yes | public diagnostics only |
| Regression | REG-1 verified happy path | targeted tests | no recovery menu on verified result | Yes | 11.3.5.6 preserved |
| Regression | REG-2 pending choice normal selection | targeted tests | 11.3.5.7 choice still works | Yes | recovery kind does not break learned_action kind |

## 推荐验证命令

```bash
cd apps/api

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_api.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py \
  tests/test_learning_run_service.py

uv run ruff check \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/conversation/context.py \
  apps/api/app/services/conversation/history.py \
  apps/api/tests/test_conversation_chat_runtime.py \
  apps/api/tests/test_conversation_api.py

git diff --check
```

如果实现没有触及 API sanitizer，可说明未运行 `test_conversation_api.py` 的原因。

## E2E / UI Smoke 边界

- 本包不要求 live browser 或 product UI smoke。
- 如果只运行 unit / integration tests，必须写成 targeted tests passed。
- 不得把 mocked replay retry 说成真实网页恢复成功。

## Live Run 边界

本包不运行：

- `verify-scenario`
- `POST /exploration/autonomous-runs`
- `POST /exploration/autonomous-runs/stream`
- in-process `run_autonomous_exploration`

如果误运行，必须记录为越界，不得作为本包通过证据。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| `verify-scenario` | 本包是 chat runtime recovery，不是 L1 autonomous verification | 无，明确禁止 |
| autonomous run | 不属于本包 | 无，明确禁止 |
| Console UI smoke | 本包不改 Console | Console recovery UI 未来另做 |
| TaskPathPlanner | 属于 11.3.5.9 | 本包直接 retry / relearn / cancel |
| Full `/records` live closed loop | 已由 11.3.5.6 验证成功路径 | 本包只做失败恢复 targeted tests |
