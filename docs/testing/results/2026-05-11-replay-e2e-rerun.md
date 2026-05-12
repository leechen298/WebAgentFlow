# Replay E2E 复跑 — Fresh Evidence

日期：2026-05-11
运行时 base commit：`0c009f0774ef042265e378841851b1ff9d814c80`
分支：`v0.1-local`
工作区：包含未提交的 11.0.7 测试 / 证据改动。

## 范围

复跑 M10.2 replay deterministic E2E，确认此前本地 sandbox 下的
`connect EPERM 127.0.0.1:8001` 和 Chromium permission failure 是否仍阻塞。

本报告不执行 live autonomous run，不调用 `/exploration/autonomous-runs` 或
`/exploration/autonomous-runs/stream`，不依赖 LLM provider。

## 命令

### API health

```bash
curl -sS -i http://127.0.0.1:8001/health
```

结果：**PASS / exit 0**

摘录：

```text
HTTP/1.1 200 OK
{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}
```

### Sandbox 复跑

```bash
pnpm run test:e2e
```

结果：默认 sandbox 下 **BLOCKED / exit 1**。

摘录：

```text
apiRequestContext.post: connect EPERM 127.0.0.1:8001
bootstrap_check_in ... Permission denied
```

### 非 sandbox 复跑

```bash
pnpm run test:e2e
```

结果：**PASS / exit 0**

摘录：

```text
Running 9 tests using 2 workers
9 passed (14.2s)
```

## 用例摘要

| 区域 | 状态 | 证据 |
| --- | --- | --- |
| Replay API E2E | PASS | `api.spec.ts` 8/8 passed |
| Replay catalog UI E2E | PASS | `catalog-ui.spec.ts` 1/1 passed |
| Autonomous endpoints called | NO | E2E suite uses replay/catalog routes only |
| LLM provider used | NO | deterministic E2E |

## 备注

- The previous BLOCKED state was caused by local sandbox permissions, not by a
  replay product regression.
- Deterministic E2E still requires local services and seeded replay fixtures.
