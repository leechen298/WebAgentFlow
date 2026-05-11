# Conversation CLI-driven E2E

Date: 2026-05-11
Base commit at run time: `7af790f2ba320ced0383d6a664a2b1f09ac3f5c7`
Branch: `v0.1-local`
Working tree: included uncommitted M11.0.6 follow-up changes plus this
E2E/Codex testing-track work.

## Scope

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

## New Test

`apps/e2e/tests/conversation/cli-runtime.spec.ts`

Coverage:

- creates an idle conversation session through `wagent conversation start`
- sends explicit `/replay <learned_path_id> <url>` through
  `wagent conversation send`
- asserts dispatch result: `command_kind=replay`, `next_status=completed`,
  `replay_status=succeeded`, `drift_status=none`
- reads completed status through `wagent conversation status`
- reads transcript through `wagent conversation transcript`
- reads lifecycle events through `wagent conversation events`
- asserts no `replay_failed` event is recorded

## Commands

### Scoped CLI E2E in default sandbox

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/cli-runtime.spec.ts
```

Result: **BLOCKED / exit 1** in the default sandbox.

Excerpt:

```text
wagent conversation: cannot reach API at http://127.0.0.1:8001.
Is WebAgentFlow running? ([Errno 1] Operation not permitted)
```

### Scoped CLI E2E outside sandbox

```bash
pnpm --filter @web-agent-flow/e2e exec playwright test tests/conversation/cli-runtime.spec.ts
```

Result: **PASS / exit 0**

Excerpt:

```text
Running 1 test using 1 worker
1 passed (5.0s)
```

### Full deterministic E2E outside sandbox

```bash
pnpm run test:e2e
```

Result: **PASS / exit 0**

Excerpt:

```text
Running 11 tests using 4 workers
11 passed (13.4s)
```

## Summary

| Area | Status | Evidence |
| --- | --- | --- |
| Conversation CLI-driven E2E | PASS | scoped Playwright run |
| Conversation API-request runtime E2E | PASS | full `pnpm run test:e2e` |
| Replay deterministic E2E | PASS | full `pnpm run test:e2e` |
| Autonomous endpoints called | NO | no `/exploration/autonomous-runs` or `/stream` |
| LLM provider used | NO | deterministic E2E |

## Notes

- The default sandbox still blocks localhost API access for this E2E shape.
  This is an environment permission issue, not a CLI or runtime regression.
- The passing evidence comes from the non-sandbox rerun, matching prior replay
  and conversation runtime E2E evidence behavior.
