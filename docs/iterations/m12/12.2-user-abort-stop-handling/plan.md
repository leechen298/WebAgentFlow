# 12.2 Plan

Status: implemented.

## 本轮范围

本轮实现 12.2 纯逻辑层，不做完整 runtime 接入。

实现：

- `apps/api/app/schemas/recovery.py` — 追加 abort signal / state / evidence / acknowledgement schema
- `apps/api/app/services/recovery/abort_handler.py` — 纯确定性 abort handler
- `apps/api/tests/test_user_abort_handler.py` — 单元测试

不实现：

- conversation dispatcher / orchestrator 接入
- API endpoint
- CLI command
- frontend stop button
- DB / migration
- 真实浏览器取消动作
- recovery proposal / retry / replan / takeover / teaching mode

## Concept Model

| Concept | Meaning |
|---|---|
| `UserAbortSignal` | 用户明确要求停止当前自动化继续操作的信号。 |
| `AbortSource` | 信号来源：slash_abort, slash_stop, user_message, ui_stop_button, external_scheduler。 |
| `UserAbortState` | interruption time 的 runtime state snapshot。 |
| `StopHandlingDecision` | 当前 stop handling 的稳定决策。 |
| `AbortEvidence` | interruption time 的 signal + state 证据。 |
| `AbortAcknowledgement` | 返回给用户或 conversation flow 的 acknowledgement，不是 proposal。 |

## Signal Sources

- slash command `/abort`
- slash command `/stop`
- 明确表达停止意图的用户消息
- UI stop button
- external scheduler cancellation

本轮不新增 slash command、不改 parser、不改 CLI。

## Stop Handling Rules

1. User abort is user intent, not engine failure.
2. Abort must be acknowledged.
3. No new browser action after abort is accepted.
4. If a browser action is already in flight, record best-effort stop boundary.
5. Abort must preserve evidence available at interruption time.
6. Abort must not silently convert to failure or success.
7. Abort must not trigger recovery proposal automatically.
8. Abort must not trigger retry automatically.
9. Abort must hand off later choices to 12.3 / 12.4 / 12.5.
10. Repeated abort / stop must be idempotent.

## Stop Decisions

| Decision | Default meaning |
|---|---|
| `accepted_stop` | Abort accepted; no new browser action may start. |
| `already_finished` | Runtime already finished before abort was handled. |
| `already_failed` | Runtime already failed before abort was handled. |
| `not_running` | There is no active automation to stop. |
| `cannot_interrupt_inflight_action` | Current action may already be in flight; record caveat. |
| `needs_manual_review` | State is not clear enough to decide without evidence review. |

## Implementation Steps

1. ✅ Define pure schemas for abort signal, abort state, abort evidence, stop decision, and
   acknowledgement in `recovery.py`.
2. ✅ Implement deterministic `UserAbortHandler` in `abort_handler.py` — pure logic,
   no side effects.
3. ✅ Handler outputs acknowledgement and evidence payload only; no proposal,
   retry, browser continuation, or LearnedPath write-back.
4. ✅ Module-level `handle_user_abort()` convenience wrapper.
5. ✅ Unit tests covering all decision paths, idempotency, evidence preservation,
   input immutability, and forbidden dependency scanning.

## Test Plan

Unit tests cover:

- `/abort` while executing -> `accepted_stop`
- `/stop` alias semantics
- abort after finished -> `already_finished`
- abort after failed -> `already_failed`
- abort when not running -> `not_running`
- null status -> `not_running`
- in-flight action caveat -> `cannot_interrupt_inflight_action`
- repeated abort is idempotent
- abort does not mutate input
- abort preserves evidence (signal, state, plan, step, replay status)
- accepted_stop blocks new actions for all active statuses
- inflight_caveat only for has_inflight_action
- abort handler does not import 12.1 recovery classifier
- abort handler has no forbidden runtime dependencies
- paused / replay_requested statuses handled correctly

## Acceptance Criteria

- ✅ User abort is represented as user control intent.
- ✅ Abort acknowledgement is returned without recovery proposal execution.
- ✅ No new browser action starts after abort is accepted.
- ✅ In-flight external side effects are explicitly marked when needed.
- ✅ Repeated abort / stop is idempotent.
- ✅ Evidence includes signal source, runtime state snapshot.
- ✅ Retry / replan / takeover / teaching mode remain outside 12.2.

## Validation

```bash
cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery/abort_handler.py tests/test_user_abort_handler.py
cd apps/api && .venv/bin/pytest tests/test_user_abort_handler.py -v
```
