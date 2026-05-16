# 11.2.4.2 · Single-page Basic Business Pages

状态：redesign required
里程碑：M11.2
类型：design-redesign-before-code

## 迭代定位

11.2.4.2 原目标是在 validation-site 的 runtime observation shell 下实现第一批 PC
single-page basic business fixtures。当前 `/runtime-observation/basic/*` 代码已实现并通过
build 级验证，但人工 review 否决该实现：页面业务密度不足，更像 UI-minimal toy fixtures，
不符合 WebAgentFlow 自建真实网页验证场景库目标。

本轮先修订文档，不改源码。后续代码重做必须以本包新增的页面级设计文档为 source of truth。

## Redesign Decision

当前实现状态：

- 7 个 basic routes 已实现。
- validation-site build 已通过。
- 人工 review 结论：rejected for redesign。
- 否决原因：页面只覆盖输入、按钮、结果区和 reset，缺少完整业务页面结构、secondary actions、
  distractors、本地业务失败状态和 production-like 页面密度。

新的标准：

```text
simple business page = business-simple
simple business page != UI-minimal toy page
```

Basic fixture 必须是 production-like single-page business fixture：业务目标单一，但页面结构完整，
具备主流程、本地失败状态、loading / pending、成功面、secondary action / distractor、reset 和
stable anchors。

## Fixture Design Documents

后续重做前必须先读取 7 个页面设计文档：

- [basic-login](./fixture-designs/basic-login.md)
- [basic-register](./fixture-designs/basic-register.md)
- [basic-sms-login](./fixture-designs/basic-sms-login.md)
- [basic-search](./fixture-designs/basic-search.md)
- [basic-detail](./fixture-designs/basic-detail.md)
- [basic-settings](./fixture-designs/basic-settings.md)
- [basic-confirm](./fixture-designs/basic-confirm.md)

每个页面设计文档定义：

- business goal。
- page anatomy。
- happy path。
- local validation / deterministic business failure states。
- loading / pending states。
- success states。
- secondary actions / distractors。
- reset behavior。
- stable anchors。
- current MVP expected observation。
- future expected observation。
- in-scope states。
- deferred states。
- implementation notes。
- business density checklist。
- acceptance checklist。

## Error Scope

11.2.4.2 只覆盖 frontend-local deterministic 的成功、失败、校验和空状态。

允许：

- required field validation。
- invalid credentials as local deterministic business error。
- email format error。
- password mismatch。
- terms not accepted。
- invalid SMS code。
- empty search result。
- missing detail / not found。
- settings warning。
- confirm cancel。
- loading / pending via deterministic frontend timer。

不覆盖：

- weak network / offline。
- real HTTP timeout。
- HTTP 400 / 401 / 403 / 404 / 409 / 429 / 500。
- real server validation。
- backend business conflict。
- retry after backend failure。
- user recovery / abort / takeover dialogue。

这些后续进入 `11.2.4.5 Mock Backend Runtime Conditions` 或 M12。

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

Future signal labels may appear in fixture metadata, but the UI must not present them as implemented
runtime observation support.

## 明确不做

- 本轮不修改 validation-site 源码。
- 本轮不新增测试代码。
- 不实现 medium / complex / mobile fixtures。
- 不实现 mock backend。
- 不新增 API / DB / CLI / Console 改动。
- 不修改 replay / wait service / observation summary / reporter。
- 不新增 current observation signal。
- 不做 M12 recovery / retry / abort。
- 不运行 E2E / `verify-scenario` / autonomous run。
