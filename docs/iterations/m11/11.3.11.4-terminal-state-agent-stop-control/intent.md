# 意图（Intent）

状态：PACKAGE_COMPLETE

## 目标

基于 child 2 的 `BrowserEventTimeline` 和 child 3 的 `PageTerminalHintSet` 生成 terminal-state
verdict、terminal type、evidence strength、evidence summary、stop decision 和 warnings。

## 动机

现在系统已经能记录浏览器事件并生成页面语义提示，但还没有统一 classifier 把这些信号合成为
“是否已到可评价终态”。Child 4 补上这个 advisory layer，使 child 5 可以再判断 attempt 是否能沉淀。

## 边界 / 非目标

- 不把 terminal verdict 直接写成 LearnedPath success。
- 不修改 pass_gate / Supervisor scorecard。
- 不替代 Attempt Evaluation Agent。
- 不做 unbounded wait 或真实循环中断。
- 不运行 live autonomous validation。

## 成功标准

- 定义并实现 terminal-state verdict schema。
- 覆盖 navigation、list_refresh、network_completion、modal/popup、dialog、download、toast/status、
  region_changed、no_observable_change、terminal_failed。
- 输出 stop/wait/continue/unverified_stop，但第一版为 advisory metadata。
- Non-live tests 覆盖所有 terminal types 和 uncertainty/failure boundaries。
