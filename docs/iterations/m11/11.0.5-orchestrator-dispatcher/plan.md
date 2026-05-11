# 实施计划

## 触及的文件 / 模块

这是后续实现计划，不是本轮文档初始化要改的代码。

- `apps/api/app/services/conversation/orchestrator.py` —— planned dispatcher
  service。
- `apps/api/app/services/conversation/__init__.py` —— export if needed。
- `apps/api/app/services/conversation/commands.py` —— reuse parser。
- `apps/api/app/services/conversation/state.py` —— reuse transition。
- `apps/api/app/repos/conversation_repo.py` —— use session / message / event
  store。
- `apps/api/tests/test_conversation_orchestrator.py` —— orchestrator tests。
- `docs/iterations/m11/11.0.5-orchestrator-dispatcher/review.md` —— implementation
  evidence after code work。

11.0.5 不改 11.0.3 public API endpoint contract，也不新增 `wagent conversation`
CLI 命令。

## Orchestrator contract

推荐实现一个内部 service function：

```text
dispatch_user_input(session_id: str, raw_input: str) -> DispatchResult
```

也可以实现为 service class：

```text
ConversationOrchestrator(repo: ConversationRepository)

dispatch_user_input(session_id: str, raw_input: str) -> DispatchResult
dispatch_engine_event(
    session_id: str,
    event_type: ConversationEventType,
    payload: dict,
) -> DispatchResult
```

`dispatch_engine_event` 只作为 11.0.5 service contract 占位；本包不执行
engine command、不调用 browser、不接 Agent routing。

建议 result 字段：

```text
DispatchResult
- session_id
- previous_status
- next_status
- command_kind
- user_response
- events_appended
- message_id optional
- allowed
- error optional
- engine_command optional
```

说明：

- `engine_command` 只作为未来 hook 的占位。
- 11.0.5 不执行 `engine_command`。
- replay command 的 `engine_command` 可为 `None` 或 placeholder，但不能调用
  replay。
- `DispatchResult` 优先作为 `orchestrator.py` 内部 Pydantic model 或 dataclass；
  如果后续 11.0.6 / API 层需要复用，再迁移到
  `apps/api/app/schemas/conversation.py`。

missing session 固定为：

```text
ValueError("session not found: <session_id>")
```

本包不设计 HTTP error mapping；API endpoint 是否接 orchestrator 留给后续包。

## Behavior contract

`dispatch_user_input` 的推荐流程：

1. 通过 `ConversationRepository.get_session(session_id)` 读取 session。
2. session 不存在时抛 `ValueError("session not found: ...")`。
3. 通过 `repo.append_message(session_id, role="user", content=raw_input)` 记录
   用户输入。
4. 调用 `parse_command(raw_input)` 得到 `ConversationCommand`。
5. 追加 `command_parsed` audit event。
6. 调用 `next_state(current_status, command)` 得到
   `ConversationTransitionResult`。
7. 如果 transition allowed：
   - update session status。
   - append transition event。
   - append `state_changed` event when status changed。
   - return user-facing response hint。
8. 如果 transition not allowed：
   - do not update status。
   - append event recording rejection or command error。
   - return error response hint。
9. 不调用 replay / autonomous / LLM。

该 flow 不执行 replay、不调用 LLM、不调用 autonomous run、不触发 browser action。

## Event policy

每次 dispatch 都必须追加 `command_parsed` event。

推荐 payload：

```text
{
  "raw": raw_input,
  "command_kind": command.kind,
  "args": command.args,
  "learned_path_id": command.learned_path_id,
  "url": command.url,
  "text": command.text,
  "parse_error": command.error,
  "allowed": transition.allowed,
  "transition_error": transition.error,
}
```

transition allowed 时追加 transition event，event type 取自
`ConversationTransitionResult.event_type`。可出现的 transition event 包括：

- `message_received`
- `state_changed`
- `pause_requested`
- `resume_requested`
- `abort_requested`
- `takeover_requested`
- `replay_requested`

status 发生变化时追加 `state_changed` event；如果 transition event 已经是
`state_changed`，则该 event 同时承担状态变化记录，不重复追加。

推荐 payload：

```text
{
  "from": current_status,
  "to": transition.next_status,
  "command_kind": command.kind,
  "transition_event_type": transition.event_type,
  "allowed": transition.allowed,
  "error": transition.error,
}
```

`session_failed` 只用于 dispatcher 内部错误审计；普通 invalid transition 不应标记为
session failure。

11.0.5 不把 replay result 包装成 `pass_gate` 或 Supervisor verdict。

## Status update policy

- `allowed=false`：不更新 session status，只记录 user message 和
  `command_parsed` event。
- `status` command：allowed，但状态不变；只记录 audit event，不追加
  `state_changed`。
- `free_text`：从 `idle` / `task_intake` 进入或保持 `task_intake`。
- `pause`：更新为 `paused`，并写入 `previous_status=current_status`。
- `resume`：遵循 11.0.1 语义回到 `task_intake`，并清空 `previous_status`。
- `abort`：进入 `abort_requested`。
- `takeover`：进入 `takeover_requested`。
- `cancel`：回到 `idle`，并清空 `previous_status`。
- `/replay <learned_path_id> <url>`：只允许进入 `replay_requested`，记录 audit；
  不执行 replay、不调用 replay API。

## Response policy

`response_hint` 直接来自 `ConversationTransitionResult.response_hint`，并作为
WebAgentFlow 视角的最小 user-facing response。

本包不生成自然语言规划、不调用 LLM、不暴露内部 Agent 作为用户直接沟通对象。
后续 11.0.6 / 11.1 如果需要更丰富 response，必须在新执行包中明确扩展。

## User-facing response hints

规划基础 response：

- `/status`：report current status。
- free text：status becomes `task_intake`；response 表示 task input recorded，
  task planning is not implemented yet。
- `/pause`：session paused。
- `/resume`：session resumed。
- `/abort`：abort requested；full abort dialogue is not implemented yet。
- `/takeover`：takeover requested；teaching / takeover flow is not implemented
  yet。
- `/cancel`：session cancelled or returned to idle, following 11.0.1 state
  contract。
- `/replay <id> <url>`：replay command recorded；replay hook is not implemented
  until 11.0.6；no replay execution。

## API integration

本包默认不新增 HTTP endpoint。

原因：

- 11.0.3 API 是 store-level API。
- 11.0.4 CLI 当前调用 store-level API。
- 11.0.5 先创建 backend service contract。
- 11.0.6 或后续包可以在需要时暴露 dispatch endpoint。

如果实现阶段认为必须新增 endpoint，必须先在 plan / review 中明确：

- endpoint name。
- 为什么 store API 不够。
- 为什么该 endpoint 不会变成 task planning。

本轮推荐 11.0.5 先不新增 endpoint。

## Boundary checks

实现阶段必须避免以下 imports / endpoint 字符串：

- `learned_path_replay`
- `/exploration/autonomous-runs`
- `/exploration/autonomous-runs/stream`
- `autonomous_explorer`
- `run_autonomous_exploration`
- `llm`
- `provider`
- `apps.cli`

`/replay` 可以作为 command text 被 parser 识别，但 11.0.5 orchestrator 不得
调用 replay service 或 replay API。

## 测试计划

后续实现时至少覆盖：

- free text from idle records user message, `command_parsed`, `state_changed`,
  and status `task_intake`。
- `/status` records audit and does not mutate status。
- `/pause` updates status to `paused` and stores `previous_status`。
- `/resume` from `paused` returns to `task_intake` and clears `previous_status`。
- `/abort` updates status to `abort_requested`。
- `/takeover` updates status to `takeover_requested`。
- `/cancel` returns status to `idle`。
- invalid transition returns `allowed=false` and does not update session status。
- `/replay <id> <url>` moves only to `replay_requested` and does not call replay。
- malformed `/replay` records parse error and does not update session status。
- dispatcher appends `command_parsed` and `state_changed` events where required。
- missing session raises `ValueError("session not found: ...")`。
- orchestrator module does not import replay / autonomous / LLM / Agent / CLI
  modules。
- existing command / state / repo / API / CLI tests still pass。

## 验证

后续实现阶段运行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_orchestrator.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py -v
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py -v
cd apps/api && ../../.venv/bin/ruff check app/services/conversation/orchestrator.py app/services/conversation/__init__.py tests/test_conversation_orchestrator.py
git diff --check
```

当前文档阶段只运行：

```bash
git diff --check
```
