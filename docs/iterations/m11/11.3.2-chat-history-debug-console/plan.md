# 实施计划（Implementation Plan）

状态：ready_for_implementation

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`

## 文件 / 模块

- `apps/api/app/schemas/conversation.py` - 新增 session summary、list response、history response schemas。
- `apps/api/app/repos/conversation_repo.py` - 新增 session list 查询和 summary 所需只读查询。
- `apps/api/app/services/conversation/history.py` - 新增 aggregate history read-model service。
- `apps/api/app/routers/conversation.py` - 新增 `GET /conversation/sessions` 和 `GET /conversation/sessions/{session_id}/history`。
- `apps/api/tests/test_conversation_api.py` - 覆盖 list / history endpoints。
- `apps/api/tests/test_conversation_repo.py` - 覆盖 repository list filters if implemented there。
- `apps/cli/wagent/conversation.py` - 新增 `list` / `history` subcommands。
- `apps/cli/wagent/chat.py` - 输出 session id，新增 `--resume`。
- `apps/cli/tests/test_conversation.py` - 覆盖 list / history CLI。
- `apps/cli/tests/test_chat.py` - 覆盖 session id 输出和 resume behavior。
- `apps/console/src/api/conversation.ts` - 新增 Console conversation API client。
- `apps/console/src/api/index.ts` - 如现有导出模式需要，导出 conversation API。
- `apps/console/src/pages/ConversationHistoryPage.vue` - session list 页面。
- `apps/console/src/pages/ConversationHistoryDetailPage.vue` - session detail 页面。
- `apps/console/src/router/index.ts` - 新增 routes。
- `apps/console/src/layouts/MainLayout.vue` - 新增 nav entry。
- `apps/console/src/i18n/locales/en.ts` - 新增英文文案。
- `apps/console/src/i18n/locales/zh.ts` - 新增中文文案。
- `apps/console/src/i18n/locales/ja.ts` - 新增日文文案。
- `apps/console/src/__tests__/api/conversation.test.ts` - API client tests。
- `apps/console/src/__tests__/components/ConversationHistoryPage.test.ts` - list page tests。
- `apps/console/src/__tests__/components/ConversationHistoryDetailPage.test.ts` - detail page tests。
- `apps/console/src/__tests__/router/index.test.ts` / `MainLayout.test.ts` - route / nav tests。

## 步骤

1. 先补 API schema 和测试。
   - 写 `ConversationSessionSummaryResponse`、`ConversationSessionListResponse`、`ConversationHistoryResponse` 预期测试。
   - 覆盖 empty session、learned_actions、learning_runs、replay_summaries。

2. 实现 repository / history service。
   - `list_sessions()` 支持 mode / status / updated range / limit。
   - `ConversationHistoryService` 生成 summary 和 aggregate payload。
   - malformed historical event 不让整个 history endpoint 失败。

3. 接 API routes。
   - 新增 `GET /conversation/sessions`。
   - 新增 `GET /conversation/sessions/{session_id}/history`。
   - 保持既有 endpoints tests 通过。

4. 补 CLI `wagent conversation`。
   - 新增 `list` 和 `history` subcommands。
   - 继续使用 HTTP API，不引入 DB / repo / replay / autonomous imports。
   - 覆盖 `--pretty` 和 params。

5. 补 `wagent chat` session id / resume。
   - 新 session 创建后输出 session id。
   - `--resume` 先读取 session 并校验 `interactive_chat`。
   - resume 不创建 session、不修改 metadata。
   - `--resume` + `--headless` 按 contract 拒绝。

6. 补 Console API client。
   - `listConversationSessions()`。
   - `getConversationHistory()`。
   - 补 API client unit tests。

7. 补 Console route / nav / i18n。
   - route path：`/conversation/history` 和 `/conversation/history/:session_id`。
   - nav item 使用 history icon 或同类图标。
   - title/menu key 对齐。

8. 实现 Console list page。
   - filter bar：mode / status / updated range / limit。
   - table：updated_at、session id、mode、status、last messages、learned action count、event count。
   - row action：detail。
   - copy session id。

9. 实现 Console detail page。
   - summary header。
   - tabs：Transcript、Events、Learned Actions、Replay / Learning Evidence、Raw JSON。
   - Raw JSON 展示 aggregate payload 并支持复制。
   - loading / error / empty states。

10. 运行 scoped verification。
    - API pytest + ruff。
    - CLI pytest + ruff。
    - Console Vitest scoped tests。
    - `git diff --check`。
    - 如果执行 manual Console smoke，记录 URL / 截图 / 观察结果到 `review.md`。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `cd apps/api && ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py -q` | API list/history endpoints and repo filters pass | Yes | no autonomous run |
| `cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py tests/test_chat.py -q` | CLI list/history/session id/resume pass | Yes | no browser required |
| `pnpm --filter @web-agent-flow/console test -- --run src/__tests__/api/conversation.test.ts src/__tests__/router/index.test.ts src/__tests__/components/ConversationHistoryPage.test.ts src/__tests__/components/ConversationHistoryDetailPage.test.ts` | Console API/router/pages pass | Yes | component tests only |
| `cd apps/api && ../../.venv/bin/ruff check app/routers/conversation.py app/repos/conversation_repo.py app/services/conversation app/schemas/conversation.py tests/test_conversation_api.py tests/test_conversation_repo.py` | API lint clean | Yes | scoped |
| `cd apps/cli && ../../.venv/bin/ruff check wagent/conversation.py wagent/chat.py tests/test_conversation.py tests/test_chat.py` | CLI lint clean | Yes | scoped |
| `git diff --check` | whitespace clean | Yes | all changed files |
| Console manual route smoke | `/conversation/history` and detail page load | Yes | required before final acceptance; not live autonomous verification |

## 复核清单（Review Checklist）

- [ ] 实现仍然匹配 `contract.md`。
- [ ] 没有修改 existing conversation endpoints 的 response contract。
- [ ] 没有新增 DB migration。
- [ ] `GET /conversation/sessions` 支持 mode / status / time / limit filters。
- [ ] `GET /conversation/sessions/{session_id}/history` 返回 aggregate payload。
- [ ] CLI `conversation list/history` 输出 JSON。
- [ ] `wagent chat` 输出 session id。
- [ ] `wagent chat --resume` 只能 resume `interactive_chat` session。
- [ ] Console list / detail 页面可读、可复制 session id / raw JSON。
- [ ] 最终 acceptance 前已真实打开 `/conversation/history` 并记录 route smoke evidence；如未运行，状态不得写成 accepted。
- [ ] 未触发 `verify-scenario` 或 autonomous run。
- [ ] 验证命令已执行并记录到 `review.md`，或写明 not run / unverified 和原因。
