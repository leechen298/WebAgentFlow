# Replay Agent 可视化页面探索运行提示词

你正在为 WebAgentFlow M10.2 replay UI 运行 Agent-operated UI exploratory
validation。

本提示词只针对 replay 测试域，不是 WebAgentFlow 全项目测试。

## 硬规则

- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不 import 或直接运行 autonomous explorer。
- 不依赖 LLM provider。
- 不修改产品代码。
- 不修改 E2E spec。
- 不修改 package scripts。
- 不新增 `data-testid`。
- 不新增 Skill / Superpowers / MCP 配置。
- 不把 headless E2E 当成 Agent-operated UI exploratory PASS。
- 不把 API-only response 当成 Agent-operated UI exploratory PASS。
- 没有页面观察证据的 UI case 不能写 PASS。

## 证据要求

Agent-operated UI exploratory 必须使用以下任一方式：

- Codex Browser panel / in-app browser。
- Claude Code Browser Use / Computer Use。
- 其他具备浏览器操作能力的 Agent。
- Headed Playwright。

每个 PASS case 必须包含至少一种可追溯证据：

- 页面可见文本观察。
- 截图。
- trace。
- video。
- 明确的 browser observation 摘录。

Headless Playwright E2E 属于 deterministic E2E。curl / Python / Node API 调用
属于 API exploratory。它们都不能替代 Agent-operated UI exploratory。

## 前置检查

1. 确认 API health 可用。
2. 确认 console 可访问。
3. 确认外部 fixture provider 可访问。
4. 确认 `apps/e2e/.tmp/replay-fixtures.json` 存在且包含 8 个 replay fixtures。
5. 如果当前数据库没有 seeded LearnedPath，可从外部 Fixture-Site 仓库显式
   opt-in 运行 local-only seed helper：
   `python3 evals/seed-webagentflow-replay-fixtures.py --webagentflow-local-seed`。
   该 helper 不调用 autonomous run，也不依赖 LLM provider，但会写入本地 raw
   fixture context；它不是 provider redacted summary。

## 必跑 UI cases

在 console LearnedPath catalog 中逐个打开 drawer、填写目标 URL、点击 replay，并观察
页面可见结果。

| Case | Scenario | URL | PASS observation |
| --- | --- | --- | --- |
| UI-001 | `e2e:replay:happy` | empty | replay button disabled |
| UI-002 | `e2e:replay:happy` | `<fixture-provider>/records` | `成功` / `无变化` / final URL / `Step 0` |
| UI-OBS | `e2e:replay:observational` | `<fixture-provider>/records` | `这条路径没有动作，已完成页面观察` / `无变化` / `暂无步骤日志` |
| UI-PAGE-MISMATCH | `e2e:replay:page-mismatch` | `<fixture-provider>/entry` | `页面变化导致无法重跑` / `页面不匹配` |
| UI-004 | `e2e:replay:target-missing` | `<fixture-provider>/records` | `页面变化导致无法重跑` / `找不到当初记录的按钮或输入框` |
| UI-UNSUPPORTED | `e2e:replay:unsupported-action` | `<fixture-provider>/records` | `这类动作当前还不能重跑` |
| UI-003 | `e2e:replay:flaky` | `<fixture-provider>/records` | `成功` / `Path trust is flaky` |
| UI-005 | `e2e:replay:deprecated` | `<fixture-provider>/records` | `重跑失败` / `learned_path is deprecated` |
| UI-SIGNATURE | `e2e:replay:signature-changed` | `<fixture-provider>/records` | `成功` / `签名已变化` |

## 报告要求

报告写入：

```text
docs/testing/results/YYYY-MM-DD-replay-visual-ui-exploratory.md
```

报告必须包含：

- 日期。
- 当前 commit。
- 工作区状态摘录。
- 前置检查结果。
- seed 结果。
- 每个 UI case 的操作方法和页面观察证据。
- PASS / FAIL / BLOCKED / NOT_RUN 统计。
- 是否调用 autonomous endpoints。
- 是否使用 LLM provider。
- `git diff --check` 结果。

如果某个 case 没跑，写 `NOT_RUN`。如果环境阻塞，写 `BLOCKED`。不得用
headless E2E 或 API-only 结果补写 Agent-operated UI PASS。
