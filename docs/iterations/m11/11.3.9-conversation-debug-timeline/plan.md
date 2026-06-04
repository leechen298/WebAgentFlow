# 实施计划（Implementation Plan）

状态：docs_generated_pending_design_review

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`

## 文档生成计划（如适用）

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.9-conversation-debug-timeline/` |
| Package type | `code` |
| Parent / child route | N/A；standalone M11.3 follow-up package |
| Required docs | `README.md` / `intent.md` / `contract.md` / `technical-design.md` / `test-plan.md` / `plan.md` / `review.md` |
| Source inputs read | `AGENTS.md`; `docs/product-model.md`; `docs/iterations/README.md`; `docs/iterations/AGENTS.zh.md`; `docs/iterations/m11/README.md`; `docs/iterations/m11/m11-plan.md`; `docs/iterations/m11/11.3.2-chat-history-debug-console/*`; current `ConversationHistoryDetailPage.vue`; current conversation history API/service/schema |
| Contract / status / evidence changes | Backward-compatible `debug_timeline` history read model; Console debug timeline display; CLI debug path handoff; no runtime behavior change |
| Design-review gate | Required；implementation cannot start until `review.md` records approved design and `implementation_authorized: yes` |
| Test-plan trigger | Required；API + Console + CLI + UI smoke boundaries |
| Implementation authorization boundary | Current docs generation does not authorize implementation |
| Stop conditions | Missing design approval; schema/API conflict; private payload leak; live-run boundary violation; scope drift into logging platform / runtime behavior |
| Handoff / checkpoint | After design review, implementation Agent reads full seven-doc package and runs scoped tests from `test-plan.md` |

## 文件 / 模块

- `apps/api/app/schemas/conversation.py` - add debug timeline response schemas and `debug_timeline` field.
- `apps/api/app/services/conversation/history.py` or `apps/api/app/services/conversation/debug_timeline.py` - build human-readable timeline from persisted public-safe history.
- `apps/api/tests/test_conversation_api.py` and/or focused history service tests - cover timeline derivation, compatibility, redaction.
- `apps/console/src/api/conversation.ts` - add timeline TypeScript types.
- `apps/console/src/pages/ConversationHistoryDetailPage.vue` - add default Timeline tab and expandable details.
- `apps/console/src/i18n/locales/en.ts` / `zh.ts` / `ja.ts` - add Timeline labels.
- `apps/console/src/__tests__/api/conversation.test.ts` - cover payload type/client behavior.
- `apps/console/src/__tests__/components/ConversationHistoryDetailPage.test.ts` - cover Timeline display and existing tab preservation.
- `apps/cli/wagent/chat.py` - improve session debug handoff line.
- `apps/cli/tests/test_chat.py` - cover debug path output.
- `docs/iterations/m11/README.md` and `docs/iterations/m11/m11-plan.md` - keep package discoverable.

## 步骤

1. Design review gate.
   - User or reviewer approves this package.
   - Update `review.md` with design decision and `implementation_authorized: yes`.
   - Stop if design changes are requested.

2. Add API schema tests first.
   - Assert history response includes `debug_timeline`.
   - Assert existing fields remain unchanged.
   - Add redaction assertions for private map / secret-like tokens.

3. Implement timeline builder.
   - Prefer a small dedicated module if `history.py` would become too large.
   - Map known message/event/trace cases.
   - Keep fallback safe for unknown event types.
   - Ensure malformed payload never breaks whole history response.

4. Wire API history response.
   - `ConversationHistoryService.get_history()` populates `debug_timeline`.
   - Keep raw/events/transcript fields unchanged.

5. Update Console API types and tests.
   - Add `ConversationDebugTimelineItem`.
   - Update mocked history payloads.

6. Update Console detail UI.
   - Add Timeline tab before Transcript.
   - Default `activeTab = 'timeline'`.
   - Render title, summary, status, source/kind/time and copyable ids.
   - Keep details collapsed or secondary.
   - Preserve existing tabs.

7. Update i18n.
   - Add labels for Timeline tab, status labels, details, empty state.

8. Update CLI handoff.
   - New session creation line includes `/conversation/history/<session_id>`.
   - Do not invent full Console URL unless a reviewed config exists.

9. Run verification.
   - API pytest / ruff.
   - CLI pytest / ruff.
   - Console Vitest scoped tests.
   - `git diff --check`.
   - Optional/required-for-accepted Console route smoke, depending on closeout target.

10. Review and closeout.
    - Update `review.md` with actual changed files, command outputs, UI smoke status and not-run items.
    - If UI smoke not run, final status must not be `accepted`.

## Checkpoints

| Checkpoint | Required update | Continue condition | Stop condition |
|---|---|---|---|
| docs / design | `review.md` design entry | approved + `implementation_authorized: yes` | changes requested / missing docs |
| API implementation | changed files + API tests | timeline redaction and compatibility pass | private leak / schema conflict |
| Console / CLI implementation | changed files + UI/CLI tests | timeline default view and CLI handoff pass | existing tabs broken / numeric raw-first UX persists |
| closeout | `FINAL_STATUS`, validation evidence, not-run table | tests pass and no boundary violation | UI smoke missing if trying to claim accepted |

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && ../../.venv/bin/python -m pytest tests/test_conversation_api.py -q` | History API timeline, compatibility and redaction tests pass | Yes | May replace with narrower service test if added |
| `cd apps/cli && ../../.venv/bin/python -m pytest tests/test_chat.py -q` | CLI debug path handoff and existing chat tests pass | Yes | No browser |
| `pnpm --filter @web-agent-flow/console test -- --run src/__tests__/api/conversation.test.ts src/__tests__/components/ConversationHistoryDetailPage.test.ts` | Console API/detail timeline tests pass | Yes | Component tests only |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/history.py app/schemas/conversation.py tests/test_conversation_api.py ../cli/wagent/chat.py ../cli/tests/test_chat.py` | API / CLI lint clean | Yes | Add `debug_timeline.py` if created |
| `git diff --check` | whitespace clean | Yes | all changed files |
| Console route smoke | `/conversation/history/:session_id` renders Timeline against local API | Yes | Required before `accepted`; not autonomous run |

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] `debug_timeline` 只读、脱敏、向后兼容。
- [ ] Timeline 默认人类可读，不以 raw JSON 为第一阅读面。
- [ ] Events / Raw JSON tabs 保留。
- [ ] CLI 输出 session id 和 relative history path。
- [ ] 后端终端日志没有 raw payload dump。
- [ ] 没有新增 DB migration。
- [ ] 没有触发 `verify-scenario` 或 autonomous run。
- [ ] 验证命令已执行并记录到 `review.md`，或写明 not run / unverified 和原因。
- [ ] 如声称 accepted，必须有真实 Console route smoke 证据。
