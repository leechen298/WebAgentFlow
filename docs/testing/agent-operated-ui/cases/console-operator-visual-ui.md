# AUI-02 · Console Operator 可视化页面探索

## 目标

使用 Agent 操作真实浏览器，验证 console operator 核心页面在不启动 live autonomous
run 的前提下仍然可导航、可观察。覆盖 history、detail、workbench、use cases 四类
operator surface。

这是 **Agent-operated UI exploratory** 证据，不是 deterministic E2E、
API-only exploratory、component test，也不是 live autonomous run。

## 范围

目标页面来自当前 console router：

- `http://127.0.0.1:5174/exploration/autonomous/history`
- `http://127.0.0.1:5174/exploration/autonomous/history/<run_id>`
- `http://127.0.0.1:5174/exploration/autonomous`
- `http://127.0.0.1:5174/exploration/autonomous/cases`

主要证据报告路径：

- `docs/testing/results/YYYY-MM-DD-console-operator-visual-ui-exploratory.md`

如果没有 persisted run，detail 页面用例可以写 `BLOCKED`。不要为了制造 detail 数据而触发 live run。

## 目标页面

| 区域 | URL |
| --- | --- |
| Run history | `http://127.0.0.1:5174/exploration/autonomous/history` |
| Run detail | `http://127.0.0.1:5174/exploration/autonomous/history/<run_id>` |
| Workbench | `http://127.0.0.1:5174/exploration/autonomous` |
| Use cases | `http://127.0.0.1:5174/exploration/autonomous/cases` |

## 前置条件

执行浏览器操作前，记录：

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5174/exploration/autonomous/history
curl -sS -I http://127.0.0.1:5174/exploration/autonomous
curl -sS -I http://127.0.0.1:5174/exploration/autonomous/cases
```

detail 页面数据前置：

- 优先从 history 页面点击可见 row 的 `View` 进入 detail。
- 如果 history 没有任何 row，`COV-002` 写 `BLOCKED`，并记录 history empty state。
- 不触发新 run 来创建数据。

如果 console 或 API 不可访问，相关用例写 `BLOCKED`。不能用 curl、源码阅读、component test 或 headless E2E 输出替代浏览器可视化证据。

## 允许工具

- Codex Browser panel / in-app browser。
- Claude Code Browser Use / Computer Use。
- 其他具备浏览器操作能力的 Agent。
- Headed Playwright，仅当它作为可视化观察工具使用时。

## 禁止动作

- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不 import 或直接运行 autonomous explorer。
- 不使用 `verify-scenario`。
- 不触发 WebAgentFlow 产品侧 LLM provider。
- Codex / Claude Code / 其他 browser-capable Agent 可作为外部测试操作员。
- 不点击 workbench `Run`。
- 不点击 workbench `Abort`，除非测试前已经有 run 处于运行中且 operator 明确要求介入。
- 不点击 use-cases `Run selected`。
- `Run in Workbench` 当前只是带 query params 跳转到 workbench，不会直接启动 run；
  但本轮仍将它视为 out of scope，不点击。后续可单独补 deep-link visual case。
- 不点击 history/detail 上的删除、accept review、reject review 等破坏性或状态变更操作。
- 不改产品代码、E2E spec、package scripts 或 `docs/iterations/`。
- 没有真实浏览器可见证据时，不得写 PASS。

## 用例

### COV-001 · History 页面渲染关键控件或 empty state

目标 URL：

```text
http://127.0.0.1:5174/exploration/autonomous/history
```

操作：

1. 打开 history 页面。
2. 记录当前 URL、页面标题或主要可见标题。
3. 确认 history page shell 可见。
4. 如果存在 refresh 和 workbench navigation 控件，确认它们可见。
5. 观察 run table/list 是否可见，或 empty state 是否可见。

预期可见结果：

- history 页面正常渲染。
- run table/list 可见，或明确 empty state 可见。
- 没有触发 live autonomous run。

证据要求：

- browser method。
- page URL。
- visible title 或 card title。
- table/list 或 empty-state 可见观察。
- screenshot、trace、video 或 browser observation excerpt 之一。

### COV-002 · Detail 页面渲染选中项详情，或因缺少 seed data 标记 blocked

目标 URL：

```text
http://127.0.0.1:5174/exploration/autonomous/history/<run_id>
```

操作：

1. 打开 history 页面。
2. 如果存在可见 row，只点击安全的 detail navigation 操作，例如 `View`。
3. 记录进入后的 detail URL。
4. 观察 detail 页面区块。
5. 如果没有 row，本用例写 `BLOCKED` 并记录 history empty state。

预期可见结果：

- 有 run 数据时，detail 页面显示 run configuration、status/verdict、result 或 raw JSON 区块，以及可能存在的 LearnedPath relation block。
- 没有 run 数据时，case 是 `BLOCKED`，不是 fail。
- 不创建新 run。

证据要求：

- history row 或 empty state 的浏览器观察。
- 有数据时，detail URL 和 detail sections 的浏览器观察。
- screenshot、trace、video 或 browser observation excerpt 之一。

### COV-003 · Workbench 页面渲染表单和配置区域

目标 URL：

```text
http://127.0.0.1:5174/exploration/autonomous
```

操作：

1. 打开 workbench 页面。
2. 观察 run configuration card。
3. 确认 URL input 和 goal input 可见。
4. 确认 fill-values 和 toggle-values 区域可见。
5. 如果初始 shell 中存在 live status / analysis / plan / result 区域，记录它们是否可见。
6. 不点击 `Run`。

预期可见结果：

- workbench shell 正常渲染。
- config controls 可见。
- run button 可以可见，但不能被点击。
- 没有触发 autonomous run。

证据要求：

- browser method。
- page URL。
- form/config 区域的可见观察。
- 明确记录 `Run` 未被点击。
- screenshot、trace、video 或 browser observation excerpt 之一。

### COV-004 · Use cases 页面渲染列表或 empty state

目标 URL：

```text
http://127.0.0.1:5174/exploration/autonomous/cases
```

操作：

1. 打开 use-cases 页面。
2. 观察页面标题或 card title。
3. 如果存在 refresh 和 workbench navigation 控件，确认它们可见。
4. 观察 spec cards/tables 是否可见，或 empty state 是否可见。
5. 不选择 runnable scenarios 执行。

预期可见结果：

- use-cases 页面正常渲染。
- spec list/table 可见，或明确 empty state 可见。
- 没有启动 batch run。

证据要求：

- browser method。
- page URL。
- list/table 或 empty-state 可见观察。
- screenshot、trace、video 或 browser observation excerpt 之一。

### COV-005 · 只观察 live-run 按钮，不点击

目标 URL：

```text
http://127.0.0.1:5174/exploration/autonomous
http://127.0.0.1:5174/exploration/autonomous/cases
```

操作：

1. 在 workbench 页面观察 `Run` button 或等价 live-run control。
2. 在 use-cases 页面观察 `Run selected` 和 per-scenario run affordances（如果可见）。
3. 记录这些控件是 enabled、disabled 还是 absent。
4. 不点击任何 live-run control。
5. 如果看到 `Run in Workbench`，只记录可见状态；它当前是 workbench deep-link，
   不是直接启动 run，但本用例不进入该分支。

预期可见结果：

- live-run controls 根据当前页面状态可见、禁用或不存在。
- 报告明确记录没有点击任何 live-run control。
- 没有请求 `/exploration/autonomous-runs` 或 stream endpoint。

证据要求：

- live-run controls 的浏览器观察。
- 明确 no-click 记录。
- screenshot、trace、video 或 browser observation excerpt 之一。

## 报告模板

```md
# Console Operator 可视化页面探索报告

日期：
Commit:
工作区：
工具：
目标 URL：

## 前置条件

- API health:
- console history:
- console workbench:
- console use cases:
- persisted run availability:

## 摘要

| 用例 | 状态 | 证据 |
| --- | --- | --- |

## 用例结果

### COV-001 · History 页面渲染关键控件或 empty state

- 状态：
- 方法：
- 页面 URL：
- 可见操作：
- 可见观察：
- 证据：
- 备注：
- 后续：

## 边界

- Autonomous endpoints called:
- `/exploration/autonomous-runs` called:
- `/exploration/autonomous-runs/stream` called:
- Autonomous explorer imported or run directly:
- verify-scenario used:
- 产品侧 LLM provider used:
- Product code modified:
- E2E spec modified:
- Package scripts modified:
- Live-run buttons clicked:
```

## 边界清单

- Product code modified: no。
- E2E spec modified: no。
- Package scripts modified: no。
- `docs/iterations/` modified: no。
- Autonomous endpoint called: no。
- `/exploration/autonomous-runs` called: no。
- `/exploration/autonomous-runs/stream` called: no。
- 产品侧 LLM provider used: no。
- Deterministic E2E claimed: no。
