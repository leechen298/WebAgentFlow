# Implementation Plan

## Inputs and Dependencies

Future implementation must inspect the current task planning schemas,
conversation events, execution service, and replay result shape before choosing
the final module boundary.

Expected inputs:

- `plan_execution_started` event;
- `plan_execution_completed` event;
- `plan_execution_failed` event;
- `plan_execution_blocked` event;
- replay run id / execution id if available;
- learned path id;
- target URL or replay entry context;
- route summary;
- replay-level error summary;
- `no_result_verification` marker from 11.1.6;
- `no_autonomous` marker from 11.1.6;
- existing `PostconditionSignal`, `TaskExecutionResult`,
  `AgentEReporterInput`, or `AgentEReporterOutput` schema fields when stable.

Potential implementation locations:

- inspect existing task planning schemas before choosing the final path;
- likely under `apps/api/app/services/task_planning/` for result verification
  and reporter logic;
- conversation integration likely under `apps/api/app/services/conversation/`;
- tests likely under `apps/api/tests/`.

This documentation package does not create code files.

## Verification Input Evidence

11.1.7 must consume execution evidence. It must not reconstruct results from raw
user text.

Allowed evidence sources may include:

- 11.1.6 execution events;
- replay result summary;
- explicit postcondition signals;
- artifact references;
- route summary or terminal route step metadata;
- manually provided verification signal;
- stable external system response summary if already present.

11.1.7 must not:

- infer success from replay completion alone;
- call replay again;
- call retrieval or Task Path Planner again;
- infer target URL or result state from raw user text;
- read raw HTML;
- call Page Understanding Agent;
- call LLM provider;
- open a browser for a second check.

## Verification Outcome Semantics

First-version outcome semantics:

- `verified`: explicit postcondition evidence supports task success.
- `failed`: replay failed, or negative evidence proves the intended result did
  not happen.
- `uncertain`: replay completed, but evidence is insufficient to prove the
  business result.
- `needs_review`: user or later system review is required before marking the
  task successful.
- `blocked`: execution did not happen, or verification cannot run because
  required evidence is missing.

Default rule:

```text
plan_execution_completed + no postcondition evidence -> uncertain / needs_review
```

`verified` requires evidence. It is not the default.

## Postcondition Evidence Boundary

Future postcondition evidence may include:

- URL changed or stayed at an expected URL;
- page title or known success marker if already captured in structured form;
- known success message;
- artifact reference exists;
- replay action log reached an expected terminal step;
- stable external response summary if available;
- manually provided verification signal.

First-version 11.1.7 must stay conservative. If available evidence cannot prove
the result, return `uncertain` or `needs_review`.

This package must not introduce:

- raw HTML parsing;
- Page Understanding Agent calls;
- LLM-based result judgment;
- browser re-open / second pass verification;
- autonomous relearning;
- recovery execution.

## Task Result Reporter Output

Task Result Reporter turns the verification outcome into a user-facing report.

The report may include:

- replay execution completed / failed / blocked;
- verification outcome;
- evidence used;
- evidence missing;
- whether user review is needed;
- no recovery attempted;
- no autonomous learning started.

The report must not claim:

- task success unless outcome is `verified`;
- form submission success without postcondition evidence;
- artifact production without an artifact reference;
- external system completion without evidence.

## AgentEReporter Schema Relationship

11.1.1 may keep schema class names such as `AgentEReporterInput` and
`AgentEReporterOutput` for compatibility.

Documentation and implementation language should use the primary role name:
Task Result Reporter. Agent E is a legacy alias and should only appear where
compatibility with older naming is useful.

11.1.7 should not casually change 11.1.1 schemas. If implementation discovers a
schema hardening need, it must be explicit, minimal, and covered by tests.

## Conversation Event Recording

Future event semantics may include:

- `result_verification_completed`;
- `result_verification_failed`;
- `result_verification_uncertain`;
- `task_result_reported`.

Event payload should include:

- execution event id or replay run id if available;
- learned path id;
- verification outcome;
- evidence summary;
- missing evidence summary;
- user-facing report summary;
- `no_recovery: true`;
- `no_autonomous: true`;
- `no_llm: true` when applicable.

Event payload must not include:

- raw HTML;
- screenshot payload;
- user/account/tenant fields;
- unsupported success assertion.

## Conversation State Transition Options

Future implementation may introduce or reuse statuses with these semantics:

```text
execution_finished -> result_verified
execution_finished -> result_uncertain
execution_failed -> result_failed
execution_blocked -> result_blocked
```

This documentation package does not modify schemas.

Required rule:

```text
verified state requires evidence.
uncertain / needs_review is valid when verification evidence is incomplete.
```

## Assistant Message Behavior

Verified:

```text
The replay completed and the expected result was verified based on available evidence.
```

Uncertain:

```text
Replay completed, but I could not verify the business result from available evidence. Please review the target page or provide a verification signal.
```

Failed:

```text
Replay execution failed before result verification. No recovery was attempted.
```

Blocked:

```text
Result verification could not run because execution was blocked or required evidence is missing.
```

Needs review:

```text
The replay evidence is incomplete. Manual review is needed before marking the task successful.
```

Exact wording can change during implementation. The semantics must remain
evidence-bound.

## Recovery Boundary

11.1.7 does not recover.

When verification is failed, uncertain, or needs review:

- do not re-run replay;
- do not call Failure Recovery Agent;
- do not start autonomous run;
- do not repair learned paths;
- do not enter teaching mode.

This package only reports `failed`, `uncertain`, `needs_review`, or `blocked`.

## Test Plan

Future implementation tests should cover:

- `plan_execution_completed` without postcondition evidence returns
  `uncertain` or `needs_review`;
- explicit postcondition evidence can produce `verified`;
- replay failure produces `failed`;
- execution blocked produces `blocked`;
- reporter does not claim task success for `uncertain`, `needs_review`,
  `failed`, or `blocked`;
- evidence summary and missing evidence summary are populated;
- no raw HTML, autonomous, LLM, Page Understanding Agent, replay re-run, or
  recovery imports;
- AgentEReporter schema compatibility remains intact if reused;
- event payload does not include raw HTML, screenshot payload, or
  user/account/tenant fields.

## Evidence Plan

Future implementation review should record:

- changed files;
- verification input examples;
- outcome examples for verified / failed / uncertain / needs_review / blocked;
- reporter message examples;
- event payload examples;
- proof that replay completed is not reported as task success;
- proof that recovery was not attempted;
- test commands and results.

## Out-of-Scope Items

11.1.7 does not do:

- replay execution;
- replay re-execution;
- autonomous run;
- hidden relearning;
- raw HTML planning or parsing;
- LLM-based verification;
- Page Understanding Agent invocation;
- slot binding;
- form filling;
- recovery dialogue;
- teaching mode;
- browser exploration;
- full deterministic E2E;
- evidence report aggregation;
- 11.1.8 detail directory creation.

## Implementation Decision Closure

以下决策收口 11.1.7 第一版实现中会影响代码结构的 open questions。它们是 future implementation decisions；本文档不修改代码、schema、API endpoint 或 CLI command。

### 1. First-version verification evidence source

第一版只消费已有结构化 evidence。允许来源：

```text
plan_execution_started / plan_execution_completed / plan_execution_failed / plan_execution_blocked events
ConversationReplaySummary (replay_status, drift_status, drift_reasons, final_url, final_title, step_count, error)
learned_path_id from execution event payload
target_url / replay entry context from execution event payload
route_summary from execution event payload if available
error_summary from failed/blocked execution events
no_result_verification marker from 11.1.6
no_autonomous marker from 11.1.6
task_verified=false marker from 11.1.6
```

禁止来源：

```text
raw HTML parsing
DOM scraping
screenshot interpretation
Page Understanding Agent invocation
LLM judgment
browser second pass / re-open
autonomous run
```

如果没有 postcondition evidence，默认 outcome 必须是：

```text
uncertain / needs_review
```

不得默认 verified。

### 2. Postcondition evidence first-version strategy

11.1.7 第一版不新增复杂 postcondition source。可以接受的 evidence：

```text
explicit structured postcondition signal if already present in execution payload or task planning schema
artifact reference if already present
replay summary terminal status (succeeded/observed vs drifted/failed)
drift_status and drift_reasons
error_summary from replay or exception
manual verification signal if a future code path already provides it
```

不允许：

```text
raw HTML parsing
DOM scraping
screenshot interpretation
Page Understanding Agent
LLM judgment
browser second pass
autonomous run
```

### 3. Outcome semantics

第一版 outcome 语义：

```text
verified   — 明确 postcondition evidence 支持成功
failed     — replay failed / drifted / error_summary 明确失败
uncertain  — replay completed，但没有足够 evidence 证明业务成功
needs_review — evidence 不足，需要用户或后续系统检查
blocked    — execution 没发生，或缺少 verification input
```

默认规则（写死）：

```text
plan_execution_completed + no postcondition evidence -> uncertain
```

如果需要更保守，也可以是：

```text
uncertain + needs_review flag
```

`verified` 不是默认。`verified` 需要明确 evidence 支持。

注意：现有 `TaskExecutionStatus` Literal 定义在 11.1.1 schema 中为 `["succeeded", "failed", "uncertain", "needs_review"]`，不含 `"verified"` 或 `"blocked"`。实现时若复用该 schema，需明确映射关系（如 `verified` -> `"succeeded"` 并附加 `verification_source` 字段，或 `blocked` -> `"failed"` 并附加 `failure_stage="verification"`）。如果实现发现必须扩展 schema，应列为独立 implementation task 并补 schema tests。本轮文档阶段不修改 schema。

### 4. Uncertain and needs_review persistence

第一版 service output 保留两者语义，但 conversation persisted status 先不拆太细。

推荐：

```text
verification outcome: uncertain
needs_review: true
```

如果未来新增 `ConversationStatus`，再单独评估：

```text
result_verified / result_failed / result_uncertain / result_blocked
```

本轮不修改 `ConversationStatus` enum。

### 5. Event semantics

未来实现可以新增最小事件语义：

```text
result_verification_completed
task_result_reported
```

如果需要区分失败 / uncertain，用 payload `outcome` 表达，而不是第一版就膨胀 event enum。

Event payload 建议：

```text
execution_event_id / replay_run_id if available
learned_path_id
verification_outcome
evidence_summary
missing_evidence_summary
report_summary
task_verified
needs_review
no_recovery: true
no_autonomous: true
no_llm: true
```

禁止 payload 包含：

```text
raw HTML
screenshot payload
user/account/tenant fields
unsupported success assertion
```

### 6. Task Result Reporter service boundary

未来实现可以新增：

```text
apps/api/app/services/task_planning/result_reporter.py
```

或等价路径。实现前必须 inspect 当前 code structure。

职责：

```text
consume execution evidence
derive verification outcome
build user-facing report
build event payload
```

不得：

```text
execute replay
re-run replay
call recovery
call autonomous
call LLM
read raw HTML
call Page Understanding Agent
```

### 7. AgentEReporter schema relationship

- 文档主名称使用 **Task Result Reporter**。
- `AgentEReporterInput` / `AgentEReporterOutput` 作为 11.1.1 legacy schema 名称保留，不删除、不重命名。
- 第一版尽量复用现有 schema。如果需要新字段，优先在 service result type 中表达，再映射到 schema。
- 不为了方便随意改 11.1.1 schema。
- 如果实现发现必须 schema hardening，单独列为 implementation task，并补 schema tests。

### 8. Conversation integration strategy

第一版可以在 `execution_finished` / `execution_failed` 后，通过现有 conversation dispatch 或 orchestrator branch 触发 reporting。

但必须明确：

```text
11.1.7 不执行 replay。
11.1.7 只消费已经存在的 execution events。
```

触发方式待实现前进一步确认（推荐方案）：

```text
automatic after execution_finished / execution_failed: orchestrator immediately appends report after execution result event
or explicit user asks for result/report
```

推荐：**automatic after execution**，因为 replay 完成后用户通常期望立即看到结果汇报，而不是再次输入指令。如果 automatic 实现有副作用风险，可以退回到 explicit。

### 9. Recovery boundary

明确：

```text
failed / uncertain / needs_review 不触发 recovery。
```

不会：

```text
replay again
autonomous run
Failure Recovery Agent
hidden relearning
teaching mode
```

## Open Questions

以下问题仍然 open，待实现前或实现中确认：

- Exact service file path after inspecting current code structure（`services/task_planning/result_reporter.py` 或 `services/conversation/result_reporter.py`？）
- Exact `ConversationEventType` names if new events are added（`result_verification_completed` vs `task_result_reported` 的命名风格需与现有 event type 保持一致）
- Whether reporting is automatic after execution or requires explicit user input（推荐 automatic，但需实现时验证无副作用）
- Whether `ConversationStatus` needs `result_verified` / `result_failed` / `result_uncertain` states in first implementation，或继续复用 `execution_finished` / `execution_failed` 并附加 verification metadata
