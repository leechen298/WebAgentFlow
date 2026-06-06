# Intent

状态：proposed

## 目标

本迭代的目标是补齐 WebAgentFlow 学习资产模型中的中间层：

```text
ExplorationRun evidence -> LearnedCapability -> composable execution -> LearnedPath
```

成功状态不是让某个页面学完所有排列组合，而是让 L1 learning 能够沉淀可复用的原子能力，
让 L3 runtime 在缺少完整 LearnedPath 时可以基于已验证能力做有界组合，并在组合执行成功后
再沉淀完整 LearnedPath。

## 动机

Clean-slate `/users` live validation 证明了当前后端已经能生成多条 filter scenario run，
也能把 action-scoped terminal evidence gate 接到 LearnedPath ingest。但它同时暴露出
当前设计的结构性缺口：

- 完整 LearnedPath 太粗。它适合 replay 一条已验证路径，不适合表达“某个控件可输入”、
  “某个按钮触发列表刷新”、“某个 tab 切换后产生子区域”。
- 穷举组合太贵。筛选页如果学习所有字段组合，会产生大量低价值 scenario；用户并不需要
  等待完整覆盖，后续也可以通过 L2 teaching 兜底。
- Page Understanding Agent 的输出还没有成为学习边界输入。它应该帮助决定页面用途、
  主要区域、可学习能力、终态候选和样本值来源，而不是只在终态判断里做辅助描述。
- `wagent chat` 的 HTTP timeout 和后端 learning batch 生命周期没有闭合。客户端退出后，
  后端仍可能继续驱动浏览器。

## 成功标准

- 定义新的 `LearnedCapability` 资产契约，并说明它和 ExplorationRun、LearnedPath、
  PageAnalysis、Page Understanding hints 的关系。
- 定义 bounded learning policy：默认学习哪些原子能力，哪些组合必须学习，哪些组合推迟到
  runtime composition 或 L2 teaching。
- 定义 runtime composition contract：代码可以组合已验证能力；Agent 只能提供意图和候选，
  不能直接输出 selector-level execution。
- 定义 learning batch lifecycle：`running / completed / partial_success / timed_out /
  cancelled / failed / unverified`，并要求 CLI timeout / disconnect 不得让后台学习无限继续。
- 定义测试计划，覆盖 asset persistence、bounded scenario generation、composition、
  cancellation、history evidence 和 live-run 边界。
- 更新产品模型和 M11 索引，使后续实现 Agent 不会把 11.3.12 理解为 `/users` 特化修复。

## 非目标

- 不为 `/users` 页面硬编码字段、按钮、数据、route 或 selector。
- 不实现所有操作元素的全排列学习。
- 不让 LLM 在 L3 中逐步操作浏览器。
- 不替代 LearnedPath；LearnedPath 继续作为完整成功路径资产存在。
- 不实现完整 L2 teaching UI；本包只定义 composition 失败后的 handoff 边界。
- 不运行 live autonomous validation 或 `verify-scenario`。

## 假设

- M11.3.10 的 `FilterCapability / CapabilityScenario` 可作为临时 discovery 数据的参考，
  但不能直接等同于持久化的 LearnedCapability。
- M11.3.11 的 terminal-state verdict 和 attempt ingest gate 是 LearnedCapability
  evidence 的基础输入。
- 旧 LearnedPath 必须继续可读、可 replay、可被 Task Path Planner 使用。
