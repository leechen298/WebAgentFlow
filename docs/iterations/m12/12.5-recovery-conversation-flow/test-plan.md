# 12.5 Recovery Conversation Flow Test Plan

状态：proposed

## 适用条件

本文件必填，因为 12.5 涉及 recovery / conversation flow，且 future matrix 超过
5 个 case。

## 测试范围（Test Scope）

- Unit：future required。覆盖 deterministic recovery conversation flow service。
- Integration：future limited conversation-flow tests。仅覆盖 conversation
  orchestrator / event boundary，不执行 browser 或 retry。
- API：N/A for design package；12.5 design package 不新增 route。
- Console UI：N/A；12.5 design package 不新增 UI。
- E2E：not run / out of scope。
- Agent / Reporter / Recovery：future unit-level recovery conversation tests。
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
| Unit | selected user option | `pytest tests/test_recovery_conversation_flow.py` | represented as conversation choice only | Yes | Not execution. |
| Unit | input immutability | `pytest tests/test_recovery_conversation_flow.py` | recovery inputs are not mutated | Yes | Pure service. |
| Unit | forbidden dependency scan | `pytest tests/test_recovery_conversation_flow.py` | no browser/network/LLM/retry/replan/LearnedPath write-back imports | Yes | Scope guard. |
| Integration | orchestrator/event wrapping | `pytest tests/test_conversation_recovery_flow.py` | event payload records response and choice boundaries only | Future | Only if implementation touches orchestrator. |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本次设计包生成没有真实打开浏览器或产品 UI。
- 本次不得声称完成 UI smoke / E2E。
- 12.5 implementation MVP 不需要 UI smoke unless implementation explicitly scopes
  a product UI surface.

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

本次 Codex / AI 只做文档编辑和静态检查，不作为外部测试操作员运行产品。

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
| Unit tests | 本次提交只生成设计包，不创建 recovery conversation code。 | Future implementation must run `test_recovery_conversation_flow.py` and recovery regressions. |
| Integration tests | 本次不接 orchestrator / event runtime。 | Future implementation must run limited integration tests if it touches orchestrator/state. |
| API tests | 12.5 design package 不新增 route 或 response contract。 | None for docs-only package. |
| CLI tests | 12.5 design package 不改 CLI。 | None for docs-only package. |
| E2E / UI smoke | 12.5 design package 不接 UI 或 browser flow。 | UI behavior unverified, by design. |
| `verify-scenario` / autonomous run | 12.5 design package 不触发 live autonomous run。 | Product runtime not exercised, by design. |
