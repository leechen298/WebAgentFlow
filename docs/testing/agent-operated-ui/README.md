# Agent-operated UI Exploratory Testing

## Scope

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
- 产出人工可读报告。

这不是 deterministic E2E，不进常规 CI，也不替代 Playwright Test。

## Naming

这类测试不再称为 “Codex 自主操作页面测试”。

推荐名称：

- English: Agent-operated UI Exploratory。
- 中文：Agent 可视化页面探索测试。

Codex 只是可选执行工具之一。Claude Code 或其他带 Browser Use / Computer Use 能力的
Agent 也可以按同一份用例和报告模板执行。

## Rules

- 没有实际浏览器观察，不得写 PASS。
- API-only 结果不能算 Agent-operated UI exploratory。
- Headless E2E 不能算 Agent-operated UI exploratory。
- Component test 不能算 Agent-operated UI exploratory。
- Static selector smoke 不能算 Agent-operated UI exploratory。
- 不点击会触发 live autonomous run 的按钮。
- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 如果工具无法打开页面，写 `BLOCKED`。
- 报告必须写明 tool：Codex、Claude Code、headed Playwright 或其他具体工具。
- 报告必须写明是否调用 autonomous endpoint，默认应为 `no`。
- 报告必须写明是否依赖 LLM provider，默认应为 `no`。

## Case Template

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
Preconditions:
Actions:
Expected visible result:
Forbidden actions:
Evidence requirement:
Report path:
```

## Current Case Groups

### AUI-01 · LearnedPath Catalog Visual UI

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
```

### AUI-02 · Console Operator Visual UI

目标：

- 打开 history。
- 打开 detail。
- 打开 workbench。
- 打开 use cases。
- 不点击 run / batch run / run selected 等 live run 按钮。

推荐报告路径：

```text
docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md
```

### AUI-03 · Validation-site Browser Smoke

目标：

- 打开 `/login`。
- 打开 `/users`。
- 确认关键控件可见。
- 执行基础搜索 / 错误提示可见性验证。

已记录报告：

```text
docs/testing/results/2026-05-11-validation-site-browser-smoke.md
```

## Report Template

```md
# <Feature> Agent-operated UI Exploratory Report

Date:
Commit:
Working tree:
Tool:
Target URLs:

## Preconditions

## Case Results

| Case | Status | Evidence |
| --- | --- | --- |

## Steps And Observations

## Boundaries

- Autonomous endpoints called:
- `/exploration/autonomous-runs` called:
- `/exploration/autonomous-runs/stream` called:
- LLM provider used:
- Product code modified:
- E2E spec modified:

## Follow-ups
```

## Execution Prompt Template

```text
请执行 Agent-operated UI Exploratory。

范围：
- 只操作已完成页面。
- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不触发 live autonomous run。
- 不依赖 LLM provider。

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
- 是否调用 autonomous endpoint：no。
- 是否依赖 LLM provider：no。
```
