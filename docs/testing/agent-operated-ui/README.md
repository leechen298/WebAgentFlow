# Agent 可视化页面探索测试

## 范围

本文件管理由 Agent 实际打开页面、点击、输入、观察的可视化 UI 探索测试。

可执行工具包括：

- Codex Browser panel / in-app browser。
- Claude Code Browser Use / Computer Use。
- 其他具备浏览器操作能力的 Agent。
- Headed Playwright，仅当它作为可视化观察工具使用时。

本 track 的重点是：

- 明确用例。
- 打开真实页面。
- 实际点击、输入、观察。
- 记录浏览器观察、截图、trace、video 或 equivalent visible evidence。
- 记录原始操作步骤：打开了哪个页面、点击了哪个按钮、输入了什么、观察到什么。
- 产出人工可读报告。

这不是 deterministic E2E，不进常规 CI，也不替代 Playwright Test。

## 命名

这类测试不再称为 “Codex 自主操作页面测试”。

推荐名称：

- English: Agent-operated UI Exploratory。
- 中文：Agent 可视化页面探索测试。

Codex 只是可选执行工具之一。Claude Code 或其他带 Browser Use / Computer Use 能力的
Agent 也可以按同一份用例和报告模板执行。

## 规则

- 没有实际浏览器观察，不得写 PASS。
- API-only 结果不能算 Agent-operated UI exploratory。
- 没有原始 UI 操作记录，不能算 Agent-operated UI exploratory。
- Headless E2E 不能算 Agent-operated UI exploratory。
- Component test 不能算 Agent-operated UI exploratory。
- Static selector smoke 不能算 Agent-operated UI exploratory。
- 默认 exploratory 用例不点击会触发 live autonomous run 的按钮。
- 如果用例明确标为 Live UI Smoke，则允许通过产品自己的 Console UI 点击
  `Run` / `Run selected` 等控件；报告必须把
  `/exploration/autonomous-runs[/stream]` 记录为 product-initiated UI traffic。
- 不用 curl、fetch、httpx 或自写脚本直接调用 `/exploration/autonomous-runs`。
- 不用 curl、fetch、httpx 或自写脚本直接调用 `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 如果工具无法打开页面，写 `BLOCKED`。
- 报告必须写明 tool：Codex、Claude Code、headed Playwright 或其他具体工具。
- 报告必须写明 operator action log：页面、控件、点击 / 输入 / 等待 / 观察顺序。
- 报告必须写明是否调用 autonomous endpoint，默认应为 `no`。
- 报告必须写明是否触发 WebAgentFlow 产品侧 LLM provider，默认应为 `no`。
- 当前最新一份 Agent-operated UI 报告必须同步到稳定 latest 路径，方便 commit /
  push 后由 ChatGPT 或其他 Agent 复核；带日期报告可作为历史归档。
- Codex、Claude Code 或其他 browser-capable Agent 可以作为外部测试操作员；
  禁止的是伪装成 WebAgentFlow 内部 Agent、绕过产品 UI 直接调内部服务、
  或编造产品没有实际返回的结果。

## 用例模板

每个用例必须包含：

- case id。
- target URL。
- goal。
- preconditions。
- actions。
- expected visible result。
- forbidden actions。
- evidence requirement。
- report path。

示例：

```text
Case ID:
Target URL:
Goal:
前置条件：
Actions:
Expected visible result:
Forbidden actions:
Evidence requirement:
Report path:
Latest report path:
```

## 当前用例组

### AUI-01 · LearnedPath Catalog 可视化页面探索

用例文件：

```text
docs/testing/agent-operated-ui/cases/learned-path-catalog-visual-ui.md
```

目标：

- 打开 `/exploration/learned-paths`。
- 验证 list / empty state。
- 验证 trust filter。
- 打开 drawer。
- 检查 replay section。
- 不触发 autonomous run。

推荐报告路径：

```text
docs/testing/results/YYYY-MM-DD-catalog-visual-ui-exploratory.md
docs/testing/results/agent-operated-ui-latest.md
```

### AUI-02 · Console Operator 可视化页面探索

用例文件：

```text
docs/testing/agent-operated-ui/cases/console-operator-visual-ui.md
```

目标：

- 打开 history。
- 打开 detail。
- 打开 workbench。
- 打开 use cases。
- 默认 non-live exploratory 模式只观察，不点击 run / batch run / run selected。
- Live UI Smoke 模式可以点击 `Run` / `Run selected`，但必须如实记录
  autonomous endpoint、产品侧 LLM / Supervisor、run status 和 run id。

推荐报告路径：

```text
docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md
docs/testing/results/YYYY-MM-DD-console-operator-live-ui-smoke.md
docs/testing/results/agent-operated-ui-latest.md
```

### AUI-03 · External fixture provider 浏览器冒烟

外部 fixture provider 的页面级浏览器冒烟不保留在 WebAgentFlow 仓库。
WebAgentFlow 只消费 provider 输出的 redacted result summary 或 replay fixture
manifest。

## 报告模板

```md
# <Feature> Agent 可视化页面探索报告

日期：
Commit:
工作区：
工具：
目标 URL：

## 前置条件

## 用例结果

| 用例 | 状态 | 证据 |
| --- | --- | --- |

## 操作步骤与观察

## Operator Action Log

| Step | Surface | Action | Target | Value / Observation |
| ---: | --- | --- | --- | --- |

## 边界

- Autonomous endpoints called:
- `/exploration/autonomous-runs` called:
- `/exploration/autonomous-runs/stream` called:
- 产品侧 LLM provider used:
- Product code modified:
- E2E spec modified:

## 后续
```

## 执行提示词模板

```text
请执行 Agent-operated UI Exploratory。

范围：
- 只操作已完成页面。
- 默认不调用 `/exploration/autonomous-runs`。
- 默认不调用 `/exploration/autonomous-runs/stream`。
- 默认不触发 live autonomous run。
- 默认不触发 WebAgentFlow 产品侧 LLM provider。
- 如果任务明确要求 Live UI Smoke，可以通过产品 Console UI 触发 live run，
  但不得直接 curl/fetch/httpx 调 endpoint，也不得伪装成内部 Agent。
- Codex / Claude Code / 其他 browser-capable Agent 可作为外部测试操作员。

目标页面：
- <target urls>

请执行：
1. 打开目标页面。
2. 记录当前 URL、页面标题或主要可见标题。
3. 按任务说明点击/输入/观察。
4. 记录可见 UI 证据。
5. 如果页面或服务不可用，标记 BLOCKED，不要改产品代码。

输出报告：
- PASS / FAIL / BLOCKED summary。
- 每一步操作和可见观察。
- 使用的工具。
- 是否调用 autonomous endpoint。
- 是否触发产品侧 LLM provider。
```
