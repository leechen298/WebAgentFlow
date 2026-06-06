# 意图（Intent）

状态：proposed

## 目标

从现有 PageAnalysis 生成 target-agnostic terminal hints，使后续 Terminal State Agent /
stop controller 能知道页面大致用途、页面区域、可能功能和每类功能可能对应的终态类型。

## 动机

Child 2 记录了浏览器事件，但事件本身不告诉系统“这个按钮更像搜索、导出、详情还是提交”。
终态判断需要语义提示：搜索/筛选通常期待 list refresh 或 network completion，导出期待 download，
详情可能期待 modal/popup，导航期待 URL/title/frame lifecycle。Child 3 先用 deterministic bridge
从 PageAnalysis 产出这些提示，避免第一版依赖 live LLM。

## 边界 / 非目标

- 不实现 Terminal State Agent verdict 或 stop/wait/continue policy。
- 不运行 LLM provider smoke，不新增 prompt asset。
- 不输出 executable selectors、raw DOM paths 或 target-specific `/users` 规则。
- 不改变 action planner、browser event recorder、LearnedPath ingest gate。
- 不运行 live autonomous validation。

## 成功标准

- `contract.md` 定义 PageTerminalHint / PageRegionHint / CandidateTerminalState schema。
- `technical-design.md` 指明 deterministic extraction 的规则和 fallback。
- Runtime implementation（若授权）只新增 schema/service/tests，并保持 PageAnalysis 旧消费者兼容。
- Tests 覆盖 list/search、form/create、modal/detail、download/export、navigation/no-control 页面。
