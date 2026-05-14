# 12.2 Review and Reflection

Status: implemented.

## 实现记录

本轮实现了 12.2 纯逻辑层：abort signal schema + deterministic abort handler + unit tests。

### Changed files

- `apps/api/app/schemas/recovery.py` — 追加 AbortSource, StopHandlingDecision, UserAbortSignal, UserAbortState, AbortEvidence, AbortAcknowledgement
- `apps/api/app/services/recovery/abort_handler.py` — 新建，纯确定性 handler
- `apps/api/tests/test_user_abort_handler.py` — 新建，19 个单元测试

### Schema contracts

| Type | Role |
|---|---|
| `AbortSource` | Literal union: slash_abort, slash_stop, user_message, ui_stop_button, external_scheduler |
| `StopHandlingDecision` | Literal union: accepted_stop, already_finished, already_failed, not_running, cannot_interrupt_inflight_action, needs_manual_review |
| `UserAbortSignal` | source + raw_text + timestamp |
| `UserAbortState` | Runtime snapshot: session_status, active_command, active_plan_id, active_step_index, replay_status, reporter_outcome, has_inflight_action, etc. |
| `AbortEvidence` | signal + state + captured_at |
| `AbortAcknowledgement` | decision + message + evidence + no_new_actions_after + inflight_caveat |

### Handler design

`UserAbortHandler.handle(signal, state) -> AbortAcknowledgement`

Decision precedence (deterministic):

1. session_status in finished set → `already_finished`
2. session_status in failed set → `already_failed`
3. session_status empty / idle / not_running → `not_running`
4. has_inflight_action + active status → `cannot_interrupt_inflight_action`
5. active status → `accepted_stop`
6. fallback → `needs_manual_review`

Fail-closed: `no_new_actions_after` is `True` for `accepted_stop`,
`cannot_interrupt_inflight_action`, and `needs_manual_review`. Only
terminal states (`already_finished`, `already_failed`, `not_running`)
return `False`.

Pre-execution states (`awaiting_confirmation`, `task_intake`) are excluded
from `_ACTIVE_STATUSES` — user abort during plan confirmation is a cancel,
not an execution stop. These fall through to `needs_manual_review`.

Module-level `handle_user_abort()` convenience wrapper.

### Test coverage

19 tests covering:

- all 6 decision paths
- idempotent repeated abort
- input immutability (no mutation)
- evidence preservation (signal, state, plan, step, replay status)
- captured_at propagates from signal.timestamp when present
- accepted_stop blocks new actions for all active statuses
- inflight_caveat only when has_inflight_action=True
- forbidden dependency scanning (no 12.1 classifier import)
- forbidden runtime dependency scanning (no sqlalchemy, playwright, httpx, etc.)
- paused / replay_requested status handling

## Non-goals Preserved

本轮没有实现：

- conversation dispatcher / orchestrator 接入
- API endpoint
- CLI command
- frontend stop button
- database migration
- 真实浏览器取消动作
- recovery proposal generation
- retry / re-run policy
- replan execution
- teaching mode
- takeover
- LearnedPath write-back
- E2E
- `verify-scenario`

## Relationship to 12.1

12.2 不改变 12.1 classifier，也不把 user abort 塞进 classifier。User abort
是 runtime user-control signal，由独立 stop handling boundary 接住。

## Relationship to 12.3 / 12.4 / 12.5

- 12.3 可以基于 abort boundary 生成后续选择 proposal，但 12.2 不生成 proposal。
- 12.4 定义 retry / re-run policy，12.2 不判断 safe retry。
- 12.5 接 conversation flow，12.2 不实现 dialogue routing。

## Acceptance Criteria

- ✅ User abort is represented as user control intent.
- ✅ Abort acknowledgement is returned without recovery proposal execution.
- ✅ No new browser action starts after abort is accepted.
- ✅ In-flight external side effects are explicitly marked when needed.
- ✅ Repeated abort / stop is idempotent.
- ✅ Evidence includes signal source, runtime state snapshot.
- ✅ Retry / replan / takeover / teaching mode remain outside 12.2.
- ✅ ruff clean.
- ✅ 19/19 unit tests pass.
