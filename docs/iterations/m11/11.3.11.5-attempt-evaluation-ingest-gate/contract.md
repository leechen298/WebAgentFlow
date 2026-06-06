# 契约（Contract）

状态：PACKAGE_COMPLETE

## 概念

`AttemptIngestEvaluation` 是 attempt-level deterministic gate summary。它回答：

- 这个 attempt 是否具备 LearnedPath ingest eligibility？
- 为什么允许或拒绝？
- 哪些 terminal / pass_gate / action evidence 被使用？

它不回答：

- Supervisor verdict 是否成功。
- 页面真实业务任务是否满足。
- LearnedPath 是否应该被 operator trust promotion。

## 输出状态

`ingest_status`:

- `eligible`
- `ineligible`
- `unverified`

`attempt_outcome`:

- `success_candidate`
- `failed`
- `unverified`
- `not_terminal`

`failure_category`:

- `terminal_unverified`
- `terminal_failed`
- `terminal_not_reached`
- `pass_gate_not_pass`
- `no_effective_actions`
- `missing_terminal_evidence`
- `none`

## 输入契约

Allowed inputs:

- `final_data.terminal_state_verdict`
- existing `pass_gate.status` from scorecard / final data
- action step logs used for LearnedPath trimming
- final_state summary / redacted evidence ids

Disallowed inputs:

- raw request / response bodies
- target-specific URL / selector / label hardcoding
- Codex-authored natural-language success claims
- direct autonomous endpoint calls

## Gate Rules

- `eligible` requires:
  - `pass_gate.status == "pass"`;
  - `terminal_state_verdict.terminal_outcome == "terminal_detected"`;
  - `terminal_state_verdict.stop_decision == "stop"`;
  - `evidence_strength in {"medium", "strong"}`;
  - at least one effective action remains after existing action trimming.
- `terminal_unverified`, `not_terminal_yet`, `terminal_failed`, `unverified_stop`, `wait` or `continue`
  must not be eligible.
- Browser-event terminal evidence must carry action correlation (`matched_action_ids`,
  `matched_step_indices`, or `matched_action_types`). A detected terminal type without action correlation is
  `unverified`, not eligible.
- Missing terminal verdict is `unverified`, not pass.
- Existing old runs without terminal verdict remain readable; this child only affects new ingest decisions
  where terminal verdict metadata exists.

## Persistence / Compatibility

- No DB migration in first version.
- The ingest evaluation may be stored in existing flexible JSON payloads only if runtime implementation is
  authorized.
- `learned_paths` schema and trust lifecycle remain unchanged.

## Non-goals

- No UI display.
- No live run.
- No negative knowledge table.
- No replacement of Attempt Evaluation Agent.
