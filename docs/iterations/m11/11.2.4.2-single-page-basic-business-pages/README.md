# 11.2.4.2 · Single-page Basic Business Pages

状态：implementation-ready
里程碑：M11.2
类型：code

## 迭代定位

11.2.4.2 在 validation-site 的 runtime observation shell 下实现第一批 PC
single-page basic business fixtures。

本轮允许修改 validation-site 前端源码，目标是新增 simple business pages 的
deterministic frontend fixtures。它不接 mock backend，不新增 API，不修改 replay /
reporter / observation runtime，也不运行 E2E / `verify-scenario` / autonomous run。

## 前置条件

- 11.2.4.0 已固化 scenario catalog：
  `业务页面复杂度 × 运行条件矩阵 × runtime behavior`。
- 11.2.4.1 已实现 `/runtime-observation` shell、category navigation 和 planned
  fixture cards。
- 本包包含 code iteration 必需文档：`intent.md`、`contract.md`、已审核
  `technical-design.md`、`test-plan.md`、`plan.md` 和 `review.md`。
- Execution agent may start implementation after reading this package in the
  order required by `webagentflow-iteration-dev`。

## 目标

实现以下 PC basic business fixtures：

- login。
- register。
- sms_login。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

这些 fixtures 使用前端本地状态和 deterministic timer 模拟 loading、validation、
visible error surface 和 empty state。Timer 只代表前端确定性 fixture，不代表真实
HTTP network evidence。

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

- 不实现 medium / complex / mobile fixtures。
- 不实现 mock backend。
- 不新增 API / DB / CLI / Console 改动。
- 不修改 replay / wait service / observation summary / reporter。
- 不新增 current observation signal。
- 不做 M12 recovery / retry / abort。
- 不运行 E2E / `verify-scenario` / autonomous run。
