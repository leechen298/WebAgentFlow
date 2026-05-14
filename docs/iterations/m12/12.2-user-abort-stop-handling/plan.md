# 12.2 Plan

Status: documentation initialized.

## 本轮范围

本轮只初始化 12.2 文档，不创建或修改代码文件。

不创建：

- `apps/api/app/services/recovery/abort_handler.py`
- `apps/api/tests/test_user_abort_handler.py`
- `apps/api/tests/test_conversation_abort_flow.py`

不修改：

- `apps/api/app/schemas/recovery.py`
- `apps/api/app/schemas/conversation.py`
- `apps/api/app/services/conversation/state.py`
- `apps/api/app/services/conversation/orchestrator.py`
- API router；
- CLI；
- database model / migration；
- frontend UI。

## Future Concept Model

未来实现可围绕以下概念建模：

| Concept | Meaning |
|---|---|
| `UserAbortSignal` | 用户明确要求停止当前自动化继续操作的信号。 |
| `AbortBoundary` | abort 被接受后，系统允许或禁止的运行时边界。 |
| `AbortReason` | 触发 abort handling 的结构化原因，例如 slash command、用户消息、UI stop。 |
| `AbortEvidence` | interruption time 的 execution / replay / reporter / user message evidence。 |
| `StopHandlingDecision` | 当前 stop handling 的稳定决策。 |
| `AbortAcknowledgement` | 返回给用户或 conversation flow 的 acknowledgement，不是 proposal。 |

## Future Signal Sources

未来实现可以识别：

- slash command `/abort`；
- slash command `/stop`；
- 明确表达停止意图的用户消息；
- UI stop button；
- external scheduler cancellation。

本轮不新增 slash command、不改 parser、不改 CLI。现有 conversation schema 中已有
`ABORT` command、`ABORT_REQUESTED` status / event、`PAUSE`、`CANCEL`、
`TAKEOVER` 等概念，12.2 只为后续实现定义边界。

## Stop Handling Rules

未来实现必须满足：

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

## Future Stop Decisions

| Decision | Default meaning |
|---|---|
| `accepted_stop` | Abort accepted; no new browser action may start. |
| `already_finished` | Runtime already finished before abort was handled. |
| `already_failed` | Runtime already failed before abort was handled. |
| `not_running` | There is no active automation to stop. |
| `cannot_interrupt_inflight_action` | Current action may already be in flight; record caveat. |
| `needs_manual_review` | State is not clear enough to decide without evidence review. |

## Future Implementation Steps

1. Define pure schemas for abort signal, abort evidence, stop decision, and
   acknowledgement.
2. Implement a deterministic abort handler that consumes current conversation /
   execution state and a user abort signal.
3. Make handler output an acknowledgement and evidence payload only; no proposal,
   retry, browser continuation, or LearnedPath write-back.
4. Integrate with conversation state/orchestrator only after the pure handler is
   tested.
5. Ensure repeated abort / stop returns the same stable acknowledgement instead
   of creating new actions.
6. Add tests for in-flight caveat and no-new-browser-action guarantees.

## Future Test Plan

Focused unit tests should cover:

- `/abort` while executing -> `accepted_stop`；
- `/stop` alias semantics；
- abort after finished -> `already_finished`；
- abort after failed -> `already_failed`；
- abort when not running -> `not_running`；
- in-flight action caveat -> `cannot_interrupt_inflight_action`；
- repeated abort is idempotent；
- abort does not call retry / replan / proposal generation；
- abort does not write LearnedPath；
- abort does not mutate 12.1 classifier behavior；
- pause / cancel / takeover remain distinct.

Integration tests should only be added after the pure handler is stable.

## Future Acceptance Criteria

- User abort is represented as user control intent.
- Abort acknowledgement is returned without recovery proposal execution.
- No new browser action starts after abort is accepted.
- In-flight external side effects are explicitly marked as unknown when needed.
- Repeated abort / stop is idempotent.
- Evidence includes user message, source status, active command / plan / step,
  last execution event, known replay status, reporter outcome, and no-new-action
  marker.
- Retry / replan / takeover / teaching mode remain outside 12.2.

## Validation for This Documentation Round

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.3*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
