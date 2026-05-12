# E2E / Agent 可视化测试过渡索引

本文件保留为历史链接兼容入口。

它原来混合管理 deterministic E2E、API exploratory、visual UI exploratory、
Codex evidence report、Browser Use / Computer Use report 和 manual live smoke。
这个口径过宽，容易把自动化 E2E 和 Agent 可视化页面探索测试混在一起。

当前已拆分为两个主文档：

- `docs/testing/e2e/README.md` — Deterministic E2E Track。
- `docs/testing/agent-operated-ui/README.md` — Agent-operated UI Exploratory
  Testing。

后续新内容不要继续添加到本文件。

## 当前拆分

### Deterministic E2E / 确定性 E2E

由 `e2e/README.md` 管理。

- 使用 Playwright Test。
- 测试代码放在 `apps/e2e/tests/`。
- 可重复、可进入 CI。
- 不依赖 LLM provider。
- 不调用 `/exploration/autonomous-runs` 或 `/stream`。
- Headless E2E 可以作为 deterministic evidence，但不能冒充 visual UI
  exploratory。

### Agent-operated UI Exploratory / Agent 可视化页面探索

由 `agent-operated-ui/README.md` 管理。

- 由 Codex、Claude Code 或其他带浏览器/Computer Use 能力的 Agent 实际打开页面
  操作。
- 通常不写测试代码，主要产出用例、浏览器观察、截图/trace/video 或 equivalent
  evidence report。
- 不进常规 CI。
- API-only、component test、static selector smoke、headless E2E 都不能冒充这类
  可视化证据。

### API Exploratory / API 探索式验证

API exploratory 仍可在能力域文档或结果报告中记录，但它不是 E2E，也不是
Agent-operated UI exploratory。

### Manual Live Smoke / 手动 live smoke

`verify-scenario` live smoke 由 `docs/testing/live-smoke.md` 管理。

- release-only。
- 不进常规 CI。
- 需要 LLM provider 和 Supervisor verdict。
- 只能通过 `verify-scenario` skill 触发，不能直接 curl autonomous endpoints。

## 现有证据入口

E2E 报告：

- `docs/testing/results/2026-05-08-replay-e2e-first-run.md`
- `docs/testing/results/2026-05-11-replay-e2e-rerun.md`
- `docs/testing/results/2026-05-11-conversation-runtime-e2e.md`
- `docs/testing/results/2026-05-11-conversation-cli-e2e.md`

Agent-operated UI / visual evidence 报告：

- `docs/testing/results/2026-05-09-replay-visual-ui-exploratory.md`
- `docs/testing/results/2026-05-11-validation-site-browser-smoke.md`

Historical API exploratory report:

- `docs/testing/results/2026-05-08-replay-e2e-codex-exploratory.md`
