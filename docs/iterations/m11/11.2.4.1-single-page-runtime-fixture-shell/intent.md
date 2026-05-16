# 意图（Intent）

状态：implemented

## 目标

实现 Single-page Runtime Fixture Shell，为后续 PC single-page runtime observation
fixtures 提供统一入口、分类、route shell、reset convention 和 stable anchor
convention。

## 动机

当前 validation-site 已有 `apps/validation-site/src/pages/IndexPage.vue` 和
`PAGES` catalog，现有入口包括 `/login`、`/users` 等页面。

11.2.4.0 已将 scenario catalog 固化为：

```text
业务页面复杂度
×
运行条件矩阵
×
runtime behavior
```

后续 11.2.4.2 / 11.2.4.3 / 11.2.4.4 会逐步实现 basic、medium、complex
business pages。为了避免这些 fixture 散落在 validation-site 中，11.2.4.1
先落地统一 shell。

## 成功标准

- `IndexPage.vue` 中有 Runtime Observation 入口，且不重写首页架构。
- `/runtime-observation` route 可打开。
- shell 页面展示 category navigation 和 planned fixture cards。
- shell contract 明确。
- route namespace 明确。
- fixture metadata shape 明确。
- stable anchor convention 明确。
- reset convention 明确。
- current MVP signals 与 future labels 分离。
- PC 优先、mobile 后移到 11.2.4.6 的边界明确。
- 后续实现应复用现有 `IndexPage.vue` / `PAGES` catalog，不重写首页架构。

## 非目标

- 不实现具体业务 fixture 页面。
- 不实现 mock backend。
- 不新增 E2E。
- 不修改 runtime observation 代码。
- 不接 Task Result Reporter。
- 不做 M12 recovery / retry / abort。
- 不实现 Common Component Runtime Semantics resolver。
- 不调用 autonomous run / `verify-scenario`。
