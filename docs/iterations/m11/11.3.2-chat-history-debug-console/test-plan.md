# 测试计划（Test Plan）

状态：proposed

## 适用条件

本轮满足以下触发条件，因此必须维护 `test-plan.md`：

- 涉及前后端协同。
- 涉及 CLI。
- 涉及 Console UI。
- 测试矩阵超过 5 个 case。
- 需要区分 unit / integration / UI smoke / live product evidence。

## 测试范围（Test Scope）

- Unit：history read-model extraction、CLI parser / payload、Console API client。
- Integration：Conversation API list / history endpoints with DB-backed repo。
- API：session list filters、aggregate history payload、404 / empty state。
- Console UI：history list / detail component tests、router/nav tests。
- E2E：N/A，首版不要求 E2E。
- Agent / Reporter / Recovery：N/A，本轮不改 internal Agent、Reporter、recovery。
- Codex / AI External Operator：只允许基于真实 API / CLI / UI 输出做调试，不得伪造 internal Agent verdict。
- Live autonomous run：N/A，本轮不得触发 `verify-scenario` 或 autonomous run。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| API | API-1 list recent sessions | `tests/test_conversation_api.py` | `GET /conversation/sessions` returns `items` sorted by updated time | Yes | no live run |
| API | API-2 filters | `tests/test_conversation_api.py` | `current_mode/status/updated_from/updated_to/limit` filter correctly | Yes | include empty result |
| API | API-3 summary fields | `tests/test_conversation_api.py` | message_count, event_count, last_user_message, last_agent_message, learned_action_count correct | Yes | DB-backed |
| API | API-4 aggregate history | `tests/test_conversation_api.py` | detail returns session, messages, events, learned_actions, raw | Yes | persisted data only |
| API | API-5 evidence extraction | `tests/test_conversation_api.py` | learning_runs and replay_summaries extracted from known event payloads | Yes | no invented evidence |
| API | API-6 not found | `tests/test_conversation_api.py` | unknown session history returns 404 | Yes | CLI depends on this |
| CLI | CLI-1 conversation list | `apps/cli/tests/test_conversation.py` | calls `GET /conversation/sessions` with mode/status/limit | Yes | JSON stdout only |
| CLI | CLI-2 conversation history | `apps/cli/tests/test_conversation.py` | calls `GET /conversation/sessions/{id}/history` | Yes | pretty output covered |
| CLI | CLI-3 chat session id | `apps/cli/tests/test_chat.py` | new chat prints session id after create | Yes | user-facing line |
| CLI | CLI-4 chat resume happy path | `apps/cli/tests/test_chat.py` | validates session and dispatches to existing id without create | Yes | no API mutation |
| CLI | CLI-5 chat resume rejects non-chat | `apps/cli/tests/test_chat.py` | exits 2 if current_mode is not `interactive_chat` | Yes | prevents accidental mode change |
| CLI | CLI-6 resume/headless conflict | `apps/cli/tests/test_chat.py` | `--resume` + `--headless` rejected when `--headless` exists | Yes | avoids false policy change |
| Console API | UI-1 conversation API client | `src/__tests__/api/conversation.test.ts` | list/history endpoints and params correct | Yes | mock axios |
| Console Router | UI-2 routes/nav | `src/__tests__/router/index.test.ts` / layout test | new routes exist and nav highlights history | Yes | no browser |
| Console Component | UI-3 list page | `ConversationHistoryPage.test.ts` | renders filters, table fields, empty/error/loading states | Yes | mock API |
| Console Component | UI-4 detail page | `ConversationHistoryDetailPage.test.ts` | renders tabs, transcript/events/learned actions/replay/raw JSON | Yes | mock API |
| Boundary | BOUNDARY-1 no live run | source scan / review | no direct `/exploration/autonomous-runs` or `verify-scenario` invocation in this iteration | Yes | docs/code review |
| Manual smoke | MANUAL-1 Console route smoke | browser or in-app browser after implementation | `/conversation/history` and detail page load against local API | Optional before acceptance | record screenshot/URL if run |

## Manual Smoke 样例（Optional）

本轮不要求 live autonomous run。若实现完成后需要人工验证 Console 页面，可以使用已有或测试造数 conversation session。

启动项目：

```bash
pnpm run dev
```

打开：

```text
http://localhost:5174/conversation/history
```

期望：

- 页面能加载 session list。
- 筛选 `interactive_chat` 后能看到 chat sessions。
- 点击 session 进入 detail。
- Transcript / Events / Learned Actions / Replay / Learning Evidence / Raw JSON tabs 可切换。
- Raw JSON 可复制。

如果没有本地历史会话，可以用 API / CLI 创建普通 conversation session 做 read-surface smoke；不得为了本轮 smoke 触发 autonomous run。

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 如果没有真实打开 Console 页面，不得声称 `MANUAL-1` 已通过。
- 如果只运行了 Vitest / unit tests，必须写成“Console route smoke not run”。
- 本轮 UI smoke 只验证 history read surface，不验证 WebAgentFlow 操作网页。
- 不得调用 `/exploration/autonomous-runs` 或 `verify-scenario` 作为本轮验收。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / Kimi Code 可以使用以下 read / debug surfaces：

```bash
wagent conversation list --mode interactive_chat --limit 20 --pretty
wagent conversation history <session_id> --pretty
wagent conversation send <session_id> --content "..." --pretty
wagent chat --resume <session_id>
```

但报告时必须说明实际调用了哪个命令、原始输出是什么、是否只是读取历史还是追加了新消息。

不得把自己从 history payload 看到的信息改写为内部 Supervisor Agent、Task Path Planner 或 Task Result Reporter 的新 verdict。

## Live Run 边界（Live Run Boundary）

本轮不触发 live autonomous run。

禁止把以下调用作为本轮默认验证：

- `wagent verify`
- `verify-scenario`
- direct `POST /exploration/autonomous-runs`
- direct `POST /exploration/autonomous-runs/stream`
- product UI 触发 autonomous run

如果用户另行明确要求 live run，必须按 AGENTS.md reporting style 记录 `pass_gate.status`、`run_id`、Supervisor verdict 和 scorecard。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| E2E | 首版 read surface 可由 API / CLI / component tests 覆盖 | 真实浏览器集成问题只能通过 optional smoke 发现 |
| `verify-scenario` | 本轮不需要 live autonomous verification | 无；history read surface 不应触发 autonomous run |
| autonomous run | 本轮不改变 learning / execution behavior | 无；只读 history |
