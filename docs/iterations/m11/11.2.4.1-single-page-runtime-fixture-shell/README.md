# 11.2.4.1 · Single-page Runtime Fixture Shell

状态：implemented
里程碑：M11.2
类型：code

## 迭代定位

11.2.4.1 在 validation-site 中落地 runtime observation fixture 的基础壳。

本轮允许修改 validation-site 源码，目标是新增 runtime observation 入口、route
shell 和 index 页面。它仍然不实现具体业务 fixture 页面、不接 mock backend、不新增
E2E，也不运行 `verify-scenario` / autonomous run。

实现应在现有 `apps/validation-site/src/pages/IndexPage.vue` 的 `PAGES` catalog
上增加 Runtime Observation 分类入口，而不是重写首页架构。

## 目标

11.2.4.1 为后续 PC single-page fixture 建设提供统一 shell：

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

- 不实现具体业务 fixture。
- 不实现 mock backend。
- 不接 replay / reporter / API。
- 不做 M12 recovery / retry / abort。
- 不调用 autonomous run / `verify-scenario`。
