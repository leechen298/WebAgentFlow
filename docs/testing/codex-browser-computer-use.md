# Codex Browser / Computer Use 测试规程

本文件定义 Codex 如何使用 Browser Use 或 Computer Use 自己操作网页，产出
WebAgentFlow 的可视化测试证据。

它只覆盖已经完成的功能，不推进新产品功能，不替代 deterministic E2E，也不触发
live autonomous run。

## 适用范围

优先使用 Browser Use：

- 打开 localhost / 127.0.0.1 上的 console、validation-site、API docs。
- 点击页面、填写表单、观察可见 UI、记录页面状态。
- 产出 visual UI exploratory 报告。

谨慎使用 Computer Use：

- Browser Use 无法覆盖的桌面级浏览器操作。
- 需要确认系统级权限弹窗、浏览器窗口状态或桌面交互。
- 不得用 Computer Use 绕过本仓库的 autonomous run 边界。

不适用：

- 普通 unit / repo / API / component baseline。
- CLI mocked tests。
- `verify-scenario` live smoke；它只能按 `live-smoke.md` 的 release-only 规程执行。

## 硬边界

- 不直接调用 `/exploration/autonomous-runs`。
- 不直接调用 `/exploration/autonomous-runs/stream`。
- 不 import / run autonomous explorer。
- 不依赖 LLM provider。
- 不把 Browser Use / Computer Use 的可视化探索写成 CI-safe deterministic E2E。
- 不把 API-only 结果冒充 visual UI exploratory。
- 不把 component test 结果冒充浏览器 E2E。
- 不在 Workbench / Use Cases 页面点击会触发 live autonomous run 的按钮。

## 前置检查

执行可视化测试前，必须确认目标服务已启动：

```bash
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5174/
curl -sS -I http://127.0.0.1:5175/
```

如果服务未启动，报告写 `BLOCKED`，不要改产品代码来迁就测试环境。

## 证据要求

每次 Browser Use / Computer Use 测试报告必须包含：

- Date。
- Commit：`git rev-parse HEAD`。
- Working tree：`git status --short`。
- Tool：Browser Use 或 Computer Use。
- Target URLs。
- 操作步骤。
- 可见页面观察。
- PASS / FAIL / BLOCKED / NOT_RUN summary。
- 是否调用 autonomous endpoint：必须明确写 `no`，除非是 release-only
  `verify-scenario` live smoke。
- 是否依赖 LLM provider：必须明确写 `no`，除非是 release-only live smoke。
- 截图、trace、video 或 Browser observation 摘录；至少要有一种可见 UI 证据。

没有真实页面观察，不能写 PASS。

## 现有功能可视化测试任务

### CBU-01 · LearnedPath Catalog Visual UI Exploratory

- Target:
  `http://127.0.0.1:5174/exploration/learned-paths`
- Goal: 验证 catalog 列表、trust filter、drawer、replay 区块可见且主流程不破。
- Actions:
  1. 打开 LearnedPath catalog。
  2. 确认列表或 empty state 可见。
  3. 使用 trust filter 切换至少一个状态。
  4. 打开一条 LearnedPath drawer。
  5. 检查 replay 区块存在。
  6. 如果使用 seeded replay path，只能调用 replay API，不得触发 autonomous run。
- Not doing:
  不做 live autonomous learning；不调用 `/exploration/autonomous-runs`。
- Report:
  `docs/testing/results/YYYY-MM-DD-catalog-visual-ui-exploratory.md`

### CBU-02 · Console Operator Visual UI Exploratory

- Targets:
  - `http://127.0.0.1:5174/exploration/autonomous/history`
  - `http://127.0.0.1:5174/exploration/autonomous`
  - `http://127.0.0.1:5174/exploration/autonomous/cases`
- Goal: 验证 operator 主入口可见，不触发 live run。
- Actions:
  1. 打开 history 页面，确认列表、empty state 或错误状态可见。
  2. 打开 workbench 页面，确认 URL / goal / scenario / headless 配置区域可见。
  3. 打开 use cases 页面，确认 specs/scenarios 表格或 empty state 可见。
  4. 如页面有运行按钮，只检查 disabled/enabled state，不点击触发 live run。
- Not doing:
  不运行自主探索；不点击 batch run / run selected / run 按钮。
- Report:
  `docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md`

### CBU-03 · Validation-site Browser Smoke

- Targets:
  - `http://127.0.0.1:5175/login`
  - `http://127.0.0.1:5175/users`
- Goal: 用真实浏览器确认 fixture 页面关键元素可见。
- Actions:
  1. 打开 `/login`。
  2. 确认 username、password、submit button 可见。
  3. 可选：输入错误凭据，确认错误提示容器可见。
  4. 打开 `/users`。
  5. 确认 search-name、search-status、search button、table 或 empty state 可见。
- Not doing:
  不做全页面交互穷举；不调用 autonomous run。
- Report:
  `docs/testing/results/YYYY-MM-DD-validation-site-browser-smoke.md`

## Browser Use Prompt 模板

```text
请使用 Browser Use 对 WebAgentFlow 做 visual UI exploratory。

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
- 是否调用 autonomous endpoint：no。
- 是否依赖 LLM provider：no。
```

## Computer Use Prompt 模板

```text
请使用 Computer Use 做桌面级可视化确认。

只在 Browser Use 无法完成时使用。

硬边界：
- 不打开或触发 live autonomous run。
- 不直接调用 autonomous endpoint。
- 不修改产品代码。
- 不把桌面观察写成 deterministic E2E。

目标：
- <desktop/browser target>

请记录：
- 使用的应用和窗口。
- 可见页面或系统状态。
- 操作步骤。
- 截图或明确 visual observation。
- PASS / FAIL / BLOCKED。
```

## 报告模板

```md
# <Feature> Visual UI Exploratory

Date:
Commit:
Working tree:
Tool:
Target URLs:

## Scope

## Preconditions

## Steps And Observations

## Result Summary

| Case | Status | Evidence |
| --- | --- | --- |

## Boundaries

- Autonomous endpoints called: no
- LLM provider used: no
- Live autonomous run triggered: no

## Follow-ups
```
