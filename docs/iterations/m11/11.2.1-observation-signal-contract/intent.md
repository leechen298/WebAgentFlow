# 11.2.1 · 观察信号契约

## 目标

定义 M11.2 的 Observation Signal Contract，让后续 wait-for-change、replay
integration 和 reporter integration 可以围绕同一套观察语义展开。

## 动机

M11.2 要解决真实网页运行时复杂性，但不能一开始就进入实现。11.2.1 先规定
观察层能够表达什么、不能表达什么，以及这些信号如何被后续包消费。

如果没有 contract，后续 11.2.2 / 11.2.3 / 11.2.5 容易把浏览器级 reload、
页面内 loading、result evidence、retry、recovery 和 report conclusion 混在一起。

## 当前范围

11.2.1 文档化：

- Observation Signal 的定义。
- signal kind。
- signal scope。
- 推荐字段。
- page load / document reload 和页面内 loading UI 的区别。
- signal 与 replay action / step / result evidence 的关系。
- conservative reporting 边界。
- 与 11.2.0 case catalog 的对齐关系。

## 边界

本轮不做：

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 public API。
- 不修改 database schema。
- 不修改 TypeScript / Python schema 文件。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不实现 wait-for-change。
- 不实现 page-load waiting。
- 不实现 mutation observer。
- 不实现 network observer。
- 不实现 WebSocket / SSE 观察。
- 不做 recovery。
- 不做 retry policy。
- 不做 abort / interruption / user takeover。
- 不读取 raw HTML。
- 不保存 raw HTML。
- 不创建 M12 / 12.x 目录。
- 不创建 v0.2 分支。

## 成功标准

- 新增 11.2.1 文档包。
- `contract.md` 清楚定义 signal kind、scope、字段 proposal 和 conservative
  reporting 边界。
- 明确 `page_load_started` / `page_load_finished` 与 `loading_started` /
  `loading_finished` 不同。
- 明确 timeout / not-observed 不属于 11.2.1 signal kind。
- 明确 11.2.1 是文档级 contract，不是实现。
- 不声称 runtime observation、wait-for-change、page-load waiting 或 reporter
  observation integration 已实现。
- 验证命令通过。
