# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

Child 1 已将 terminal-state classification 定义为 L1 attempt trial 和 Attempt Evaluation 之间的
evidence contract。当前 runtime 已有 Playwright execution、autonomous explorer、wait result、
ExplorationRun JSON payload 和 learning run history，但没有独立的 browser event timeline contract。

本包先定义 event recorder 的 implementation design；runtime code 只有在 review 授权后才能修改。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Event recorder is code service, not Agent | Add service under learning/execution boundary, no prompt | unit tests / code review | No internal Agent role change |
| Required event types recorded | Register Playwright listeners for request/response/requestfailed/download/dialog/popup/framenavigated/load/domcontentloaded/console/pageerror | synthetic event tests | Hook exact page/context after implementation inspection |
| Safe-by-default redaction | Central redaction helpers for URL, headers, messages, filenames | redaction tests | Request/response body forbidden |
| Attempt correlation | Timeline entries include correlation_id/attempt_id/step_index/action_id when available | correlation tests | run_id may attach after persistence |
| Recorder failure non-fatal | recorder status + warnings, no crash by default | failure tests | Fail-closed requires later authorization |
| Old runs readable | event timeline optional | compatibility tests | Missing timeline -> not available |

## 实现方案（Proposed Implementation）

Expected implementation units:

- `apps/api/app/services/execution/browser_event_recorder.py` or equivalent focused module close to Playwright lifecycle.
- Optional schema helpers under existing learning schemas if concrete DTOs are needed.
- Integration hook in `ExecutionRuntime._create_context()` after `new_context()` / `new_page()` creates the
  Playwright context/page, plus a narrow autonomous explorer step/action correlation hook.
- JSON serialization into existing run metadata/result payload until a later package justifies a dedicated table.
- Focused tests under `apps/api/tests/test_browser_event_recorder.py` and targeted integration tests around autonomous explorer metadata if implementation touches it.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No by default | No new endpoint | Existing run detail may later expose additive metadata |
| API response schema | No by default | Child 6 owns read-model display | Keep timeline internal metadata in child 2 |
| Database schema / migration | No | Use existing JSON payload direction | Dedicated table out of scope |
| CLI | No | N/A | N/A |
| Console UI | No | N/A | Child 6 |
| Conversation events | No | N/A | Child 6 may summarize later |
| Replay execution | No | N/A | This is autonomous learning only unless review extends |
| Reporter | No | N/A | Child 5/6 |
| Worker / async jobs | No | N/A | N/A |
| Tests / fixtures | Yes | Unit/integration tests for recorder | Non-live only |
| Docs | Yes | This child docs and review | Already in scope |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

V1 data shape is logical, optional and JSON-serializable:

- `browser_event_timeline.status`
- `browser_event_timeline.events[]`
- `browser_event_timeline.truncated`
- `browser_event_timeline.event_count`
- `browser_event_timeline.redaction_warnings[]`
- `browser_event_timeline.recorder_warnings[]`
- `browser_event_timeline.correlation_id`

Concrete field placement should prefer existing run JSON payloads and must be recorded in implementation review.
Current runtime creates `run_id` after exploration completes and the `ExplorationRun` row is persisted, so implementation
should not force a pre-created run row only to satisfy event correlation. Use runtime `correlation_id` first and attach
`run_id` after persistence if needed.

## 服务 / 模块设计（Service / Module Design）

Suggested public surface:

```text
BrowserEventRecorder.start(page, context, correlation_id, attempt_id?) -> recorder
recorder.bind_action(action_id, step_index?, action_type?)
recorder.snapshot() -> BrowserEventTimeline
recorder.stop() -> BrowserEventTimeline
sanitize_browser_event(event) -> BrowserEvent
```

The recorder should:

- attach listeners once per page/context;
- maintain bounded in-memory event list;
- redact as events are captured;
- tolerate listener errors;
- support action correlation by setting current action id around action execution;
- detach listeners on stop where Playwright API supports it.
- avoid storing selectors, raw `target_selector`, raw request/response body, cookies, authorization headers or full
  console args.

## 数据流（Data Flow）

```text
autonomous run starts
  -> recorder attaches to page/context
  -> attempt starts with attempt_id
  -> action starts with action_id
  -> Playwright emits events
  -> recorder redacts and appends bounded entries
  -> action/attempt completes
  -> timeline snapshot added to attempt/run metadata
  -> later child consumes timeline for terminal-state classification
```

## 状态推导（Status / State Derivation）

- If listeners attach and at least zero events can be represented -> `recording_available`.
- If listener attach succeeds but event conversion/redaction errors occur -> `recording_partial` with warnings.
- If attach fails or page/context unavailable -> `recording_unavailable` with warning.
- If event count exceeds bound -> `recording_partial`, `truncated=true`.

## 兼容性（Compatibility）

- Missing `browser_event_timeline` is valid.
- Timeline truncation must preserve earliest critical events and latest recent events according to implementation review.
- Event recorder must not mutate request/response, block navigation or consume dialogs differently from existing runtime.

## 失败 / 边界情况（Failure / Edge Cases）

- Download event without file metadata: record event with warning.
- Dialog event with sensitive text: redact bounded message.
- Request URL contains tokens: strip values and warn.
- Console/pageerror contains secrets: redact known token patterns and bound length.
- Popup opens a child page: record popup event and page id; full child-page tracking may be follow-up unless implementation review authorizes it.
- Recorder stop called twice: idempotent.
- `run_id` unavailable during execution: keep `correlation_id` and let persistence attach run-level linkage later.

## 非目标（Non-goals）

- No terminal-state verdict.
- No LearnPath ingest change.
- No UI rendering.
- No live validation.

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Unit synthetic events | Event conversion and ordering with fake page/context emitters | `test-plan.md` unit matrix |
| Redaction | Secret-bearing URLs/headers/messages/files sanitized | `test-plan.md` redaction matrix |
| Correlation | correlation_id/attempt_id/step_index/action_id assignment | `test-plan.md` correlation matrix |
| Failure behavior | partial/unavailable/truncated statuses | `test-plan.md` failure matrix |
| Compatibility | missing timeline remains readable | `test-plan.md` compatibility matrix |

## 验证命令入口（Validation Commands）

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_browser_event_recorder.py -q
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_autonomous_explorer.py -q
uv run ruff check apps/api/app/services/learning/browser_event_recorder.py apps/api/tests/test_browser_event_recorder.py
git diff --check
```

Exact commands may change during implementation if existing test file names differ; review must record actual commands.
