# Initial State Parser —— DOM 到 AST 的规则

本文规定客户端 DOM walker 的行为，实现位置 `apps/extension/src/recorder/initial-state.ts`。修改或扩展该 parser 时，下列规则为**强制约束**。

> **说明**：主 AST 管线正在往服务端 HTML → Full AST 迁移（参见 [`architecture.zh.md`](./architecture.zh.md)）。本文件仍对扩展端代码生效，但**新能力请在服务端** `apps/api/app/services/html_ast_parser.py` 中实现。

## 核心原则：统一递归 + 回退

parser 通过统一的递归流程处理每个 DOM 节点：

```
walkNode(el):
  1. classifyNode(el)     → 统一分类
                            （已知组件 > class/tag/id > 原生 HTML > null）
  2. tryProcess(el, type) → 按匹配到的 processor 提取
  3. processor 返回空     → 回退到 walkChildren 通用递归
  4. walkChildren 也为空 + 有可见内容
                          → 回退到 localHtml（type: 'custom'）
```

**不允许任何分支静默丢弃内容**。processor 返回 `[]` 的含义是"我处理不了，请回退"，**不是**"这个元素没内容"。

## 首要原则：DOM 忠实优先

parser 不做"先理解再改写"，而是"把页面忠实转录为结构化的中间表示"。

1. **原始 DOM 树关系优先** —— 输出 JSON 的 `children` 顺序必须与原 DOM 一致。
2. **兄弟顺序优先** —— 绝不为语义抽象而重排兄弟节点。
3. **节点类型优先** —— 每个 DOM 节点按其实际类型保留。
4. **隐藏节点必须保留** —— 通过 `cssState` 字段标注，绝不跳过。
5. **复杂节点保留 localHtml 回退** —— 语义抽取不足时使用。
6. **绝不为了"整齐"而重构页面结构** —— 例如"标题 + 内容"或"组 + 明细"这类抽象。

## 分类优先级（由高到低，先匹配先用）

1. **已知组件库元素** —— 如 `el-select` / `ant-cascader` / `van-cell` / `n-date-picker`。作为整体组件类型处理，**绝不拆解为内部 DOM 结构**（例如带内部 input 的 `el-select` 仍然当作 select 处理）。`component-classifier.ts` 使用前缀无关的检测，覆盖 12+ 个 UI 库。

2. **通过 class/tag/id 识别到的自定义结构** —— 如 `class="xx-select"` / `role="listbox"` 这类开发者命名的组件，通过模式匹配分类。

3. **标准 HTML 语义元素** —— `<table>` / `<input>` / `<select>` / `<button>` / `<a>` 等，按原生语义处理。

4. **不可分类元素** —— 递归 walkChildren 提取子节点结构。如果有可见内容但抽取失败，产出 `type: 'custom'` 节点并附 `localHtml`（最多 500 字）。

## 元素类型规则

**表格**：抽取表头和行数据。每行中每个 cell 都走统一的 `walkNode` 处理路径（不是纯文本抽取）。一个 `table` 节点同时带 `rows`（给前端展示用的文本摘要）和 `children`（给 Agent 分析用的完整结构）。

**iframe**：同源 iframe 通过 `contentDocument` 递归解析（遵循同样的规则），跨源 iframe 静默跳过。产出 `blockType: 'iframe-content'` 的 section 节点。支持多层 iframe 嵌套。

**导航区**：通过 HTML5 语义标签（`nav` / `aside` / `header` / `footer`）和 ARIA role（`role="navigation"` 等）识别，**位于主内容根之外**。支持嵌套子菜单（如 `el-submenu` + `aria-haspopup`）。叶节点是 `link` 或 `button` 类型，带 `href` / `active` / `selector`。**导航和菜单内容绝不能被跳过或丢弃** —— 它们在跨系统操作场景里是关键信息。

**表单容器**：通过已知的 form-item 模式识别（`.el-form-item` / `.ant-form-item` 等），按 label + control pair 处理。如果内容区有多个交互元素（≥2 个非 simple control，或 ≥3 个 simple control），递归展开为 `group` + `children`，而不是压成单个叶节点。如果 `processFormItem` 返回空（例如 `el-form-item__actions` 其实是按钮容器），**回退**到通用 walkChildren。

## 多 frame 初始状态合并

一个页面可能包含多个 frame（顶层 + 一个或多个 iframe，iframe 还可能嵌套）。每个 frame 独立运行 content script 并发送 `RECORDING_INITIAL_STATE`。背景脚本的 `setInitialState`（`state.ts`）这样处理：

- **同一 frameId 的重复发送**（例如 content.ts 两轮）→ 分数竞争式替换（保留分数更高的）。
- **不同 frameId** → **总是合并**。iframe 的 stateTree 作为 `iframe-content` section 追加到已有 state。不管嵌套多深 / iframe 多少个，每个 frame 的内容都保留下来。
- **绝不用替换代替合并** —— 顶层 frame 的导航/菜单 和 iframe 里的业务内容同等重要，iframe 里节点多或分数高不代表能覆盖顶层内容。

## 可见性处理

所有 walk 逻辑使用统一的可见性处理 —— **绝不跳过隐藏元素**。`shouldSkip` 只过滤 `SKIP_TAGS`（script/style/svg 等纯技术标签），**不**检查 `isVisible`。隐藏元素（`display:none` / `visibility:hidden`）仍然解析，通过 `cssState` 字段标注。

- `display:none` 表示不渲染也不可点击（例如折叠菜单）。
- `visibility:hidden` 表示占位但仍可接收交互。

**不同 walk 类型（导航 vs 内容）不得使用不同的可见性处理** —— 所有 walk 共享同一套规则。

## 截断回退

当 `MAX_NODES`（300）或 `MAX_NAV_ITEMS`（100）导致收集被截断时，**剩余内容不得静默丢弃**。被截断的导航区把 `localHtml` 挂到 section 节点上，保留原始 HTML 供后续扩展。

## 信息保留原则

优先保留对 Agent 理解页面功能有分析价值的信息：页面在做什么、有哪些可交互元素、当前状态是什么。没有即时分析价值但后续可能用得上的信息（如完整的导航菜单原始 HTML），放在 `localHtml` 里，不进入 Agent 的主分析管线。

## 禁止的做法

- **不得基于臆测跳过元素** —— 除 `SKIP_TAGS` 外没有硬编码跳过清单。所有元素都必须处理（包括隐藏的）。绝不假设开发者遵循了语义化 HTML。
- **不得拆解已知的复合组件** —— `el-select` 是 1 个 select 节点，不是 `input` + `div` + `ul`。组件边界就是分类边界。
- **不得产出空容器** —— 子节点为空的 section/group 必须丢弃。
- **不得静默丢弃内容** —— 分类失败必须回退到通用递归；通用递归也失败且有可见内容时，必须产出 localHtml 回退。被截断的内容必须保留 localHtml。
- **不得压扁复杂结构** —— 容器如果包含多个交互子元素，必须递归展开为子树，不能压成单个叶节点 + localHtml。
- **不得加特化逻辑** —— 所有处理规则必须通用化，不允许针对特定组件库或页面结构的 if-else 分支。所有 walk 类型共用同一套过滤与处理规则。
- **不得为"整齐"而重构页面结构** —— 不合并并列兄弟为"标题 + 内容"块；不为"清晰"改动节点边界；不为"美观"重排节点；不吞掉中间的 tip / alert / 按钮组 / 状态文本去凑"标题 + 内容"模式。
- **不得把复杂单元格降级为纯文本** —— 表格的图片列必须保留 `src`，操作列必须保留真实按钮，`input-number` 必须保留为结构化控件。
- **不得把多个按钮拼成单字符串** —— 按钮必须作为独立节点保留。
- **不得只留主控件而忽略兄弟辅助信息** —— form-item 里的 tip / description / 状态文本都必须保留。

## 输出结构

- **容器节点**（`section` / `group`）：带 `children[]` / `blockType` / `label`。**无 `selector`**。截断时可携带 `localHtml`。
- **叶节点**（`input` / `select` / `button` / `link` / `custom` 等）：带 `selector` / `value` / `label`。**无 `children`**。
- **`table` 节点**：可能是叶（`rows[][]`）也可能是容器（`children[]`），取决于单元格复杂度。
- **`localHtml`**：只在语义抽取不足的叶节点上出现，最多 500 字。
- **`rawHtmlSnapshot`**：独立的 debug-only 完整 HTML 快照，不属于 AST。

## 测试

多场景测试（`apps/extension/src/__tests__/multi-scenario.test.ts`）覆盖 8 类 fixture：企业官网、管理后台、H5 移动端、多导航文档页、无语义标签页、数据看板、Element UI 嵌套菜单 + iframe、复杂嵌套结构（form-item 内嵌表格 / 子表单、表格操作列）。

**任何 parser 改动都必须通过全部现有 fixture 测试。新加的解析行为必须同时加对应 fixture 和测试。**

## 参考测试用例

`apps/extension/src/__tests__/fixtures/lottery-page.html` 是一个真实用户页面的完整 HTML fixture。`apps/extension/src/__tests__/fixtures/lottery-page-expected.jsonc` 是**当前（有问题的）parser 输出**，用 `//` 和 `/* */` 注释标注了具体问题。这**不是**正确的期望输出 —— 它是**问题清单**。新 parser 改动必须逐条解决这些标注。

---

本文为 [`parser-rules.md`](./parser-rules.md) 的中文镜像，内容以英文版为准。
