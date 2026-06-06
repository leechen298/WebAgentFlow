# 契约（Contract）

状态：proposed

## 概念 / 边界契约

`BrowserEventTimeline` 是一次 autonomous run 或 attempt 期间浏览器事件的 bounded、redacted、
ordered metadata list。它只回答“浏览器层发生了什么”，不回答“操作是否成功”。

Event recorder 是 engineering service，不是产品 Agent。它不得生成 terminal verdict，不得直接决定
LearnedPath ingest，不得改变 action planner 或 Playwright execution semantics。

## 状态 / 结果契约

Event recording result:

- `recording_available`：timeline 正常采集。
- `recording_partial`：部分事件采集失败或达到 bounded limit，但已有事件可用。
- `recording_unavailable`：无法挂载 recorder 或 page/context 不支持事件。

Recorder failure must be non-fatal by default. Exploration should continue with warning metadata unless child
implementation review explicitly authorizes fail-closed for a narrow case.

## Schema / API 契约

Logical event shape:

```text
BrowserEvent {
  event_id
  event_type
  occurred_at
  correlation_id
  run_id?
  attempt_id?
  action_id?
  page_id?
  frame_url_origin?
  frame_path?
  metadata
  redaction_warnings
}
```

Required `event_type` values:

- `request`
- `response`
- `requestfailed`
- `download`
- `dialog`
- `popup`
- `framenavigated`
- `load`
- `domcontentloaded`
- `console`
- `pageerror`

Metadata must be safe-by-default:

- URLs may store scheme, host, path template and safe query-key inventory, but not raw secret query values.
- Headers may store allowlisted names only; cookies and auth headers are forbidden.
- Request body is forbidden in v1.
- Response body is forbidden in v1.
- Download metadata may store suggested filename after filename sanitization, MIME/type when known, size when safe,
  but not file content.
- Dialog metadata may store dialog type and bounded redacted message.
- Console/pageerror metadata may store type and bounded redacted message/stack summary.

Storage direction:

- v1 should prefer existing JSON payload surfaces such as run / strategy / result metadata until a later child proves
  a dedicated table is required.
- Because current `run_id` is created at persistence time after autonomous execution, runtime event entries must use
  a stable `correlation_id` plus `attempt_id` / `step_index` / `action_id` during execution. Persisted summaries may
  attach the final `run_id` after the `ExplorationRun` row exists.
- Old runs without event timeline must remain readable.
- Event timeline payload must be size-bounded and truncate deterministically.

## Evidence / Observation 契约

Allowed evidence:

- Playwright page/context event metadata.
- Event timestamps and event ordering.
- Correlation ids assigned by WebAgentFlow runtime.
- Redaction warnings and truncation metadata.

Disallowed evidence:

- Raw secret-bearing URLs or headers.
- Raw request/response body.
- File content from downloads.
- Direct user personal identifiers when not necessary for terminal-state reasoning.
- Codex commentary or external operator natural language.

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：BrowserEventTimeline feeds L1 terminal-state classification / Attempt Evaluation handoff.
- Scope boundary 对齐：code records browser events; Agent later evaluates bounded evidence.
- Roadmap / milestone 对齐：M11.3 post-closeout implementation slice; M14 may reuse timeline as learning quality evidence.
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- Existing exploration runs without event timelines remain readable.
- Recorder unavailable / partial status must not crash existing autonomous exploration by default.
- Existing pass_gate / Supervisor scorecard semantics remain unchanged.
- Existing LearnedPath ingest behavior remains unchanged in child 2.

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变，除非 child implementation review explicitly scopes additive read-model metadata.
- Database schema：默认不变；dedicated table requires separate design review.
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不变。

## 非目标

- 不实现 terminal verdict。
- 不实现 stop/wait/continue policy。
- 不实现 Attempt Evaluation prompt changes。
- 不实现 Console evidence presentation。
- 不运行 live validation。

## 未决问题

- Implementation review must confirm exact hook point after reading current Playwright page/context lifecycle.
- Implementation review must choose final JSON storage field and truncation limit.
- Implementation review must confirm whether popup child pages need independent timeline ids in v1.
