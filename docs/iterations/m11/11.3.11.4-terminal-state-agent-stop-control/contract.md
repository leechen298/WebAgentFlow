# 契约（Contract）

状态：PACKAGE_COMPLETE

## 概念 / 边界契约

`TerminalStateVerdict` 是 attempt-level advisory summary。它回答“是否有足够 evidence 进入
Attempt Evaluation”，不回答“是否应保存 LearnedPath”。

`ExplorationStopController` 第一版是 deterministic policy helper，不是产品 Agent。它不得直接点击、
等待浏览器、重试、恢复或写 LearnedPath。

## 状态 / 结果契约

`terminal_outcome`:

- `terminal_detected`
- `terminal_unverified`
- `not_terminal_yet`
- `terminal_failed`

`stop_decision`:

- `stop`
- `wait`
- `continue`
- `unverified_stop`

`evidence_strength`:

- `strong`
- `medium`
- `weak`
- `none`

## Schema / API 契约

Logical shape:

```text
TerminalStateVerdict {
  terminal_outcome
  terminal_type
  evidence_strength
  evidence_summary
  stop_decision
  warnings[]
  matched_event_ids[]
  matched_hint_ids[]
  matched_evidence[]
  missing_evidence[]
  needs_more_wait
  max_wait_reached
  source
}
```

Any result metadata field is optional and backward compatible.

## Evidence / Observation 契约

Allowed inputs:

- `browser_event_timeline`
- `page_terminal_hints`
- step logs / final_state summary

Disallowed:

- direct endpoint calls;
- Codex natural-language verdicts;
- target-specific route/label/selector rules;
- raw secrets or unredacted evidence.

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：supports L1 terminal-state classification before Attempt Evaluation.
- Scope boundary 对齐：classification only; no browser operation.
- Roadmap / milestone 对齐：M11.3 post-closeout; child 5 owns ingest gate.
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- Missing timeline/hints returns `terminal_unverified` or `continue`, not false success.
- Request-start evidence without response/load/failure evidence returns `wait` before a bounded wait limit and
  `unverified_stop` after `max_wait_reached`.
- `stop` is allowed only when medium/strong terminal evidence is present and not contradicted by failure evidence.
- `continue` is not success; it only means the first classifier saw no terminal evidence.
- Existing result consumers keep working.
- No DB migration.

## 不变契约

本轮不改变 pass_gate、Supervisor、LearnedPath ingest、replay status、recovery/abort。

## 非目标

- 不实现 provider-backed Terminal State Agent prompt。
- 不实现 real bounded wait loop mutation.
- 不保存 successful LearnedPath。

## 未决问题

- Later child may make stop_decision actually control exploration loop timing.
- Child 5 decides ingest eligibility.
