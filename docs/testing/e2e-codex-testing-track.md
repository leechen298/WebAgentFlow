# E2E & Codex Testing Track

## Scope

本文件专门管理 WebAgentFlow 的 E2E 与 Codex 证据型测试路线。

当前目标不是补全所有测试层级，而是：

- 给现有已完成功能补真实 deterministic E2E。
- 让 Codex 使用 Browser Use / Computer Use 自己操作网页，形成 visual UI
  exploratory 证据。
- 把这些证据和普通 unit / repo / API / component baseline 分开。

它覆盖：

- deterministic E2E。
- API exploratory。
- visual UI exploratory。
- Codex evidence report。
- Browser Use / Computer Use 自主网页操作报告。
- release-only manual live smoke。

它不管理普通 unit、repo-only、component-only、CLI mocked unit tests，也不替代
已有 baseline backlog。

文档分工：

- `full-test-matrix.md` 是全测试地图，覆盖 unit / repo / API / component /
  E2E / exploratory / live smoke 等所有层级。
- `current-testing-backlog.md` 是已完成功能的测试补全 backlog，会混合
  unit、API、CLI、component 和 E2E。
- `codex-browser-computer-use.md` 是 Codex 使用 Browser Use / Computer Use
  自己操作网页的测试规程。
- 本文件是 E2E / Codex 专项路线图，只讨论需要真实 E2E、浏览器观察、API
  exploratory 证据或 manual live smoke 证据的任务。

## Evidence Types Included

| Evidence type | Included | 说明 |
| --- | --- | --- |
| Deterministic E2E | yes | Playwright Test，对稳定 seed 和固定服务栈做可重复回归 |
| API exploratory | yes | 直接调用 API，保留命令、退出码、响应摘录和边界判断 |
| Visual UI exploratory | yes | Codex Browser panel / in-app browser / headed Playwright 的可见页面操作证据 |
| Codex evidence report | yes | Codex 产出的人工可读证据报告，必须引用真实命令或浏览器观察 |
| Browser Use / Computer Use report | yes | Codex 自己操作网页或桌面浏览器后产出的可见证据报告 |
| Manual live smoke | yes | 只能通过 `verify-scenario` skill 触发，release-only，不进常规 CI |
| Unit | no | 属于 full matrix / feature backlog |
| Repo-only | no | 属于 full matrix / feature backlog |
| Component-only | no | 属于 full matrix / feature backlog |
| CLI mocked unit tests | no | 属于 full matrix / feature backlog |

## Current Evidence

### Replay

现有证据：

- Deterministic E2E 已存在：`apps/e2e/tests/replay/`。
- 首次实跑报告：
  `docs/testing/results/2026-05-08-replay-e2e-first-run.md`。
- Codex API exploratory 报告：
  `docs/testing/results/2026-05-08-replay-e2e-codex-exploratory.md`。
- Visual UI exploratory 报告：
  `docs/testing/results/2026-05-09-replay-visual-ui-exploratory.md`。
- Fresh rerun 报告：
  `docs/testing/results/2026-05-11-replay-e2e-rerun.md`。

当前状态：

- Q1 baseline 曾记录 replay E2E `9/9 passed`。
- 2026-05-11 rerun 在默认 sandbox 下曾因 localhost / Chromium permission
  BLOCKED，但 non-sandbox rerun `9 passed`。
- 11.0.7 conversation runtime E2E 加入后，full deterministic E2E 报告记录
  `10 passed`。

### Conversation

现有证据：

- API-level runtime E2E 已存在：
  `apps/e2e/tests/conversation/runtime.spec.ts`。
- CLI-driven runtime E2E 已存在：
  `apps/e2e/tests/conversation/cli-runtime.spec.ts`。
- 结果报告：
  `docs/testing/results/2026-05-11-conversation-runtime-e2e.md`。
- CLI-driven 结果报告：
  `docs/testing/results/2026-05-11-conversation-cli-e2e.md`。

当前 runtime E2E 覆盖：

```text
POST /conversation/sessions
-> POST /conversation/sessions/{session_id}/dispatch
-> explicit /replay <learned_path_id> <url>
-> M10 replay hook
-> transcript/events
```

重要边界：

- `runtime.spec.ts` 是 API-request E2E。
- `cli-runtime.spec.ts` 是真实 `wagent conversation` subprocess 打真实 API 的
  CLI-driven E2E。
- `apps/cli/tests/test_conversation.py` 仍是 mocked `httpx` CLI tests，用于
  CLI unit/integration baseline，不等同 E2E。
- 两条 conversation E2E 都不调用 autonomous run，不依赖 LLM provider。

### Console / Catalog / Validation-site

现有证据：

- Console component smoke 已存在，但 component smoke 不是 visual UI
  exploratory。
- Validation-site selector stability smoke 已存在，但它读取源文件做静态 selector
  guard，不是浏览器 E2E。
- Replay visual UI exploratory 已覆盖 LearnedPath catalog 的 replay drawer
  主要路径。

当前缺口：

- LearnedPath catalog trust/filter/drawer/replay 区块还没有独立的最新 visual UI
  exploratory 报告。
- Console operator history/detail/workbench/use-cases 还没有专项 visual UI
  exploratory 报告。
- Validation-site `/login`、`/users` 还没有最小浏览器 smoke 报告。

### Autonomous Exploration

当前状态：

- 本 track 不把 live autonomous run 纳入 deterministic E2E。
- `verify-scenario` live smoke 只能作为 release-only manual live smoke。
- `docs/testing/live-smoke.md` 已有 runbook；真正执行时才新增
  `docs/testing/results/YYYY-MM-DD-verify-scenario-live-smoke.md`。

## Gaps

| ID | Gap | Current status | Notes |
| --- | --- | --- | --- |
| ECT-GAP-01 | CLI-driven conversation E2E | existing / keep-running | 已有真实 `wagent conversation` subprocess 打真实 API |
| ECT-GAP-02 | LearnedPath catalog visual UI exploratory | gap | replay drawer 做过，catalog trust/filter 仍缺专项视觉证据 |
| ECT-GAP-03 | Console operator visual UI exploratory | gap | component smoke 已有，visual UI 证据仍缺 |
| ECT-GAP-04 | Validation-site browser smoke | gap | static selector smoke 已有，浏览器可见 fixture smoke 仍缺 |
| ECT-GAP-05 | verify-scenario live smoke execution | deferred | runbook 已有，实际执行只在 release/manual 触发 |
| ECT-GAP-06 | Replay E2E fresh evidence upkeep | keep-running | 最新报告已有 fresh evidence，后续持续复跑 |

## Next E2E / Codex Batch

### ECT-01 · Replay E2E Fresh Rerun Evidence

- Goal: 持续复跑 replay + conversation deterministic E2E，确认 fresh PASS 或记录
  环境 BLOCKED。
- Scope: `pnpm run test:e2e` 结果报告和必要 health check 证据。
- Not doing: 不改 E2E spec，不改产品代码，不调用 autonomous run。
- Evidence type: Deterministic E2E。
- CI-safe: yes，前提是服务编排和浏览器权限稳定。
- LLM: no。
- Autonomous run: no。
- Report path:
  `docs/testing/results/YYYY-MM-DD-e2e-rerun.md`。

### ECT-02 · Conversation CLI-driven E2E

- Goal: 持续运行真实 `wagent conversation` 命令驱动的 session / send /
  transcript / events E2E。
- Scope: `apps/e2e/tests/conversation/cli-runtime.spec.ts` 和结果报告。
- Not doing: 不做 M11.1 task-to-path，不做 path selection，不调用 autonomous run。
- Evidence type: Deterministic E2E。
- CI-safe: yes，前提是服务和 CLI 环境可编排。
- LLM: no。
- Autonomous run: no。
- Report path:
  `docs/testing/results/YYYY-MM-DD-conversation-cli-e2e.md`。

### ECT-03 · LearnedPath Catalog Visual UI Exploratory

- Goal: 使用 Codex Browser panel / headed browser 打开 catalog，验证 trust /
  filter / drawer / replay 区块的可见 UI 行为。
- Scope: 只写 visual UI exploratory 结果报告，必要时记录截图、trace 或可见
  observation。
- Not doing: 不改产品代码，不新增 deterministic E2E，不调用 autonomous run。
- Evidence type: Visual UI exploratory。
- CI-safe: no。
- LLM: no。
- Autonomous run: no。
- Report path:
  `docs/testing/results/YYYY-MM-DD-catalog-visual-ui-exploratory.md`。

### ECT-04 · Console Operator Visual UI Exploratory

- Goal: 可视化打开 history / detail / workbench / use-cases，验证主入口不破，
  且不触发 live run。
- Scope: 重点页面抽样，不做全页面穷举。
- Not doing: 不触发 autonomous run，不把 visual UI exploratory 写成 headless E2E。
- Evidence type: Visual UI exploratory。
- CI-safe: no。
- LLM: no。
- Autonomous run: no。
- Report path:
  `docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md`。

### ECT-05 · Validation-site Browser Smoke

- Goal: 用浏览器实际打开 `/login`、`/users`，确认关键 fixture 可见和基础交互
  可执行。
- Scope: 可选择 deterministic Playwright smoke 或 visual report；先做最小页面。
- Not doing: 不做 validation-site 全页面 E2E，不测试所有控件，不调用 autonomous run。
- Evidence type: Deterministic E2E or Visual UI exploratory，取决于实现方式。
- CI-safe: deterministic version yes；visual report no。
- LLM: no。
- Autonomous run: no。
- Report path:
  `docs/testing/results/YYYY-MM-DD-validation-site-browser-smoke.md`。

### ECT-06 · verify-scenario Release Smoke

- Goal: 保持 release-only live smoke 规程；只有 release/manual 场景才执行。
- Scope: `docs/testing/live-smoke.md` 已有 runbook；真正执行时新增结果报告。
- Not doing: 不自动执行 live run，不进常规 CI，不直接 curl autonomous endpoints。
- Evidence type: Manual live smoke。
- CI-safe: no。
- LLM: yes。
- Autonomous run: 只能通过 `verify-scenario` skill。
- Report path:
  `docs/testing/results/YYYY-MM-DD-verify-scenario-live-smoke.md`。

## Rules

- Headless E2E does not count as visual UI exploratory。
- API-only evidence does not count as visual UI exploratory。
- Component tests do not count as browser E2E。
- Static selector smoke does not count as browser E2E。
- Live smoke cannot be CI deterministic E2E。
- Codex cannot claim PASS without evidence: command, exit code, stdout/stderr
  excerpt, browser observation, screenshot, trace, or report.
- Browser panel / headed Playwright evidence is required for visual UI
  exploratory。
- `verify-scenario` is the only permitted live autonomous path。
- Direct calls to `/exploration/autonomous-runs` or
  `/exploration/autonomous-runs/stream` are not allowed。
