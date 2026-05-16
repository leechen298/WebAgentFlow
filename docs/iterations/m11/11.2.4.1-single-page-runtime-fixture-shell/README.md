# 11.2.4.1 · Single-page Runtime Fixture Shell

状态：文档生成完成，能力未实现
里程碑：M11.2
类型：docs

## 迭代定位

11.2.4.1 设计 validation-site 中 runtime observation fixture 的基础壳。

本轮只生成后续实现用的开发文档，不修改 validation-site 源码，不新增 route，
不实现具体 fixture 页面，不新增测试，也不运行 E2E / `verify-scenario` /
autonomous run。

后续实现包应在现有 `apps/validation-site/src/pages/IndexPage.vue` 的 `PAGES`
catalog 上增加 Runtime Observation 分类入口，而不是重写首页架构。

## 目标

11.2.4.1 为后续 PC single-page fixture 建设提供统一规范：

- runtime observation fixture index。
- route namespace。
- category navigation。
- fixture card metadata。
- stable anchor convention。
- reset convention。
- current MVP signal label。
- future signal label。

PC fixture 是 11.2.4.1 - 11.2.4.5 的优先目标。移动端分类可以在 shell 中预留，
但移动端具体 fixture 后移到 11.2.4.6。

## 文档

- [Intent](./intent.md)
- [Contract](./contract.md)
- [Technical Design](./technical-design.md)
- [Test Plan](./test-plan.md)
- [Plan](./plan.md)
- [Review](./review.md)

## Current MVP Boundary

Current MVP observation signals:

- `url_changed`
- `title_changed`
- `network_idle_observed` supporting only

Current evidence capabilities:

- `wait_result`
- `observation_summary`

Future labels may be shown by the shell, but they must not be presented as
implemented runtime observation signals.

## 明确不做

- 不写源码。
- 不新增测试代码。
- 不新增 `/runtime-observation` route。
- 不修改 `IndexPage.vue`。
- 不实现 fixture shell 页面。
- 不实现具体业务 fixture。
- 不实现 mock backend。
- 不接 replay / reporter / API。
- 不做 M12 recovery / retry / abort。
- 不调用 autonomous run / `verify-scenario`。
