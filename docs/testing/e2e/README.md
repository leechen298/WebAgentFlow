# 确定性 E2E 轨道

## 范围

本文件只管理 WebAgentFlow 的 deterministic E2E。

Deterministic E2E 的定义：

- 使用 Playwright Test 执行。
- 测试代码放在 `apps/e2e/tests/`。
- 目标是稳定、可重复、可进入 CI 的回归测试。
- 使用 seeded fixtures、external fixture provider、deterministic API 或固定本地服务栈。
- 产物是测试代码、命令输出、trace / video / Playwright report，以及人类可读
  result report。

本文件不管理：

- Agent-operated UI exploratory。
- API exploratory。
- manual live smoke。
- unit / repo / component / mocked CLI tests。

这些内容分别由 `../agent-operated-ui/README.md`、`../full-test-matrix.md`、
`../current-testing-backlog.md` 或 `../live-smoke.md` 管理。

## 规则

- 不依赖 LLM provider。
- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不触发 live autonomous run。
- 不通过 `verify-scenario` 运行 live scenario。
- 使用 seeded fixtures / external fixture provider / deterministic API。
- Headless E2E 可以作为 deterministic evidence。
- Headless E2E 不等于 Agent-operated UI exploratory。
- 如果服务或浏览器权限导致无法运行，结果写 `BLOCKED`，不能写 PASS。

## 当前 E2E 套件

当前 E2E 测试代码位于：

- `apps/e2e/tests/replay/`
- `apps/e2e/tests/conversation/runtime.spec.ts`
- `apps/e2e/tests/conversation/cli-runtime.spec.ts`
- `apps/e2e/tests/conversation/task-execution.spec.ts`
- `apps/e2e/tests/conversation/task-result-reporter.spec.ts`

覆盖范围：

- Replay E2E 覆盖 M10.2 LearnedPath replay execution + drift detection。
- LearnedPath catalog E2E 覆盖 catalog list、trust filter、actions drawer、
  replay section presence，以及 seeded happy path replay。
- Conversation runtime E2E 覆盖 API-request runtime flow：
  session -> dispatch `/replay` -> replay summary -> transcript/events。
- Conversation CLI-driven E2E 覆盖真实 `wagent conversation` subprocess flow：
  start -> send `/replay <learned_path_id> <url>` -> status / transcript / events。
- Conversation task execution E2E 覆盖 11.1.6 scoped runtime execution flow
  和 11.1.7 Task Result Reporter output：seeded confirmed execution context
  -> `execute` -> replay handler evidence -> `task_result_reported`，以及自然
  preview 缺少 `target_url` 时的 blocked reporting 边界。
- Conversation task result reporter E2E 覆盖 11.1.7 scoped reporter output：
  successful replay -> `uncertain`，failed replay -> `failed`，blocked
  execution -> `blocked`，以及 `task_result_reported` event order 和 payload
  boundary。
- External fixture provider owns browser-smoke coverage for its own pages.
  WebAgentFlow E2E consumes only the provider-generated replay fixture manifest
  and the resulting seeded LearnedPath rows.

这些 E2E 都不调用 autonomous run，不依赖 LLM provider。外部 fixture provider 的
页面级 browser smoke 不保留在本仓库。

## 报告

已有 E2E 报告：

- `../results/2026-05-08-replay-e2e-first-run.md`
- `../results/2026-05-11-replay-e2e-rerun.md`
- `../results/2026-05-11-learned-path-catalog-deterministic-e2e.md`
- `../results/2026-05-11-conversation-runtime-e2e.md`
- `../results/2026-05-11-conversation-cli-e2e.md`
- `../results/2026-05-13-11-1-6-scoped-e2e.md`
- `../results/2026-05-13-11-1-7-scoped-e2e.md`

历史 API exploratory 报告仍可作为调试证据，但不等同 deterministic E2E：

- `../results/2026-05-08-replay-e2e-codex-exploratory.md`

## 下一批 E2E 候选项

当前 E2E 线优先做 keep-running 和小范围补强：

- Replay E2E keep-running。
- LearnedPath catalog deterministic E2E keep-running。
- Conversation API-request runtime E2E keep-running。
- Conversation CLI-driven E2E keep-running。
- Conversation 11.1.6 scoped task execution E2E keep-running。
- Conversation 11.1.7 scoped task result reporter E2E keep-running。
- External fixture manifest ingestion keep-running。

当前不纳入本 track：

- LearnedPath Catalog Agent-operated UI exploratory。
- Console operator Agent-operated UI exploratory。
- verify-scenario live smoke。
- M11.1 task-to-path E2E。

## 验证命令

常用命令：

```bash
pnpm run test:e2e
pnpm run test:e2e:headed
pnpm run test:e2e:ui
```

首次运行前：

```bash
pnpm run test:e2e:install
```

运行报告写入 `docs/testing/results/`，Playwright 原始输出保留在
`apps/e2e/test-results/` 和 `apps/e2e/playwright-report/`。
