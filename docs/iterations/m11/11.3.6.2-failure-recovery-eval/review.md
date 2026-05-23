# 评审记录（Review）

状态：implementation_complete_non_live（non-live checks passed，live Conversation eval not run）

## Current Decision

- Reviewer: ChatGPT
- Decision: implementation_passed_non_live
- Code: implemented
- Live eval: not_run
- Notes:
  - failure trigger contract 稳定且不污染普通 runtime。
  - recovery gates source / pass semantics 清楚。
  - private payload redaction 覆盖 retry / relearn / cancel。
  - live eval not-run 规则清楚。
  - 2026-05-23 已完成非 live implementation review；live Conversation eval 未运行。

## Design Summary

本迭代计划在 11.3.6.1 runner core 之上增加 `failure_recovery_menu_safety` case，
验证 11.3.5.8 基础失败恢复菜单和 private payload safety。

## Review Checklist

- [x] failure trigger contract 稳定且不污染普通 runtime。
- [x] recovery gates 有明确 source 和 pass / fail semantics。
- [x] private payload redaction 覆盖 retry / relearn / cancel 私有载荷。
- [x] happy path no-recovery gate 不依赖 Codex 主观判断。
- [x] direct replay / autonomous-run 边界清楚。
- [x] live eval not-run 规则清楚。

## Not Run

- 未运行 live Conversation eval。
- 未触发 autonomous run。

## Implementation Closeout

### Actual Delivery

- `scripts/evals/wagent_runtime_eval.py`
  - 新增 `failure_recovery_menu_safety` case。
  - 新增 failure recovery hard gates：
    `failure_triggered`、`recovery_menu_shown`、`retry_wording_safe`、
    `retry_side_effect_warning`、`relearn_option_shown`、`cancel_option_shown`、
    `private_payload_not_visible`、`recovery_events_sanitized`、
    `verified_happy_path_no_recovery`、`no_autonomous_or_direct_replay`。
  - Markdown result 对 failure recovery case 显式输出 live eval / trigger / retry
    not-run 边界。
- `apps/api/app/services/conversation/chat_runtime.py`
  - 新增最小 eval-only hook。只有 `client=wagent_eval` 且
    `eval_fault_injection.case_id=failure_recovery_menu_safety`、allowlisted
    `reporter_outcome=needs_review` 时生效。
  - hook 不绕过 Conversation API dispatch，只把本次 eval turn 的 reporter outcome
    降级为 `needs_review`，并写入脱敏 `eval_fault_injection_applied` event。
- `apps/api/tests/test_wagent_runtime_eval.py`
  - 覆盖 recovery menu gates、private payload leak gates、blocked artifact case、
    Markdown boundary、history message echo 去重和 hook event redaction scan。
- `apps/api/tests/test_conversation_chat_runtime.py`
  - 覆盖 eval-only hook opt-in 生效、默认关闭、`client != wagent_eval` 忽略、
    invalid outcome 忽略和 hook event 脱敏。
- `package.json`
  - 新增 `pnpm run eval:wagent:failure-recovery`。
- `docs/testing/wagent-runtime-eval.md`
  - 新增 failure recovery case 的运行方式、metadata contract、gate 列表和 not-run
    边界。
- Evidence artifacts:
  - `artifacts/wagent-eval/wagent-runtime-eval-20260522T163632Z.json`
  - `docs/testing/results/m11-11.3.6.2-failure-recovery-eval-20260522T163632Z.md`

### Review Fixes

- P1 fixed:
  `verified_happy_path_no_recovery` no longer treats the same latest recovery reply
  echoed from `history.messages` as a prior happy-path message. The runner now uses
  `/messages` as the primary message source and falls back to `history.messages` only
  when `/messages` is unavailable.
- P2 fixed:
  `recovery_events_sanitized` now scans `eval_fault_injection_applied` in addition to
  `failure_recovery*` events, so hook event private payload leaks fail the hard gate.

### Verification Evidence

| Command / Check | Result |
|---|---|
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_runtime_eval.py -q` | `27 passed` |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_chat_runtime.py -q -k "eval_fault_injection"` | `4 passed, 65 deselected` |
| `uv run ruff check scripts/evals/wagent_runtime_eval.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py` | `All checks passed!` |
| `uv run ruff format --check scripts/evals/wagent_runtime_eval.py apps/api/app/services/conversation/chat_runtime.py apps/api/tests/test_wagent_runtime_eval.py apps/api/tests/test_conversation_chat_runtime.py` | `4 files already formatted` |
| `git diff --check` | pass |
| safety grep for autonomous / direct replay endpoints | no matches |
| `.venv/bin/python scripts/evals/wagent_runtime_eval.py --help` | exit `0` |
| invalid API blocked path | expected exit `2`, blocked JSON / Markdown artifacts written |

### Not Run / Unverified

- Live Conversation eval: not run.
- Retry execution after selecting A: not run; not required by 11.3.6.2.
- `verify-scenario`: not run.
- autonomous-run endpoints: not called.
- Console UI smoke: not run.

### Final Decision

11.3.6.2 implementation is complete for the scoped non-live review. It must remain
marked as `live Conversation eval not run` until a real service-backed eval run records
session id, JSON artifact, Markdown result, exit code and required gate summary.
