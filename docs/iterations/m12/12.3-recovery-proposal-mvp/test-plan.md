# 12.3 Recovery Proposal MVP Test Plan

状态：implemented

## 适用条件

本文件必填，因为 12.3 涉及 recovery，并且 future unit matrix 超过 5 个 case。

## 测试范围（Test Scope）

- Unit：implemented。覆盖 deterministic recovery proposal generator。
  35 tests passed（commit `b139aab`）。
- Integration：N/A for 12.3 implementation MVP；不接 conversation flow、API 或 DB。
- API：N/A；12.3 不新增 route 或 response contract。
- Console UI：N/A；12.3 不新增 UI。
- E2E：not run / out of scope。
- Agent / Reporter / Recovery：unit-level recovery proposal tests 已实现。
- Codex / AI External Operator：review only, not test。
- Live autonomous run：explicitly excluded。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Unit | failure boundary -> review / retry / reteach options | `pytest tests/test_recovery_proposal.py` | Emits `review_evidence`, `consider_retry_later`, or `suggest_reteach` according to boundary recommendation. | Yes | `consider_retry_later` is not retry. |
| Unit | blocked boundary | `pytest tests/test_recovery_proposal.py` | Emits `ask_user_for_context` with evidence refs. | Yes | No browser continuation. |
| Unit | uncertain boundary | `pytest tests/test_recovery_proposal.py` | Emits `review_evidence`. | Yes | Does not claim success. |
| Unit | needs_review boundary | `pytest tests/test_recovery_proposal.py` | Emits `review_evidence`. | Yes | Keeps evidence refs. |
| Unit | abort `accepted_stop` | `pytest tests/test_recovery_proposal.py` | Emits `abandon_task`, `review_evidence`, or later handoff options without execution. | Yes | Preserves no-new-action boundary. |
| Unit | abort `cannot_interrupt_inflight_action` | `pytest tests/test_recovery_proposal.py` | Emits `review_evidence` with side-effects-unknown risk hint. | Yes | Does not promise rollback. |
| Unit | all options non-executable | `pytest tests/test_recovery_proposal.py` | Every option has `non_executable=true`. | Yes | Default must be stable. |
| Unit | recommended option is not auto-selected | `pytest tests/test_recovery_proposal.py` | Output has no selected option state. | Yes | `recommended != selected`. |
| Unit | no `selected_option_id` | `pytest tests/test_recovery_proposal.py` | Proposal schema/output has no `selected_option_id` or equivalent. | Yes | Allows `recommended_option_ids`, `rank`, `priority`. |
| Unit | retry option handoff only | `pytest tests/test_recovery_proposal.py` | Retry-related output is only `consider_retry_later` and requires 12.4 policy. | Yes | No retry command. |
| Unit | re-teach handoff only | `pytest tests/test_recovery_proposal.py` | `suggest_reteach` does not write LearnedPath. | Yes | No hidden relearning. |
| Unit | takeover handoff only | `pytest tests/test_recovery_proposal.py` | `handoff_to_takeover_later` does not implement takeover. | Yes | Future owner only. |
| Unit | runtime observation handoff only | `pytest tests/test_recovery_proposal.py` | `wait_for_runtime_observation_later` does not implement M11.2. | Yes | No M11.2 dependency. |
| Unit | input immutability | `pytest tests/test_recovery_proposal.py` | Input `RecoveryBoundary` / `AbortAcknowledgement` is not mutated. | Yes | Pure generator. |
| Unit | forbidden dependency scan | `pytest tests/test_recovery_proposal.py` | No DB/browser/network/LLM/conversation dispatcher/retry execution/LearnedPath write-back imports. | Yes | Scope guard. |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本轮没有真实打开浏览器或产品 UI。
- 本轮不得声称完成 UI smoke / E2E。
- 12.3 implementation MVP 不需要 UI smoke；后续 12.5 conversation flow 若接 UI，再另行设计。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

本轮 Codex / AI 只做文档编辑和静态检查，不作为外部测试操作员运行产品。

如果后续要运行 product-driven browser execution，必须记录实际入口、操作路径、
截图或可复查输出，并按根 `AGENTS.md` 报告 pass gate / run_id。

## Live Run 边界（Live Run Boundary）

本轮不运行：

- `verify-scenario`
- autonomous run
- product-driven browser execution
- Console UI smoke
- E2E

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| API tests | 12.3 不新增 route 或 response contract。 | None. |
| CLI tests | 12.3 不改 CLI。 | None. |
| E2E / UI smoke | 12.3 不接 UI 或 browser flow。 | UI behavior unverified, by design. |
| `verify-scenario` / autonomous run | 12.3 不触发 live autonomous run。 | Product runtime not exercised, by design. |
