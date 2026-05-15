# 12.4 Retry / Re-run Policy Test Plan

状态：proposed

## 适用条件

本文件必填，因为 12.4 涉及 recovery / retry policy，且 future unit matrix
超过 5 个 case。

## 测试范围（Test Scope）

- Unit：future required。覆盖 deterministic retry policy evaluator。
- Integration：N/A for 12.4 implementation MVP；不接 conversation flow、API 或 DB。
- API：N/A；12.4 不新增 route 或 response contract。
- Console UI：N/A；12.4 不新增 UI。
- E2E：not run / out of scope。
- Agent / Reporter / Recovery：future unit-level retry policy tests。
- Codex / AI External Operator：review only, not test。
- Live autonomous run：explicitly excluded。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | `consider_retry_later` + clear evidence | `pytest tests/test_retry_policy.py` | `retry_allowed_requires_confirmation` | Yes | Does not start retry. |
| Unit | `consider_retry_later` + `side_effects_unknown` | `pytest tests/test_retry_policy.py` | `retry_denied` | Yes | Fail-closed. |
| Unit | `consider_retry_later` + missing evidence | `pytest tests/test_retry_policy.py` | `retry_needs_more_context` | Yes | Does not infer safety. |
| Unit | `abandon_task` proposal | `pytest tests/test_retry_policy.py` | `no_retry_needed` | Yes | No retry path; preserve risk evidence without treating abandon as retry failure. |
| Unit | `review_evidence` proposal | `pytest tests/test_retry_policy.py` | `retry_needs_manual_review` | Yes | Manual review boundary. |
| Unit | abort `accepted_stop` | `pytest tests/test_retry_policy.py` | `retry_denied` unless future user-confirmed path exists | Yes | Abort boundary remains active. |
| Unit | abort `cannot_interrupt_inflight_action` | `pytest tests/test_retry_policy.py` | `retry_denied` | Yes | Side effects may be unknown. |
| Unit | `success_no_recovery_needed` | `pytest tests/test_retry_policy.py` | `no_retry_needed` | Yes | No retry after success. |
| Unit | non-idempotent action risk | `pytest tests/test_retry_policy.py` | `retry_denied` | Yes | Prevent duplicate side effects. |
| Unit | irreversible action possible | `pytest tests/test_retry_policy.py` | `retry_denied` | Yes | Fail-closed. |
| Unit | unsupported replay state | `pytest tests/test_retry_policy.py` | `retry_denied` | Yes | No unsupported retry. |
| Unit | missing user confirmation | `pytest tests/test_retry_policy.py` | `retry_allowed_requires_confirmation`, not `retry_started` | Yes | Policy result only. |
| Unit | input immutability | `pytest tests/test_retry_policy.py` | Input models are not mutated. | Yes | Pure evaluator. |
| Unit | forbidden dependency scan | `pytest tests/test_retry_policy.py` | No DB/browser/network/LLM/conversation dispatcher/retry execution/LearnedPath write-back imports. | Yes | Scope guard. |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本次设计包生成没有真实打开浏览器或产品 UI。
- 本次不得声称完成 UI smoke / E2E。
- 12.4 implementation MVP 不需要 UI smoke；后续 12.5 conversation flow 若接 UI，
  再另行设计。

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
| Unit tests | 本次提交只生成设计包，不创建 retry policy code。 | Future implementation must run `test_retry_policy.py` and recovery regressions. |
| API tests | 12.4 design package 不新增 route 或 response contract。 | None for docs-only package. |
| CLI tests | 12.4 design package 不改 CLI。 | None for docs-only package. |
| E2E / UI smoke | 12.4 design package 不接 UI 或 browser flow。 | UI behavior unverified, by design. |
| `verify-scenario` / autonomous run | 12.4 design package 不触发 live autonomous run。 | Product runtime not exercised, by design. |
