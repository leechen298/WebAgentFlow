# 测试基础设施

本目录存放 WebAgentFlow 长期测试基础设施文档。

`docs/iterations/` 只保留里程碑施工文档，用来记录 M10/M11 等交付的
intent、plan、step 文档和 review。长期测试体系文档不放在
`docs/iterations/` 下。

## 当前测试线

WebAgentFlow 规划两条验证线：

- 确定性 E2E 回归：稳定的 Playwright Test 套件，用来覆盖已经交付的行为。
- Codex 探索式验证：后续阶段的工作流，由 Codex 基于产品/API contract 提出边界用例，
  并把稳定发现沉淀为长期 E2E 用例。

当前先实现确定性 E2E。Codex 探索式验证目前只保留方案文档。

E2E 套件不依赖 LLM 服务，不调用 `/exploration/autonomous-runs`，
不调用 `/exploration/autonomous-runs/stream`，也不创建 live autonomous run。

## 常用命令

```bash
pnpm run test:e2e
pnpm run test:e2e:headed
pnpm run test:e2e:ui
```

首次设置 E2E workspace 时安装 Playwright Test 浏览器：

```bash
pnpm run test:e2e:install
```

查看 [e2e.md](./e2e.md) 了解确定性 E2E 设计；
查看 [results/2026-05-08-replay-e2e-first-run.md](./results/2026-05-08-replay-e2e-first-run.md)
了解 M10.2 replay E2E 首次实跑结果；
查看 [codex-exploratory.md](./codex-exploratory.md) 了解后续探索式验证方案。

人类可读的测试运行摘要放在 `docs/testing/results/`。
Playwright 原始输出保留在 `apps/e2e/test-results/` 和
`apps/e2e/playwright-report/`，并由 gitignore 忽略。
