# 实施计划

## 关键设计决策

本包采用以下方向：

1. 新增 conversation dispatch endpoint：
   - `POST /conversation/sessions/{session_id}/dispatch`
   - 用于把 user input 交给 Orchestrator。
   - 这是 runtime conversation endpoint，不是 store-level append message
     endpoint。
2. 更新 `wagent conversation send`：
   - 从调用 `POST /conversation/sessions/{session_id}/messages`
   - 改为调用 `POST /conversation/sessions/{session_id}/dispatch`
   - 这样普通 free text 和 `/replay` 都通过 Orchestrator。
3. 保留 11.0.3 store-level message endpoint：
   - `POST /conversation/sessions/{session_id}/messages` 仍然存在。
   - 它是低层 store facade。
   - CLI runtime send 不再直接调用它。
4. `/replay` 仅支持显式 `learned_path_id + url`。
5. replay hook 调用 M10 replay service，不做 HTTP self-call。
6. replay result 保持 M10 `ReplayResult` 语义，不包装成 `pass_gate` 或
   Supervisor verdict。
7. dispatch endpoint 第一版只接受 user input，不支持 non-user roles。
8. internal `DispatchResult` 可以保留 `engine_command` 作为 future hook
   placeholder；public `ConversationDispatchResponse` 不暴露 `engine_command`。
9. 11.0.6 不写 `session.metadata.last_replay_result`；replay lifecycle 只写
   conversation events。

## 触及的文件 / 模块

这是后续实现计划，不是本轮文档初始化要改的代码。

- `apps/api/app/services/conversation/orchestrator.py` —— add replay hook
  integration。
- `apps/api/app/services/conversation/replay_hook.py` 或等价 module —— bridge
  explicit replay command to M10 replay service。
- `apps/api/app/routers/conversation.py` —— add dispatch endpoint。
- `apps/api/app/schemas/conversation.py` —— add dispatch request / response
  schema if needed。
- `apps/cli/wagent/conversation.py` —— make `send` call dispatch endpoint。
- `apps/api/tests/test_conversation_replay_hook.py` —— service-level replay
  hook tests。
- `apps/api/tests/test_conversation_api.py` —— dispatch endpoint tests。
- `apps/cli/tests/test_conversation.py` —— CLI send mapping tests。
- `docs/iterations/m11/11.0.6-explicit-replay-command-hook/review.md`。

## API contract

新增 endpoint：

```text
POST /conversation/sessions/{session_id}/dispatch
```

Request:

```text
ConversationDispatchRequest
- input: string
- metadata optional, default {}
```

Response:

```text
ConversationDispatchResponse
- session_id
- previous_status
- next_status
- command_kind
- user_response
- events_appended
- message_id optional
- allowed
- error optional
- replay_result optional: ConversationReplaySummary
```

Rules:

- missing session -> HTTP 404。
- malformed `/replay` -> no replay call; allowed=false or parser error response
  according to 11.0.5 semantics。
- non-replay commands behave like 11.0.5 dispatch。
- replay command triggers replay hook only when parse succeeds and transition is
  allowed。
- replay hook errors map to dispatch response + `replay_failed` event, not to
  `pass_gate`。

## Dispatch endpoint error policy

`POST /conversation/sessions/{session_id}/dispatch` 的错误语义固定为：

- Missing conversation session -> HTTP 404。
- Invalid HTTP request body -> HTTP 422。
- Malformed slash command, including malformed `/replay`, returns HTTP 200 with
  `allowed=false` and `error` in `ConversationDispatchResponse`; it must not call
  replay。
- Replay resource / runtime failures, including missing LearnedPath, deprecated
  LearnedPath, drifted, unsupported, failed, or `runtime_error`, return HTTP 200
  with a dispatch response that records the replay failure and appends a
  `replay_failed` event。
- The dispatch endpoint should not expose M10 replay HTTP statuses directly
  except through structured replay error fields。

说明：

- conversation dispatch is runtime conversation command processing。
- 只要 session 存在、request body 合法，用户输入应进入 audit trail。
- replay failure 是 conversation result，不是 dispatch endpoint crash。

## Replay response shape

`ConversationDispatchResponse.replay_result` 第一版使用 summary，不嵌入完整
M10 `ReplayResult` step details。

```text
ConversationReplaySummary
- learned_path_id
- url
- replay_status
- drift_status
- drift_reasons
- warnings
- final_url
- final_title
- step_count
- error optional
```

Full M10 `ReplayResult` semantics remain authoritative inside replay service。
Conversation event payload uses the same summary shape。

## Replay hook design

Replay hook 通过小 handler interface 注入 `ConversationOrchestrator`。

推荐 contract：

```text
ReplayCommandHandler
- run(learned_path_id: str, url: str) -> ConversationReplaySummary or ReplayResult
```

或者：

```text
run_explicit_replay_command(db/session/context, learned_path_id, url) -> ReplayResult
```

要求：

- 不使用 HTTP self-call。
- 复用 M10 replay service / schema。
- 不改变 M10 replay API contract。
- 不做 path selection。
- 不做 slot binding。
- 不调用 autonomous run。
- 不调用 LLM provider。
- 不把 result 包装为 Supervisor verdict。

`orchestrator.py` may depend on the handler abstraction, but should not directly
scatter M10 replay service details. The concrete handler may live in
`apps/api/app/services/conversation/replay_hook.py` and may call M10 replay
service.

`orchestrator.py` should not directly import autonomous explorer, LLM provider,
or HTTP routes. If it imports `replay_hook`, tests must still guard that no
autonomous / LLM / `/exploration/autonomous-runs` imports appear。

## Status / event lifecycle

建议流程：

1. User sends `/replay <learned_path_id> <url>` through dispatch。
2. Orchestrator records user message。
3. Orchestrator parses command and appends `command_parsed`。
4. State transitions to `replay_requested`。
5. Append `replay_requested` event。
6. Hook starts execution：
   - update session status to `replay_running`。
   - append `state_changed` event。
7. M10 replay returns result。
8. If replay status is `succeeded` or `observed`：
   - update session status to `completed`。
   - append `replay_completed` event with replay result summary。
9. If replay status is `drifted`, `unsupported`, `failed`, or
   `runtime_error`：
   - update session status to `failed`。
   - append `replay_failed` event with replay result summary。
10. Dispatch response includes `replay_result`。

If existing `ConversationEventType` lacks an event needed by this flow, plan may
add enum values minimally. Do not add user / account / tenant fields。

## CLI behavior

Update existing command:

```text
wagent conversation send <session_id> --content "..."
```

New behavior:

- Calls `POST /conversation/sessions/{session_id}/dispatch`。
- For ordinary free text, returns `ConversationDispatchResponse` JSON。
- For `/replay <learned_path_id> <url>`, returns `ConversationDispatchResponse`
  including `replay_result`。
- Still outputs JSON by default。
- `--pretty` still works。
- Do not add a new `wagent conversation replay` command in 11.0.6。
- Do not add interactive REPL。

Reason:

- Existing `send` is the runtime user input command。
- Routing it through dispatch connects CLI to Orchestrator without adding new
  CLI surface。

## Event payload policy

Replay lifecycle event payload should include:

- `learned_path_id`
- `url`
- `replay_status`
- `drift_status`
- `drift_reasons` summary
- `warnings`
- `final_url`
- `final_title`
- step count
- error summary if any

Do not include full screenshots or artifacts。
Do not include `pass_gate` or Supervisor verdict。

## Public response and metadata policy

- Internal `DispatchResult` may keep `engine_command` as a future hook
  placeholder。
- Public `ConversationDispatchResponse` does not expose `engine_command` in
  11.0.6。
- `POST /conversation/sessions/{session_id}/dispatch` accepts user input only。
- Dispatch does not support non-user roles in 11.0.6。
- 11.0.6 does not write `last_replay_result` into session metadata。
- Replay lifecycle is recorded through conversation events。

## Testing plan

### Service tests

Add or update tests covering:

- `/replay <id> <url>` calls replay handler with explicit id + url。
- malformed `/replay` does not call replay handler。
- ordinary free text does not call replay handler。
- replay succeeded -> session completed + `replay_completed` event。
- replay observed -> session completed + `replay_completed` event。
- replay drifted -> session failed + `replay_failed` event。
- replay unsupported -> session failed + `replay_failed` event。
- replay `runtime_error` / failed -> session failed + `replay_failed` event。
- replay handler exception -> session failed + `replay_failed` event。
- no path selection。
- no autonomous imports。
- no LLM imports。

### API tests

Add tests for:

- `POST /conversation/sessions/{id}/dispatch` free text。
- dispatch missing session -> 404。
- dispatch malformed replay -> no replay result, no replay call。
- dispatch replay success returns `replay_result`。
- dispatch replay drift / unsupported / failure returns `replay_result` and
  status update。
- response envelope uses `ApiResponse`。
- dispatch endpoint does not expose user / account / tenant fields。

### CLI tests

Update tests for:

- `wagent conversation send` calls `/conversation/sessions/{id}/dispatch`。
- `send` with free text prints `ConversationDispatchResponse`。
- `send` with `/replay ...` prints `replay_result`。
- API error from dispatch exits 2。
- `wagent conversation messages` / `transcript` / `events` / `status` /
  `start` behavior remains unchanged。
- CLI does not import DB, replay, autonomous, or LLM modules。

### Existing tests

Run:

- conversation orchestrator tests。
- conversation API tests。
- conversation repo / commands / state tests。
- CLI tests。
- Replay service / API tests if hook touches replay imports。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest \
  tests/test_conversation_replay_hook.py \
  tests/test_conversation_orchestrator.py \
  tests/test_conversation_api.py \
  tests/test_conversation_repo.py \
  tests/test_conversation_commands.py \
  tests/test_conversation_state.py \
  tests/test_learned_path_replay.py \
  tests/test_exploration_learned_paths_api.py -v

cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_verify.py tests/test_skill.py -v

cd apps/api && ../../.venv/bin/ruff check \
  app/services/conversation/orchestrator.py \
  app/services/conversation/replay_hook.py \
  app/routers/conversation.py \
  app/schemas/conversation.py \
  tests/test_conversation_replay_hook.py \
  tests/test_conversation_api.py

cd apps/cli && ../../.venv/bin/ruff check wagent/conversation.py tests/test_conversation.py

git diff --check
```

当前文档阶段只运行：

```bash
git diff --check
```
