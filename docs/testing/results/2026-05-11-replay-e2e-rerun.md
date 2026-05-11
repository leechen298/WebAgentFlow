# Replay E2E Rerun — Fresh Evidence

Date: 2026-05-11
Base commit at run time: `0c009f0774ef042265e378841851b1ff9d814c80`
Branch: `v0.1-local`
Working tree: included uncommitted 11.0.7 test / evidence changes.

## Scope

复跑 M10.2 replay deterministic E2E，确认此前本地 sandbox 下的
`connect EPERM 127.0.0.1:8001` 和 Chromium permission failure 是否仍阻塞。

本报告不执行 live autonomous run，不调用 `/exploration/autonomous-runs` 或
`/exploration/autonomous-runs/stream`，不依赖 LLM provider。

## Commands

### API health

```bash
curl -sS -i http://127.0.0.1:8001/health
```

Result: **PASS / exit 0**

Excerpt:

```text
HTTP/1.1 200 OK
{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}
```

### Sandbox rerun

```bash
pnpm run test:e2e
```

Result: **BLOCKED / exit 1** in the default sandbox.

Excerpt:

```text
apiRequestContext.post: connect EPERM 127.0.0.1:8001
bootstrap_check_in ... Permission denied
```

### Non-sandbox rerun

```bash
pnpm run test:e2e
```

Result: **PASS / exit 0**

Excerpt:

```text
Running 9 tests using 2 workers
9 passed (14.2s)
```

## Case Summary

| Area | Status | Evidence |
| --- | --- | --- |
| Replay API E2E | PASS | `api.spec.ts` 8/8 passed |
| Replay catalog UI E2E | PASS | `catalog-ui.spec.ts` 1/1 passed |
| Autonomous endpoints called | NO | E2E suite uses replay/catalog routes only |
| LLM provider used | NO | deterministic E2E |

## Notes

- The previous BLOCKED state was caused by local sandbox permissions, not by a
  replay product regression.
- Deterministic E2E still requires local services and seeded replay fixtures.
