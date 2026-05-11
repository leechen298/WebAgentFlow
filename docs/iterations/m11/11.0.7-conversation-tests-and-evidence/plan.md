# 实施计划

## 触及的文件 / 模块

- `apps/e2e/tests/conversation/runtime.spec.ts` — conversation runtime deterministic E2E。
- `docs/testing/results/2026-05-11-replay-e2e-rerun.md` — replay E2E fresh evidence。
- `docs/testing/results/2026-05-11-conversation-baseline.md` — conversation baseline evidence。
- `docs/testing/results/2026-05-11-conversation-runtime-e2e.md` — conversation E2E evidence。
- `docs/testing/live-smoke.md` — verify-scenario manual live smoke runbook。
- `docs/testing/README.md` / `docs/testing/e2e.md` / `docs/testing/features/conversation.md` — 状态同步。

## E2E 场景

Conversation runtime E2E 使用既有 replay fixture：

1. `POST /conversation/sessions` 创建 idle session。
2. `POST /conversation/sessions/{session_id}/dispatch` 发送
   `/replay <learned_path_id> <url>`。
3. 断言 dispatch response：
   - `command_kind=replay`
   - `allowed=true`
   - `next_status=completed`
   - `replay_result.replay_status=succeeded`
   - `replay_result.drift_status=none`
4. 读取 session，断言 status 为 `completed`。
5. 读取 transcript，断言 user message 被记录。
6. 读取 events，断言包含 `command_parsed`、`state_changed`、`replay_completed`，
   且不包含 `replay_failed`。

## 验证

```bash
curl -sS -i http://127.0.0.1:8001/health
cd apps/api && ../../.venv/bin/pytest tests/test_conversation_replay_hook.py tests/test_conversation_orchestrator.py tests/test_conversation_api.py tests/test_conversation_repo.py tests/test_conversation_commands.py tests/test_conversation_state.py tests/test_learned_path_replay.py tests/test_exploration_learned_paths_api.py -v
cd apps/cli && ../../.venv/bin/pytest tests/test_conversation.py -v
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/runtime.spec.ts
pnpm run test:e2e
git diff --check
```

## 边界

- 不调用 `/exploration/autonomous-runs` 或 `/stream`。
- 不依赖 LLM provider。
- 不改 M10 replay contract。
- 不新增 M11.1 详情目录。
