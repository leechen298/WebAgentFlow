# 技术设计（Technical Design）

状态：docs_generated_pending_design_review

## 当前状态（Current State）

已有实现基础：

- `apps/api/app/services/conversation/history.py` 聚合 session、messages、events、
  learned_actions、learning_runs、replay_summaries、llm_traces、entry_gate_traces 和 raw。
- `apps/api/app/schemas/conversation.py` 已有 `ConversationHistoryResponse`。
- `apps/api/app/routers/conversation.py` 已暴露
  `GET /conversation/sessions/{session_id}/history`。
- `apps/console/src/pages/ConversationHistoryDetailPage.vue` 已展示 session info、
  Transcript、Events、Learned Actions、Evidence、Raw JSON。
- `apps/console/src/api/conversation.ts` 已有 history payload 类型和 `getConversationHistory()`。
- `wagent chat` 创建 session 后输出 session id，但调试提示还不够明确。

当前缺口：

- Detail 页的默认阅读顺序仍偏 raw：用户要自己理解 event type 和 JSON payload。
- API 没有面向人类的 timeline read model。
- 后端终端日志没有也不应该承载完整调试语义。
- CLI 没有直接告诉用户后台详情 path。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Timeline 是只读派生 read model | `ConversationHistoryService` 新增 timeline builder，从 messages/events/traces 派生 | API-1 / API-2 | 不新增 DB 表 |
| Timeline 默认人类可读 | schema 提供 `title` / `summary` / `status` / `kind`，Console 默认展示 Timeline tab | UI-1 / UI-2 | Raw JSON 保留在后续 tab |
| 不暴露 private payload | 复用 `conversation_event_public_payload()`、`session_public_payload()` 和 public trace payload | API-3 / UI-4 | 增加 private-token scan test |
| History response 向后兼容 | `debug_timeline: list[...] = Field(default_factory=list)` | API-4 | 旧调用方忽略即可 |
| 终端不 dump raw payload | 不新增 provider raw logging；CLI 只输出 session id/path | CLI-1 / review scan | 如需日志增强，只限 correlation summary |
| 不改变 runtime 行为 | 只改 history read service、Console read UI、CLI handoff 文案 | REG-1 | 不触发 learning/replay |
| 不触发 live run | test-plan 明确排除 verify-scenario/autonomous run | BOUNDARY-1 | UI smoke 只打开 history page |

## 实现方案（Proposed Implementation）

### API schema

修改 `apps/api/app/schemas/conversation.py`：

- 新增 `ConversationDebugTimelineRawRef`。
- 新增 `ConversationDebugTimelineItem`。
- 在 `ConversationHistoryResponse` 增加：

```python
debug_timeline: list[ConversationDebugTimelineItem] = Field(default_factory=list)
```

建议字段：

```python
class ConversationDebugTimelineItem(BaseModel):
    id: str
    kind: str
    title: str
    summary: str
    status: Literal["info", "waiting", "running", "success", "warning", "error", "cancelled"]
    created_at: datetime | None = None
    source: Literal["message", "event", "trace", "derived"]
    message_id: str | None = None
    event_id: str | None = None
    trace_id: str | None = None
    related_event_ids: list[str] = Field(default_factory=list)
    related_trace_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    raw_ref: ConversationDebugTimelineRawRef | None = None
```

### History service

修改 `apps/api/app/services/conversation/history.py`：

- 新增 `_build_debug_timeline(session, messages, events, llm_traces, entry_gate_traces)`。
- 在 `get_history()` 返回 `ConversationHistoryResponse(debug_timeline=...)`。
- Timeline builder 保持 deterministic：
  - 先按 created_at / append order 合并 messages、events、trace summaries；
  - 对已知 event type 生成专门标题；
  - 对未知 event type 生成通用“记录事件：<type>”节点；
  - 所有 details 先走现有 public payload / redaction helper；
  - 空 payload、malformed payload 不让 endpoint 失败。

首版 mapping 建议：

| Source | Condition | Timeline kind | Title | Status |
|---|---|---|---|---|
| user message | role=`user` and URL-like content | `user_message` | 用户输入页面地址 | `info` |
| user message | role=`user` generic | `user_message` | 用户输入需求 | `info` |
| agent message | role=`agent` | `agent_response` | 我回复用户 | status from provenance/fallback |
| event | `entry_gate_recorded` | `entry_gate` | 入口门禁判断 | `info` / `warning` |
| event | `llm_trace_recorded` | `llm_trace` | LLM 调用完成 | `info` / `warning` / `error` |
| event | `chat_progress_recorded` + `progress_kind=unknown_target_choice_created` | `action_options` | 生成下一步选项 | `waiting` |
| event | `chat_progress_recorded` + `progress_kind` contains `choice_selected` | `pending_choice` | 用户选择下一步 | `info` |
| event | `chat_learning_started` | `learning` | 开始学习页面操作 | `running` |
| event | `chat_learning_completed` | `learning` | 学习完成 | `success` / `warning` |
| event | `chat_execution_started` | `replay` | 开始执行已学操作 | `running` |
| event | replay/execution completed payload | `replay` | 执行完成 | `success` / `warning` / `error` |
| event | recovery/failure progress | `recovery` | 进入失败恢复 | `warning` |
| event | cancel command/progress | `cancel` | 用户取消当前任务 | `cancelled` |

### Console API client

修改 `apps/console/src/api/conversation.ts`：

- 增加 `ConversationDebugTimelineItem` type。
- 在 `ConversationHistoryPayload` 增加 `debug_timeline`。

### Console detail UI

修改 `apps/console/src/pages/ConversationHistoryDetailPage.vue`：

- 默认 active tab 改为 `timeline`。
- 新增 Timeline tab，位于 Transcript 前。
- Timeline item 显示：
  - title；
  - status tag；
  - kind / source；
  - created_at；
  - summary；
  - message_id / event_id / trace_id copyable；
  - details collapsible JSON。
- Existing Transcript / Events / Evidence / Raw JSON tabs 保留。
- 空 timeline 时显示 empty，并提示查看 Events / Raw JSON。

样式要求：

- 不做营销式 hero / 卡片堆叠；保持 Console 工具页面密度。
- Timeline row 可扫描，状态标签颜色克制。
- Raw JSON 不默认占据第一阅读面。

### CLI handoff

修改 `apps/cli/wagent/chat.py`：

- 新 session 创建后输出：

```text
WAgent > 本次会话 ID：<session_id>。调试详情：/conversation/history/<session_id>
```

- 如果以后新增 console base URL 配置，应另立包定义；本轮不猜完整 URL。

### Optional low-noise backend log

本轮不要求新增 backend log middleware。若实现阶段发现需要最小关联日志，只允许在 dispatch path 记录：

- session_id；
- message_id；
- command_kind；
- next_status；
- events_appended count；
- latency_ms；
- error short summary。

不得记录 full payload。该部分建议作为 optional，不作为本包 required deliverable。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 复用 existing history endpoint | No new route |
| API response schema | Yes | Add `debug_timeline` to history response | Backward-compatible field |
| Database schema / migration | No | Derived from existing tables/events | No migration |
| CLI | Yes | Improve debug handoff text | Existing chat behavior unchanged |
| Console UI | Yes | Add default Timeline tab in history detail | Existing tabs remain |
| Conversation events | No | Read existing events only | No runtime event contract change |
| Replay execution | No | Read-only display | No behavior change |
| Reporter | No | Read-only display | No behavior change |
| Worker / async jobs | No | N/A | N/A |
| Tests / fixtures | Yes | API / Console / CLI regression tests | No target fixture dependency |
| Docs | Yes | Iteration docs and M11 index | N/A |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

- No DB migration。
- Add Pydantic response models for timeline items。
- Add frontend TypeScript types。
- `debug_timeline` defaults to `[]` for compatibility。

## 服务 / 模块设计（Service / Module Design）

建议新增私有 helper，不创建大而泛的 logging service：

- `_build_debug_timeline(...)`
- `_timeline_item_from_message(...)`
- `_timeline_item_from_event(...)`
- `_timeline_status_from_payload(...)`
- `_safe_timeline_details(...)`

这些 helper 位于 `apps/api/app/services/conversation/history.py` 或同 package 下新建
`debug_timeline.py`。如果 `history.py` 继续膨胀，优先新建
`apps/api/app/services/conversation/debug_timeline.py`，由 `ConversationHistoryService`
调用。

## 数据流（Data Flow）

```text
wagent chat creates / dispatches session
  -> conversation messages/events/traces are persisted
  -> user opens /conversation/history/:session_id
  -> API get_history loads messages/events/traces
  -> debug_timeline builder derives human-readable steps
  -> Console renders Timeline first, raw evidence remains expandable
```

## 状态推导（Status / State Derivation）

Timeline status 只用于显示：

- payload 明确 success / completed / succeeded / verified -> `success`；
- payload 明确 failure / failed / error / provider_error -> `error`；
- payload 是 fallback / low confidence / needs review / unverified -> `warning`；
- progress 表示 created options / waiting for user -> `waiting`；
- started / running -> `running`；
- cancel -> `cancelled`；
- default -> `info`。

不得从 status 推导 product pass/fail。

## 兼容性（Compatibility）

- Existing API clients ignore `debug_timeline`。
- Existing Console tabs remain available。
- Existing CLI tests should only need updated expected handoff text。
- Unknown historical event payloads still render as generic event or remain visible in Events tab。

## 失败 / 边界情况（Failure / Edge Cases）

- Missing session: existing 404 behavior unchanged。
- Empty session: timeline empty or contains session-created derived item; design review decides. Recommended: empty list + empty state。
- Malformed event payload: generic item with warning status, no endpoint failure。
- Trace missing from `llm_traces`: agent message still renders provenance summary, related trace id may remain unresolved。
- Non-interactive sessions: timeline still works but may have fewer specialized labels。
- Very long details: Console collapses details and keeps Raw JSON tab scrollable。

## 非目标（Non-goals）

- No raw provider request dump。
- No terminal full payload logging。
- No new log storage / search / retention policy。
- No live run。
- No changes to learning / replay / task planning semantics。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| API history service | Timeline items derive from messages/events/traces and stay redacted | `test-plan.md` API-1..API-5 |
| API compatibility | Existing history shape remains and new field defaults safely | `test-plan.md` API-6 |
| Console API/types | Frontend consumes `debug_timeline` | `test-plan.md` UI-1 |
| Console detail UI | Timeline tab renders first, expandable details, empty/error states | `test-plan.md` UI-2..UI-4 |
| CLI handoff | New session line includes history path, no behavior change | `test-plan.md` CLI-1 |
| Boundary scan | No autonomous endpoint / verify-scenario / raw private payload exposure | `test-plan.md` BOUNDARY-1 |

## 验证命令入口（Validation Commands）

```bash
cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_api.py -q
cd apps/cli && ../../.venv/bin/python -m pytest tests/test_chat.py -q
pnpm --filter @web-agent-flow/console test -- --run src/__tests__/api/conversation.test.ts src/__tests__/components/ConversationHistoryDetailPage.test.ts
cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/history.py app/schemas/conversation.py tests/test_conversation_api.py ../cli/wagent/chat.py ../cli/tests/test_chat.py
git diff --check
```
