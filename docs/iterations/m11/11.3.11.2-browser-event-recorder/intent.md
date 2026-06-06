# 意图（Intent）

状态：proposed

## 目标

为 autonomous exploration attempt 增加 target-agnostic browser event recording，使后续
Terminal State Agent / stop controller 可以读取可审计、已脱敏、可关联到 run / attempt / action 的
browser event timeline。

## 动机

筛选、刷新、导出、弹窗和静默网络请求的终态不一定体现在 URL / title 或明显截图差异中。Playwright
本身能观察 request/response、download、dialog、popup、navigation、console 和 pageerror 等事件。
如果这些事件没有被结构化记录，后续 terminal-state 判断只能靠弱 DOM diff 或 Supervisor 结束后摘要，
无法在探索循环中可靠 stop / wait / continue。

Child 2 的职责是补上“浏览器发生了什么”的证据层，不评价 attempt 是否成功。

## 边界 / 非目标

- 不实现 Terminal State Agent verdict、ExplorationStopController 或 Attempt Evaluation ingest gate。
- 不改变 action planner、element discovery、wait_for_change 的业务语义。
- 不把 `/users`、字段名、按钮文案、DOM id 或 fixture-specific class 写入 runtime 规则。
- 不记录 raw cookies、authorization headers、tokens、raw request bodies 或 direct personal data。
- 不运行 live autonomous validation、`verify-scenario`、product UI smoke。

## 成功标准

- `contract.md` 定义 `BrowserEventTimeline` 和 event metadata redaction contract。
- `technical-design.md` 指明 event recorder 的 module boundary、hook points、storage direction 和 failure behavior。
- `test-plan.md` 覆盖 synthetic event、redaction、correlation、bounded timeline、compatibility 和 recorder failure。
- `review.md` 记录是否授权 runtime implementation；授权前不改 runtime code。
