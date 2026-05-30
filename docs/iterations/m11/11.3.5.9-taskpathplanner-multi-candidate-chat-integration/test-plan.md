# 测试计划（Test Plan）

状态：implementation complete（code review passed，targeted tests passed）

## 适用条件

本包接入 TaskPathPlanner 到 `wagent chat` multi-candidate path，涉及 Runtime routing、
private map、安全 payload 和单路径回归，必须维护 `test-plan.md`。

## 测试范围（Test Scope）

- Unit：TaskIntent adapter、candidate adapter、Runtime ranked candidates -> pending choice mapping、
  planner top-candidate signal mapping。
- Integration：InteractiveChatRuntime + mocked replay handler + session learned actions。
- API：如 public session payload 或 event payload sanitizer 被触及，补 conversation API 回归。
- Console UI：N/A。
- Live `wagent chat`：默认不要求。
- Live autonomous run：N/A，明确禁止。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | AD-1 build TaskIntent from intake | helper | raw_text / normalized_goal / hints set | Yes | no LLM |
| Unit | AD-2 candidates limited to session actions | helper | no candidate outside session learned_actions | Yes | security |
| Unit | AD-3 deprecated path excluded | helper | deprecated candidate not executable | Yes | planner also filters |
| Unit | MAP-1 runtime candidates to visible choice | helper | A/B/C labels, no path id | Yes | sanitized |
| Unit | MAP-2 runtime candidate + planner signal to private map | helper | private map has learned_path_id / slot_overrides | Yes | runtime only |
| Unit | MAP-3 planner unable | helper | no executable private map | Yes | no replay |
| Unit | MAP-4 planner does not supply alternatives | helper | choices come from ranked session candidates | Yes | planner output is top route only |
| Integration | PL-1 multi-candidate invokes planner | chat runtime | planner called once, pending_choice created | Yes | mocked planner |
| Integration | PL-2 vague request invokes planner | chat runtime | “处理一下这个页面” enters planner choice | Yes | no direct guess |
| Integration | PL-3 single candidate skips planner | chat runtime | direct replay, planner not called | Yes | `/records` regression |
| Integration | PL-4 choice selection executes selected path | chat runtime | selecting A calls replay for private path | Yes | no Router |
| Integration | PL-5 selection preserves slot_overrides | chat runtime | `record_name` retained through private map | Yes | 11.3.5.4 regression |
| Integration | PL-6 planner unable asks clarification | chat runtime | no replay, no executable private map | Yes | conservative |
| Integration | PL-7 flaky / provisional warning shown safely | chat runtime | description has warning, no id | Yes | risk display |
| Integration | PL-8 URL plus vague action invokes planner | chat runtime | URL is target hint, not skip condition | Yes | no `not user_url` gate |
| Integration | PL-9 "继续" respects live context | chat runtime | pending / active / recovery handled before planner | Yes | priority |
| Security | SEC-1 WAgent reply no path id | output text | no `learned_path_id` / selected path | Yes | user visible |
| Security | SEC-2 pending_choice public no path id | session metadata | public choice has no private id | Yes | 11.3.5.7 invariant |
| Security | SEC-3 progress events no private payload | events | no path id / slot overrides / route raw steps / slot values | Yes | event safety |
| Security | SEC-4 planner fallback event sanitized | events | fallback records no private payload | Yes | reviewability |
| Preflight | PF-1 11.3.5.7 / 11.3.5.8 tests pass | targeted tests | choice / recovery base is available | Yes | dependency gate |
| Regression | REG-1 `/records` single path happy path | chat runtime | no planner, replay succeeds | Yes | P0 protection |
| Regression | REG-2 failure recovery choice unaffected | chat runtime | recovery A/B/C still works | Yes | 11.3.5.8 protection |
| Regression | REG-3 pending choice parser unaffected | chat runtime | A / 1 / 第一个 still match | Yes | 11.3.5.7 protection |

## 建议命令

Targeted chat runtime:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  -k "planner or pending_choice or recovery or items"
```

Planner service regression:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_task_planning_retrieval.py \
  tests/test_task_planning_preview.py \
  tests/test_task_planning_schemas.py
```

Conversation safety slice:

```bash
cd apps/api
PYTHONPATH=. ../../.venv/bin/pytest \
  tests/test_conversation_chat_runtime.py \
  tests/test_conversation_api.py \
  tests/test_conversation_entry_gate.py \
  tests/test_conversation_router_agent.py
```

Lint / diff:

```bash
cd apps/api
uv run ruff check \
  app/services/conversation/chat_runtime.py \
  tests/test_conversation_chat_runtime.py

git diff --check
```

## 不运行 / 不声明

| Item | Reason | Follow-up |
|---|---|---|
| `verify-scenario` | 本包不是 autonomous exploration 验证 | 不运行 |
| autonomous run | 明确禁止 | 不运行 |
| Console UI smoke | 本包默认 service/runtime tests | 如用户显式要求再做 |
| live `wagent chat` closed loop | 11.3.5.6 已覆盖 P0；本包可后续人工验收 | 不作为默认 required |

## 验收门槛

实现阶段不得只证明 Planner 被 import。必须证明：

```text
multi-candidate chat branch
-> TaskPathPlanner called
-> sanitized pending_choice created
-> choices are Runtime-ranked session candidates, not Planner alternatives
-> private map preserves selected learned_path_id and slot overrides
-> user choice executes selected path
-> single-path happy path bypasses Planner
-> live pending / active / recovery context has priority over Planner
```
