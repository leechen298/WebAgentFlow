# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

已有底层：

- `apps/api/app/models/conversation.py` 定义 `ConversationSession`、`ConversationMessage`、`ConversationEvent`，并明确是 persistent store。
- `apps/api/app/repos/conversation_repo.py` 支持 create / get session、append / list messages、transcript、append / list events。
- `apps/api/app/routers/conversation.py` 暴露 create / get session、messages、transcript、events、dispatch。
- `apps/api/app/schemas/conversation.py` 已有 Conversation API request / response schema 和 dispatch response schema。
- `apps/cli/wagent/conversation.py` 已有 `start/status/send/messages/transcript/events`。
- `apps/cli/wagent/chat.py` 创建 `current_mode=interactive_chat` session，并进入 REPL。
- `apps/console/src/router/index.ts` 当前只有 overview、autonomous exploration、autonomous history、autonomous use cases、learned paths。

当前缺口：

- repository / API 没有 session list。
- API 没有 aggregate history endpoint。
- CLI 没有 `conversation list` / `conversation history`。
- `wagent chat` 不输出 session id，也不能 `--resume`。
- Console 没有 conversation history list / detail 页面。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Session list by mode / status / time | `ConversationRepository.list_sessions()` + router query params | API-1 / API-2 | Sort by `updated_at desc` |
| Session summary includes counts and last messages | history service computes counts / last user / last agent from existing messages/events | API-3 | No DB schema change |
| Aggregate history returns messages + events + learned_actions + replay / learning evidence | `ConversationHistoryService.get_history()` builds read model from repo + event payloads | API-4 / API-5 | No invented verdicts |
| Existing endpoints unchanged | only add routes / schemas; no existing response mutation | REG-1 | Backward compatibility |
| CLI list / history | add subcommands in `apps/cli/wagent/conversation.py` | CLI-1 / CLI-2 | Thin HTTP client only |
| `wagent chat` prints session id | print after successful create session | CLI-3 | User-facing debug handoff |
| `wagent chat --resume` | fetch session, validate `current_mode=interactive_chat`, reuse id | CLI-4 / CLI-5 | Does not mutate session |
| Console routes and nav | add API client, list page, detail page, route, nav/i18n | UI-1 / UI-2 / UI-3 | Console read-only debug surface |
| No live run | no autonomous endpoints or `verify-scenario` in implementation/test plan | BOUNDARY-1 | History is read-only |

## 实现方案（Proposed Implementation）

### API schemas

Modify `apps/api/app/schemas/conversation.py`:

- Add `ConversationSessionSummaryResponse`.
- Add `ConversationSessionListResponse`.
- Add `ConversationLearningRunSummary`.
- Add `ConversationReplayHistorySummary`.
- Add `ConversationHistoryResponse`.

Keep existing schemas unchanged.

### Repository and service

Modify `apps/api/app/repos/conversation_repo.py`:

- Add `list_sessions(current_mode=None, status=None, updated_from=None, updated_to=None, limit=50)`.
- Add helper queries or service-facing methods for counts and latest messages if needed.

Create `apps/api/app/services/conversation/history.py`:

- `ConversationHistoryService.list_session_summaries(...)`.
- `ConversationHistoryService.get_history(session_id)`.
- `ConversationHistoryService` owns read-model extraction so the router stays thin.
- Extract learned actions from `session.metadata_json.get("learned_actions") or []`.
- Extract learning runs from events where `type == "chat_learning_completed"`.
- Extract replay summaries from event payloads that contain a `replay` object or known replay summary fields.
- Preserve raw session / messages / events in `raw`.

### API routes

Modify `apps/api/app/routers/conversation.py`:

- Add `GET /conversation/sessions` for list.
- Add `GET /conversation/sessions/{session_id}/history` for aggregate detail.
- Keep `GET /conversation/sessions/{session_id}` unchanged.
- Keep response envelope `ApiResponse`.

### CLI

Modify `apps/cli/wagent/conversation.py`:

- Add `list` subcommand:

```bash
wagent conversation list --mode interactive_chat --status task_intake --limit 20 --pretty
```

- Add `history` subcommand:

```bash
wagent conversation history <session_id> --pretty
```

- Use existing `_api_request` and `_output`.
- Do not import backend DB, repo, replay, autonomous, or LLM modules.

Modify `apps/cli/wagent/chat.py`:

- After creating a new session, print:

```text
WAgent > 本次会话 ID：<session_id>。需要调试时可以在管理后台查看。
```

- Add `--resume <session_id>`.
- On resume:
  - call `GET /conversation/sessions/{session_id}`;
  - require `current_mode == "interactive_chat"`;
  - enter the same REPL using that session id;
  - do not create a new session;
  - reject `--resume` combined with `--headless` if `--headless` exists.

### Console API client

Create `apps/console/src/api/conversation.ts`:

- Type `ConversationSessionSummary`.
- Type `ConversationHistoryPayload`.
- `listConversationSessions(params)`.
- `getConversationHistory(sessionId)`.

Update `apps/console/src/api/index.ts` if the project exports API modules there.

### Console UI

Create:

- `apps/console/src/pages/ConversationHistoryPage.vue`
- `apps/console/src/pages/ConversationHistoryDetailPage.vue`

Modify:

- `apps/console/src/router/index.ts`
- `apps/console/src/layouts/MainLayout.vue`
- `apps/console/src/i18n/locales/en.ts`
- `apps/console/src/i18n/locales/zh.ts`
- `apps/console/src/i18n/locales/ja.ts`

List page:

- filter controls: mode, status, updated range, limit.
- table columns: updated_at, session id, mode, status, last_user_message, last_agent_message, learned_action_count, event_count.
- row action: open detail.
- copy session id action.

Detail page:

- header with session id, status, mode, created_at, updated_at.
- tabs: Transcript, Events, Learned Actions, Replay / Learning Evidence, Raw JSON.
- Raw JSON uses aggregate history payload, formatted and copyable.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | Yes | Add session list and aggregate history read endpoints | Existing endpoints unchanged |
| API response schema | Yes | Add read-model schemas | Existing schemas unchanged |
| Database schema / migration | No | Reuse existing conversation tables and metadata JSON | No migration |
| CLI | Yes | Add conversation list/history and chat resume/session id output | Existing commands unchanged |
| Console UI | Yes | Add history list/detail routes and nav entry | Read-only |
| Conversation events | No | Read existing events only | No new event type planned |
| Replay execution | No | Only display replay summaries from persisted events | No execution path change |
| Reporter | No | Reporter outputs are displayed only if already in events | No Reporter behavior change |
| Worker / async jobs | No | No async jobs | N/A |
| Tests / fixtures | Yes | Add API, CLI, Console tests | No validation-site fixtures |
| Docs | Yes | Add 11.3.2 docs and update M11 planning index | Existing iteration docs unchanged |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No database migration.

Read-model schema additions only:

```python
class ConversationSessionSummaryResponse(BaseModel):
    id: str
    status: ConversationStatus
    current_mode: str | None
    created_at: datetime | None
    updated_at: datetime | None
    message_count: int
    event_count: int
    last_user_message: str | None
    last_agent_message: str | None
    learned_action_count: int
    learned_actions: list[dict[str, Any]]
```

```python
class ConversationSessionListResponse(BaseModel):
    items: list[ConversationSessionSummaryResponse]
```

```python
class ConversationHistoryResponse(BaseModel):
    session: ConversationSessionResponse
    messages: list[ConversationMessageResponse]
    events: list[ConversationEventResponse]
    learned_actions: list[dict[str, Any]]
    learning_runs: list[dict[str, Any]]
    replay_summaries: list[dict[str, Any]]
    raw: dict[str, Any]
```

## 服务 / 模块设计（Service / Module Design）

`ConversationHistoryService`:

- Input: SQLAlchemy session or `ConversationRepository`.
- Output: Pydantic read-model schemas.
- Responsibilities:
  - validate session existence;
  - list sessions with filters;
  - compute summary metrics;
  - build aggregate detail payload;
  - extract known evidence objects from raw event payloads;
  - keep raw persisted payload available.

CLI remains a thin HTTP client. Console uses the HTTP API only.

## 数据流（Data Flow）

List:

```text
Console / CLI
-> GET /conversation/sessions?current_mode=interactive_chat
-> ConversationHistoryService.list_session_summaries()
-> existing conversation tables
-> ApiResponse(data={items:[...]})
```

Detail:

```text
Console / CLI
-> GET /conversation/sessions/{session_id}/history
-> ConversationHistoryService.get_history()
-> session + messages + events + metadata learned_actions
-> extracted learning_runs / replay_summaries
-> ApiResponse(data=aggregate payload)
```

Resume:

```text
wagent chat --resume <session_id>
-> GET /conversation/sessions/{session_id}
-> validate current_mode == interactive_chat
-> enter REPL
-> POST /conversation/sessions/{session_id}/dispatch
```

## 状态推导（Status / State Derivation）

No new status derivation.

Summary fields:

- `message_count` = count of messages for the session.
- `event_count` = count of events for the session.
- `last_user_message` = latest message with `role=user`.
- `last_agent_message` = latest message with `role=agent`.
- `learned_action_count` = length of `session.metadata_json.learned_actions or []`.

History evidence:

- `learning_runs` are extracted only from known event payloads.
- `replay_summaries` are extracted only from known event payloads.
- Missing payloads remain missing.

## 兼容性（Compatibility）

- Existing session rows continue to work.
- Existing API clients are unaffected.
- Existing CLI commands are unaffected.
- Old sessions without `learned_actions` display `0` and `[]`.
- Old events without replay payload display no replay summary.

## 失败 / 边界情况（Failure / Edge Cases）

- Session not found: API returns 404; CLI exits 2; Console shows empty/error state.
- Non-`interactive_chat` resume: CLI exits 2 and explains that only chat sessions can be resumed.
- Empty session: list/detail show zero counts and empty arrays.
- Very long messages: list page truncates display text, raw detail preserves full content.
- Malformed historical event payload: raw JSON still displays; extracted summary skips malformed item and does not fail the whole page.
- API unavailable: CLI uses existing error style; Console shows request failure state.

## 非目标（Non-goals）

- No autonomous run.
- No `verify-scenario`.
- No LLM summary.
- No full-text search.
- No multi-user permission or tenant model.
- No export/archive system.
- No M12 recovery / retry / abort.

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| API unit / integration | list filters, summary fields, aggregate history payload, 404 | `test-plan.md` API-1 to API-6 |
| CLI unit | list/history commands, chat session id output, resume validation | `test-plan.md` CLI-1 to CLI-6 |
| Console API / router | API client paths, new routes and nav entry | `test-plan.md` UI-1 / UI-2 |
| Console component | list/detail render states and raw JSON copy surface | `test-plan.md` UI-3 / UI-4 |
| Boundary | no live run or autonomous endpoint usage | `test-plan.md` BOUNDARY-1 |

## 验证命令入口（Validation Commands）

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py -q
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_chat.py -q
pnpm --filter @web-agent-flow/console test -- --run src/__tests__/api/conversation.test.ts src/__tests__/router/index.test.ts src/__tests__/components/ConversationHistoryPage.test.ts src/__tests__/components/ConversationHistoryDetailPage.test.ts
cd apps/api && ../../.venv/bin/ruff check app/routers/conversation.py app/repos/conversation_repo.py app/services/conversation app/schemas/conversation.py tests/test_conversation_api.py tests/test_conversation_repo.py
cd apps/cli && ../../.venv/bin/ruff check wagent/conversation.py wagent/chat.py tests/test_conversation.py tests/test_chat.py
git diff --check
```
