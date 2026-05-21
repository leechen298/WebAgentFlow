# 测试计划（Test Plan）

状态：ready_for_implementation（design review passed，未开始实现）

## 适用条件

本包涉及 conversation runtime 状态、Router / LLM 可见边界、cancel、replay 前置选择和
active task ledger，必须维护 `test-plan.md`。

## 测试范围（Test Scope）

- Unit：choice parser、metadata helpers、active task helpers、expiry / cleanup helpers。
- Integration：InteractiveChatRuntime + in-memory conversation repo / mocked learning / replay。
- API：默认不新增 API；可通过 existing tests 间接验证 metadata / event payload。
- Console UI：N/A。
- E2E：N/A，本包不要求 live `wagent chat` closed-loop。
- Agent / Reporter / Recovery：只验证 Router 安全边界；不做 Reporter / recovery。
- Codex / AI External Operator：N/A，除非后续用户明确要求 live smoke。
- Live autonomous run：N/A，明确禁止。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | PC-1 create pending choice | runtime helper | visible payload has choice ids / labels only | Yes | no private id in visible object |
| Unit | PC-2 private map persisted | runtime helper | private map keyed by choice id, internal only | Yes | can inspect metadata in test |
| Unit | SEL-1 parse `A` | choice parser | selects first choice | Yes | deterministic |
| Unit | SEL-2 parse `1` | choice parser | selects first choice | Yes | deterministic |
| Unit | SEL-3 parse `第一个` | choice parser | selects first choice | Yes | deterministic |
| Unit | SEL-4 label match | choice parser | matches exact / normalized label | Yes | no LLM needed |
| Unit | EXP-1 turns remaining decrements | runtime helper | invalid answer decrements | Yes | at zero clears |
| Unit | EXP-2 expired choice cleanup | runtime helper | pending choice and private map removed | Yes | asks user to restate |
| Integration | PC-3 multiple learned actions | chat runtime | writes `pending_choice` and asks A/B/C | Yes | seed learned_actions |
| Integration | SEL-5 choose A dispatches | chat runtime | clears choice and enters selected branch | Yes | mocked replay / ask branch acceptable |
| Integration | REV-1 correction input | chat runtime | clears choice and reruns intake | Yes | “不是，我要搜索” |
| Integration | CAN-1 `/cancel` cleanup | chat runtime | clears pending_intake / target / choice / active_task | Yes | existing cancel regression extended |
| Integration | CAN-2 Chinese cancel cleanup | chat runtime | “算了” clears runtime state | Yes | if supported in current command path |
| Integration | AT-1 clarify task | chat runtime | writes `active_task.kind=clarify` waiting for user | Yes | pending choice or missing info |
| Integration | AT-2 learning task | chat runtime | learning start writes active task, success clears/completes | Yes | mocked learning |
| Integration | AT-3 execution task | chat runtime | execution start writes active task, completion clears/completes | Yes | mocked replay |
| Security | SEC-1 no id in WAgent reply | output text | no `learned_path_id` / UUID in A/B/C reply | Yes | private map stays internal |
| Security | SEC-2 no id in Router payload | router trace / request payload | no private map / learned_path_id in LLM-facing payload | Yes | if router trace test exists |
| Regression | REG-1 single `/items` action | targeted runtime tests | direct replay path unchanged | Yes | no TaskPathPlanner |
| Regression | REG-2 11.3.5.4/5 targeted suite | pytest | parameterized replay + evidence tests still pass | Yes | prevents P0 regression |

## 推荐验证命令

```bash
cd apps/api

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py

PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_replay_hook.py \
  tests/test_task_planning_result_reporter.py \
  tests/test_learned_path_replay.py \
  tests/test_learning_run_service.py

uv run ruff check \
  apps/api/app/services/conversation/context.py \
  apps/api/app/services/conversation/entry_gate.py \
  apps/api/app/services/conversation/chat_runtime.py \
  apps/api/app/services/conversation/router_agent.py \
  apps/api/tests/test_conversation_chat_runtime.py \
  apps/api/tests/test_conversation_entry_gate.py \
  apps/api/tests/test_conversation_router_agent.py

git diff --check
```

如果实现不触及 `router_agent.py` 或对应 tests，可在 `review.md` 中说明 scoped ruff / pytest
的实际文件集。

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本包不要求真实浏览器或 live `wagent chat` smoke。
- 如果只运行 unit / integration tests，必须写成 targeted tests passed，不得写 E2E passed。
- 如果后续用户要求 live smoke，可用 `wagent chat` 验证 choice mode，但必须保存 transcript、
  session id 和 events，不得调用 autonomous run。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 可以运行 targeted tests、读事件 payload、检查 diff。没有真实运行 CLI 或浏览器时，
不得声称完成 CLI / E2E / UI smoke。

## Live Run 边界（Live Run Boundary）

本包不运行：

- `verify-scenario`
- `POST /exploration/autonomous-runs`
- `POST /exploration/autonomous-runs/stream`
- in-process `run_autonomous_exploration`

如果误运行，必须记录为越界，不得作为本包通过证据。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| `verify-scenario` | 本包是 conversation state robustness，不是 L1 autonomous verification | 无；明确禁止 |
| autonomous run | 不属于本包 | 无；明确禁止 |
| Console UI smoke | 本包不改 Console | Console choice UI 未来另做 |
| TaskPathPlanner multi-candidate | 属于 11.3.5.9 | 本包只能用已有 learned_actions 构造 choice |
| Failure Recovery menu | 属于 11.3.5.8 | 失败出口后续补 |
| Full `/items` closed loop | 已由 11.3.5.6 验证 | 本包只做 targeted regression |
