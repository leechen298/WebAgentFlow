# AUI-01 · LearnedPath Catalog 可视化页面探索

## 目标

使用 Agent 操作真实浏览器，验证 LearnedPath catalog 作为 operator surface
仍然可用：页面能打开，catalog list 或 empty state 可见，trust filter 可操作，
有数据时可以打开 LearnedPath drawer，并且 drawer 中可以看到 replay section。

这是 **Agent-operated UI exploratory** 证据，不是 deterministic E2E、
API-only exploratory、component test，也不是 live autonomous run。

## 范围

目标页面：

- `http://127.0.0.1:5174/exploration/learned-paths`

主要证据报告路径：

- `docs/testing/results/YYYY-MM-DD-learned-path-catalog-visual-ui-exploratory.md`

如果当前 catalog 没有 LearnedPath row，drawer 相关用例可以记录为 `BLOCKED`。
不能用 API 输出或 headless Playwright 输出冒充浏览器可视化证据。

## 目标页面

| 区域 | URL |
| --- | --- |
| LearnedPath catalog | `http://127.0.0.1:5174/exploration/learned-paths` |

## 前置条件

执行浏览器操作前，记录：

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5174/exploration/learned-paths
```

drawer 用例的数据前置：

- catalog 中至少有一条 LearnedPath row。
- 如果当前已有 deterministic E2E seed 数据，可以直接复用。
- 如果没有任何 row，`LPC-003` 和 `LPC-004` 记录为 `BLOCKED`，并把可见 empty
  state 作为证据。

如果 console 或 API 不可访问，相关用例写 `BLOCKED`。不要为了让本次可视化验证通过而修改产品代码、seed 数据、package scripts 或 iteration 文档。

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
- 只验证 replay section presence 时，不点击 replay。
- 不点击 trust mutation 操作，例如 confirm、mark flaky、deprecate。
- 不改产品代码、E2E spec、package scripts 或 `docs/iterations/`。
- 没有真实浏览器可见证据时，不得写 PASS。

## 用例

### LPC-001 · Catalog 页面渲染列表或 empty state

目标 URL：

```text
http://127.0.0.1:5174/exploration/learned-paths
```

操作：

1. 打开 catalog 页面。
2. 记录当前 URL、页面标题或主要可见标题。
3. 观察 LearnedPath table/list 是否可见。
4. 如果没有 row，观察 empty state。
5. 记录 refresh 操作是否可见。

预期可见结果：

- catalog 页面正常渲染。
- LearnedPath table/list 可见，或明确 empty state 可见。
- 页面没有尝试启动 autonomous run。

证据要求：

- browser method。
- page URL。
- visible title。
- list/table 或 empty-state 可见观察。
- screenshot、trace、video 或 browser observation excerpt 之一。

### LPC-002 · Trust filter 会改变可见状态或 filter 状态

目标 URL：

```text
http://127.0.0.1:5174/exploration/learned-paths
```

操作：

1. 打开 catalog 页面。
2. 找到 trust filter。
3. 打开 filter dropdown。
4. 选择一个 trust value，例如 `Flaky`、`Confirmed`，或当前页面可见的本地化等价文案。
5. 观察 table/list、empty state 或已选 filter label 的变化。

预期可见结果：

- trust filter 可见且可操作。
- selected filter state 有可见变化，或 list / empty state 更新。
- 如果没有匹配 row，empty state 可见并被记录。

证据要求：

- filter 操作前后的浏览器观察。
- selected filter label，或 list / empty-state 的可见变化。
- screenshot、trace、video 或 browser observation excerpt 之一。

### LPC-003 · LearnedPath drawer 可从 row/card 打开

目标 URL：

```text
http://127.0.0.1:5174/exploration/learned-paths
```

操作：

1. 打开 catalog 页面。
2. 找到一个可见 LearnedPath row 或 card。
3. 只点击用于打开详情的安全操作，例如 `View actions`。
4. 观察 drawer。

预期可见结果：

- detail drawer 打开。
- drawer 中显示 path identity 或 scenario 信息。
- drawer 中显示 path trust 和 actions detail（如果当前 path 有这些数据）。
- 如果没有 row/card，本用例写 `BLOCKED` 并记录 empty state。

证据要求：

- 选中的 row/card 可见观察。
- drawer 打开后的可见观察。
- drawer title 或 scenario/path identity 可见。
- screenshot、trace、video 或 browser observation excerpt 之一。

### LPC-004 · Drawer replay section 可见但不触发 live autonomous run

目标 URL：

```text
http://127.0.0.1:5174/exploration/learned-paths
```

操作：

1. 打开 catalog 页面。
2. 从可见 row/card 打开 LearnedPath drawer。
3. 观察 replay section。
4. 如果存在 target URL input，确认它可见。
5. 如果存在 replay button，确认它可见。
6. 不点击 replay。

预期可见结果：

- drawer 中存在 replay section 或等价 replay affordance。
- 选中 path 支持 replay 时，target input 和 replay button 可见。
- 没有启动 autonomous run。
- 没有请求 `/exploration/autonomous-runs` 或 stream endpoint。

证据要求：

- drawer 打开后的浏览器观察。
- replay section 可见观察。
- 明确记录 replay 没有被点击。
- screenshot、trace、video 或 browser observation excerpt 之一。

## 报告模板

```md
# LearnedPath Catalog 可视化页面探索报告

日期：
Commit:
工作区：
工具：
目标 URL：

## 前置条件

- API health:
- console learned-path catalog:
- LearnedPath row availability:

## 摘要

| 用例 | 状态 | 证据 |
| --- | --- | --- |

## 用例结果

### LPC-001 · Catalog 页面渲染列表或 empty state

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
- Replay clicked:
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
