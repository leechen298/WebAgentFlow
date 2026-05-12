# Conversation CLI-driven 确定性 E2E

日期：2026-05-11
运行时 base commit：`7af790f2ba320ced0383d6a664a2b1f09ac3f5c7`
分支：`v0.1-local`
工作区：包含未提交的 M11.0.6 follow-up 改动，以及本轮 E2E / Agent
testing track 改动。

## 范围

新增并运行第一个 `wagent conversation` CLI-driven deterministic E2E。

该测试使用真实 CLI subprocess：

```text
.venv/bin/wagent conversation start
-> .venv/bin/wagent conversation send <session_id> --content "/replay <learned_path_id> <url>"
-> .venv/bin/wagent conversation status <session_id>
-> .venv/bin/wagent conversation transcript <session_id>
-> .venv/bin/wagent conversation events <session_id>
```

它打真实 Conversation API，不 mock `httpx`，不调用 autonomous run，不依赖 LLM
provider。

## 新增测试

`apps/e2e/tests/conversation/cli-runtime.spec.ts`

覆盖：

- creates an idle conversation session through `wagent conversation start`
- sends explicit `/replay <learned_path_id> <url>` through
  `wagent conversation send`
- asserts dispatch result: `command_kind=replay`, `next_status=completed`,
  `replay_status=succeeded`, `drift_status=none`
- reads completed status through `wagent conversation status`
- reads transcript through `wagent conversation transcript`
- reads lifecycle events through `wagent conversation events`
- asserts no `replay_failed` event is recorded

## 命令

### 默认 sandbox 下 scoped CLI E2E

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/cli-runtime.spec.ts
```

结果：默认 sandbox 下 **BLOCKED / exit 1**。

摘录：

```text
wagent conversation: cannot reach API at http://127.0.0.1:8001.
Is WebAgentFlow running? ([Errno 1] Operation not permitted)
```

### 非 sandbox scoped CLI E2E

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/cli-runtime.spec.ts
```

结果：**PASS / exit 0**

摘录：

```text
Running 1 test using 1 worker
1 passed (5.0s)
```

### 非 sandbox 全量确定性 E2E

```bash
pnpm run test:e2e
```

结果：**PASS / exit 0**

摘录：

```text
Running 11 tests using 4 workers
11 passed (13.4s)
```

## 摘要

| 区域 | 状态 | 证据 |
| --- | --- | --- |
| Conversation CLI-driven E2E | PASS | scoped Playwright run |
| Conversation API-request runtime E2E | PASS | full `pnpm run test:e2e` |
| Replay deterministic E2E | PASS | full `pnpm run test:e2e` |
| Autonomous endpoints called | NO | no `/exploration/autonomous-runs` or `/stream` |
| LLM provider used | NO | deterministic E2E |

## 备注

- The default sandbox still blocks localhost API access for this E2E shape.
  This is an environment permission issue, not a CLI or runtime regression.
- The passing evidence comes from the non-sandbox rerun, matching prior replay
  and conversation runtime E2E evidence behavior.
