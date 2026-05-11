# 测试基础设施

本目录存放 WebAgentFlow 长期测试基础设施文档。

`docs/iterations/` 只保留里程碑施工文档，用来记录 M10/M11 等交付的
intent、plan、step 文档和 review。长期测试体系文档不放在
`docs/iterations/` 下。

## 当前测试线与测试域

WebAgentFlow 规划两条验证线：

- 确定性 E2E 回归：稳定的 Playwright Test 套件，用来覆盖已经交付的行为。
- Codex 探索式验证：按产品能力域执行，由 Codex 基于产品/API contract 提出边界用例，
  并把稳定发现沉淀为长期测试用例。

当前已建立的测试域包括 M10.2 replay 和 M11 conversation。后续核心产品能力域可以继续在
`docs/testing/features/` 下建立自己的测试矩阵，例如
task-execution、recovery、teaching、multi-page-workflow。不是每个小功能都需要
完整 E2E；小功能应归入所属能力域，只有跨模块、用户可见、真实浏览器链路等核心
行为才需要 E2E 或探索式验证。

- `replay`：已有 deterministic E2E、API exploratory 和 visual UI exploratory
  证据，用于保护 M10.2 LearnedPath replay execution + drift detection。
- `conversation`：已有 domain / repo / API / CLI 覆盖，用于保护 M11 runtime
  conversation 基础；11.0.5 Orchestrator Dispatcher、11.0.6 Explicit Replay
  Command Hook 和 11.0.7 conversation runtime E2E 已有证据。

Codex exploratory validation 也按能力域执行，不做一次性全项目自动测试。新增探索式
用例必须先明确所属能力域、证据类型、是否 CI-safe，以及是否依赖当前里程碑。

测试规划文档分三层：

- [full-test-matrix.md](./full-test-matrix.md)：全测试地图，覆盖 unit /
  repo / API / component / E2E / exploratory / live smoke 等所有层级，不是一次性
  施工清单。
- [current-testing-backlog.md](./current-testing-backlog.md)：已完成功能的测试
  补全 backlog，可包含普通 API、CLI、component baseline。
- [e2e-codex-testing-track.md](./e2e-codex-testing-track.md)：只管理
  deterministic E2E、API exploratory、visual UI exploratory、Codex evidence
  report 和 release-only manual live smoke。
- [codex-browser-computer-use.md](./codex-browser-computer-use.md)：定义 Codex
  使用 Browser Use / Computer Use 自己操作网页并产出 visual UI evidence 的测试规程。

E2E 套件不依赖 LLM 服务，不调用 `/exploration/autonomous-runs`，
不调用 `/exploration/autonomous-runs/stream`，也不创建 live autonomous run。

## 证据类型

- Deterministic E2E：Playwright Test 自动化，通常是 headless。它是适合 CI
  和稳定回归的证据。
- API exploratory：使用 curl、Python、Node 等直接调用 API，并保留命令、退出码
  和原始响应摘录。
- Visual UI exploratory：使用 Codex Browser panel / in-app browser，或 headed
  Playwright 打开真实页面，执行可见 UI 操作，并记录页面观察、截图、trace、video
  或明确的 browser observation 证据。

Headless E2E 不能算 visual UI exploratory。API-only 调用也不能算 visual UI
exploratory。报告必须清楚写明采用的是哪一种证据类型。

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

查看 [full-test-matrix.md](./full-test-matrix.md) 了解全量测试地图；
查看 [e2e-codex-testing-track.md](./e2e-codex-testing-track.md) 了解 E2E /
Codex 专项路线图；
查看 [codex-browser-computer-use.md](./codex-browser-computer-use.md) 了解 Codex
自主网页操作测试规程；
查看 [e2e.md](./e2e.md) 了解确定性 E2E 设计；
查看 [features/replay.md](./features/replay.md) 了解 M10.2 replay 测试域；
查看 [features/conversation.md](./features/conversation.md) 了解 M11 conversation 测试域；
查看 [exploratory/README.md](./exploratory/README.md) 了解 replay 探索式验证提示词和用例矩阵；
查看 [results/2026-05-08-replay-e2e-first-run.md](./results/2026-05-08-replay-e2e-first-run.md)
了解 M10.2 replay E2E 首次实跑结果；
查看 [results/2026-05-09-replay-visual-ui-exploratory.md](./results/2026-05-09-replay-visual-ui-exploratory.md)
了解 M10.2 replay 右侧浏览器可视化点击验证结果；
查看 [results/2026-05-11-conversation-baseline.md](./results/2026-05-11-conversation-baseline.md)
和 [results/2026-05-11-conversation-runtime-e2e.md](./results/2026-05-11-conversation-runtime-e2e.md)
以及 [results/2026-05-11-conversation-cli-e2e.md](./results/2026-05-11-conversation-cli-e2e.md)
了解 M11 conversation baseline、API-request runtime E2E 和 CLI-driven E2E 证据；
查看 [live-smoke.md](./live-smoke.md) 了解 release-only manual live smoke 规则；
查看 [codex-exploratory.md](./codex-exploratory.md) 了解后续探索式验证方案。
查看 [current-testing-backlog.md](./current-testing-backlog.md) 了解当前测试补全计划和状态。

人类可读的测试运行摘要放在 `docs/testing/results/`。
Playwright 原始输出保留在 `apps/e2e/test-results/` 和
`apps/e2e/playwright-report/`，并由 gitignore 忽略。
