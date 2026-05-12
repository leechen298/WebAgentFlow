# Conversation Runtime 确定性 E2E — 首次冒烟

日期：2026-05-11
运行时 base commit：`0c009f0774ef042265e378841851b1ff9d814c80`
分支：`v0.1-local`
工作区：包含未提交的 11.0.7 测试 / 证据改动。

## 范围

新增并运行第一个 conversation runtime deterministic E2E：

```text
POST /conversation/sessions
-> POST /conversation/sessions/{session_id}/dispatch with /replay <learned_path_id> <url>
-> M10 replay hook
-> GET /conversation/sessions/{session_id}
-> GET /conversation/sessions/{session_id}/transcript
-> GET /conversation/sessions/{session_id}/events
```

本测试不做 LearnedPath selection，不做 task-to-path，不调用 autonomous run，不依赖
LLM provider。

## 新增测试

`apps/e2e/tests/conversation/runtime.spec.ts`

覆盖：

- creates an idle conversation session
- dispatches explicit `/replay <learned_path_id> <url>`
- asserts replay summary: `replay_status=succeeded`, `drift_status=none`
- asserts session status becomes `completed`
- asserts transcript records the user command
- asserts events include `command_parsed`, `state_changed`, `replay_completed`
- asserts events do not include `replay_failed`

## 命令

### 本地迁移前置条件

The first scoped run hit `POST /conversation/sessions` returning HTTP 500
because the local PostgreSQL database had not applied the conversation tables.
The local test database was updated with:

```bash
cd apps/api && ../../.venv/bin/alembic -c alembic.ini upgrade head
```

结果：**PASS / exit 0**

摘录：

```text
Running upgrade 20260502_0001 -> a93d26f33594, add conversation tables
```

### Scoped conversation E2E

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/runtime.spec.ts
```

结果：**PASS / exit 0**

摘录：

```text
Running 1 test using 1 worker
1 passed (4.4s)
```

### 全量确定性 E2E

```bash
pnpm run test:e2e
```

结果：**PASS / exit 0**

摘录：

```text
Running 10 tests using 3 workers
10 passed (14.0s)
```

## 摘要

| 区域 | 状态 | 证据 |
| --- | --- | --- |
| Conversation runtime E2E | PASS | scoped Playwright run |
| Replay regression E2E | PASS | full `pnpm run test:e2e` |
| Autonomous endpoints called | NO | no `/exploration/autonomous-runs` or `/stream` |
| LLM provider used | NO | deterministic E2E |

## 备注

- The first scoped run exposed an over-strict transcript assertion. The API
  correctly returns id/session_id/metadata/created_at alongside role/content;
  the test now asserts behavior with `toMatchObject`.
- Local E2E commands required non-sandbox execution because sandboxed localhost
  and Chromium access returned EPERM.
