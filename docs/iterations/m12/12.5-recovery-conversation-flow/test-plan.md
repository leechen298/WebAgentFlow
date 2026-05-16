# 12.5 Recovery Conversation Flow Test Plan

状态：approved for implementation

## 适用条件

本文件必填，因为 12.5 涉及 recovery / conversation flow，且 future matrix 超过
5 个 case。

## 测试范围（Test Scope）

- Unit：required for implementation。覆盖 deterministic recovery conversation flow service。
- Integration：required only if implementation touches conversation orchestrator /
  event / state boundary；不执行 browser 或 retry。
- API：N/A for 12.5 MVP unless implementation explicitly changes existing
  conversation API contract；默认不新增 route。
- Console UI：N/A；12.5 MVP 不新增 UI。
- E2E：not run / out of scope。
- Agent / Reporter / Recovery：unit-level recovery conversation tests。
- Codex / AI External Operator：review only, not test。
- Live autonomous run：explicitly excluded。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | failure boundary | `pytest tests/test_recovery_conversation_flow.py` | response explains failure and shows proposal options when present | Yes | No recovery execution. |
| Unit | blocked boundary | `pytest tests/test_recovery_conversation_flow.py` | asks user for missing context | Yes | No replan. |
| Unit | uncertain result | `pytest tests/test_recovery_conversation_flow.py` | asks review / evidence clarification | Yes | No success claim. |
| Unit | needs_review | `pytest tests/test_recovery_conversation_flow.py` | shows manual review response | Yes | Preserves evidence. |
| Unit | abort accepted_stop | `pytest tests/test_recovery_conversation_flow.py` | acknowledges stop and no new browser action | Yes | User control boundary. |
| Unit | abort cannot_interrupt_inflight_action | `pytest tests/test_recovery_conversation_flow.py` | explains side-effect uncertainty | Yes | No rollback claim. |
| Unit | proposal with `consider_retry_later` | `pytest tests/test_recovery_conversation_flow.py` | shows retry policy result or downstream policy requirement | Yes | Does not start retry. |
| Unit | retry policy `retry_allowed_requires_confirmation` | `pytest tests/test_recovery_conversation_flow.py` | asks for confirmation, no retry execution | Yes | Confirmation marker is not execution. |
| Unit | retry policy `retry_denied` | `pytest tests/test_recovery_conversation_flow.py` | explains denial, no retry execution | Yes | Safe result. |
| Unit | retry policy `retry_needs_more_context` | `pytest tests/test_recovery_conversation_flow.py` | asks for context | Yes | No retry. |
| Unit | retry policy `retry_needs_manual_review` | `pytest tests/test_recovery_conversation_flow.py` | asks review | Yes | No action. |
| Unit | `abandon_task` option | `pytest tests/test_recovery_conversation_flow.py` | can record abandon intent for conversation only | Yes | No browser cleanup. |
| Unit | recommended option display | `pytest tests/test_recovery_conversation_flow.py` | recommended/rank shown but not selected automatically | Yes | Preserves 12.3 boundary. |
| Unit | selected user option | `pytest tests/test_recovery_conversation_flow.py` | represented as `chosen_option_kind`, `conversation_choice`, `requested_next_step`, or equivalent conversation-only marker | Yes | Not execution. |
| Unit | choice naming boundary | `pytest tests/test_recovery_conversation_flow.py` | response / payload does not expose `selected_action`, `execute_choice`, `run_choice`, or `retry_choice` fields | Yes | Prevents field names that imply execution. |
| Unit | choice execution boundary marker | `pytest tests/test_recovery_conversation_flow.py` | user choice preserves `non_executable`, `execution_boundary`, or equivalent marker | Yes | Choice is not command. |
| Unit | input immutability | `pytest tests/test_recovery_conversation_flow.py` | recovery inputs are not mutated | Yes | Pure service. |
| Unit | forbidden dependency scan | `pytest tests/test_recovery_conversation_flow.py` | no browser/network/LLM/retry/replan/LearnedPath write-back imports | Yes | Scope guard. |
| Integration | orchestrator/event wrapping | `pytest tests/test_conversation_recovery_flow.py` | event payload records response and choice boundaries only | Conditional | Required only if implementation touches orchestrator. |
| Integration | event enum boundary | `pytest tests/test_conversation_recovery_flow.py` | implementation reuses existing event payload mechanisms by default; any new `ConversationEventType` / `ConversationStatus` is explicitly documented and covered | Conditional | Required only if implementation touches orchestrator/state enums. |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 12.5 implementation MVP does not require browser or product UI validation.
- 不得声称完成 UI smoke / E2E unless a future scoped task actually runs those
  surfaces and records evidence.
- 12.5 implementation MVP 不需要 UI smoke unless implementation explicitly scopes
  a product UI surface.

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

12.5 implementation does not require Codex / AI to act as an external product
test operator.

如果后续要运行 product-driven browser execution，必须记录实际入口、操作路径、
截图或可复查输出，并按根 `AGENTS.md` 报告 pass gate / run_id。

## Live Run 边界（Live Run Boundary）

本次不运行：

- `verify-scenario`
- autonomous run
- product-driven browser execution
- Console UI smoke
- E2E

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| API tests | 12.5 MVP 默认不新增 route 或 response contract。 | If implementation changes existing conversation API, add focused API tests in that task. |
| CLI tests | 12.5 MVP 默认不改 CLI。 | If implementation changes CLI, add focused CLI tests in that task. |
| E2E / UI smoke | 12.5 MVP 不接 UI 或 browser flow。 | UI behavior remains `not run` / `unverified` unless explicitly scoped later. |
| `verify-scenario` / autonomous run | 12.5 MVP 不触发 live autonomous run。 | Product live runtime remains `not run` / `unverified` unless explicitly requested later. |
