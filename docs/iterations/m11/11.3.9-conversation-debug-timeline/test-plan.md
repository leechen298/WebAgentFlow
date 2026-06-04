# 测试计划（Test Plan）

状态：docs_generated_pending_design_review

## 适用条件

本轮满足以下触发条件，因此必须维护 `test-plan.md`：

- 涉及前后端协同。
- 涉及 API response schema。
- 涉及 Console UI。
- 涉及 CLI user-facing handoff。
- 测试矩阵超过 5 个 case。
- 涉及 UI smoke / product debug surface。
- 需要明确 live autonomous run 边界。

## 测试范围（Test Scope）

- Unit：timeline builder status/kind/title/details derivation。
- Integration：Conversation history API response with persisted messages/events/traces。
- API：history endpoint `debug_timeline` compatibility and redaction。
- Console UI：history detail Timeline tab rendering, expanded details, raw tabs preserved。
- CLI：new session debug path handoff text。
- E2E：N/A；首版不要求 Playwright E2E。
- Agent / Reporter / Recovery：只读展示 recovery / reporter related events；不改 Agent / Reporter / Recovery behavior。
- Codex / AI External Operator：可做 Console UI smoke，但不得触发 live autonomous run。
- Live autonomous run：N/A；本包不得触发 `verify-scenario` 或 autonomous run。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| API | API-1 derives user / agent timeline | `tests/test_conversation_api.py` or focused service test | user message and agent response create readable timeline items | Yes | DB-backed or service fixture |
| API | API-2 derives choice / waiting timeline | focused API/service test | `unknown_target_choice_created` becomes waiting/action-options item | Yes | Covers current user complaint path |
| API | API-3 derives LLM / entry gate trace summary | focused API/service test | trace items include provider/model/request_id/latency but no raw private payload | Yes | Use sanitized payload |
| API | API-4 redacts private maps | focused API/service test | `pending_choice_private_map`, `learned_path_id` private maps, secrets absent from timeline details | Yes | May use string scan |
| API | API-5 unknown event safe fallback | focused API/service test | unknown event renders generic item or is safely skipped; endpoint still 200 | Yes | Robustness |
| API | API-6 compatibility | `tests/test_conversation_api.py` | existing history fields still present; `debug_timeline` defaults to list | Yes | Backward compatible |
| Console API | UI-1 types/client | `src/__tests__/api/conversation.test.ts` | mocked history payload includes `debug_timeline` and client returns it | Yes | No browser |
| Console Component | UI-2 default Timeline tab | `ConversationHistoryDetailPage.test.ts` | detail page opens Timeline first and shows title/summary/status | Yes | Mock API |
| Console Component | UI-3 expandable details | `ConversationHistoryDetailPage.test.ts` | details JSON is hidden/collapsible or clearly secondary | Yes | Implementation-specific assertion |
| Console Component | UI-4 raw tabs preserved | `ConversationHistoryDetailPage.test.ts` | Transcript / Events / Raw JSON still accessible | Yes | Regression |
| CLI | CLI-1 session debug path | `apps/cli/tests/test_chat.py` | new chat prints session id and `/conversation/history/<id>` path | Yes | No full URL required |
| Boundary | BOUNDARY-1 no live run | source scan / review | no `verify-scenario`, no autonomous endpoint invocation, no raw provider dump | Yes | Record in review |
| Manual smoke | SMOKE-1 Console route | in-app browser or user-run browser | `/conversation/history/:session_id` renders Timeline against local API | Required before accepted | If not run, mark UI smoke not run |

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 如果没有真实打开 Console 页面，不得声称 UI smoke / E2E 完成。
- 如果只运行 Vitest / unit tests，必须写成“浏览器 UI smoke 未运行”。
- UI smoke 只验证 read-only history/debug page，不验证 WebAgentFlow 操作网页。
- 如果用户自己打开页面确认，需要标记为 user acceptance，不写成 Codex 已执行。
- 不得为了本包 smoke 调用 `/exploration/autonomous-runs` 或 `verify-scenario`。

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI 可以作为外部测试操作员：

- 运行 API / CLI / Console unit tests；
- 打开 `/conversation/history/:session_id` 做 read-only UI smoke；
- 报告真实命令输出、URL、截图或观察结果。

Codex / AI 不可以：

- 伪造内部 Agent verdict；
- 把 static review 写成 tested；
- 直接调用 autonomous-run endpoints；
- 把未脱敏 raw provider payload 复制进 artifact。

## Live Run 边界（Live Run Boundary）

本轮不触发 live autonomous run。

禁止作为默认验证：

- `wagent verify`
- `verify-scenario`
- direct `POST /exploration/autonomous-runs`
- direct `POST /exploration/autonomous-runs/stream`
- product UI 触发 autonomous run

如果用户另行明确要求 live run，必须按根 `AGENTS.md` reporting style 记录
`pass_gate.status`、`run_id`、Supervisor verdict 和 scorecard；但该 live run 不属于本包
默认验收。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| E2E | 本包是 read-only debug surface，首版不要求 Playwright E2E | 真实布局问题由 required Console route smoke 兜底 |
| `verify-scenario` | 不属于本包，且会触发 live autonomous verification | 无；本包不改变 learning/execution |
| autonomous run | 本包只读 conversation history | 无；禁止默认触发 |
| backend terminal full log dump | 明确非目标 | 无；调试入口应在 Console history detail |
