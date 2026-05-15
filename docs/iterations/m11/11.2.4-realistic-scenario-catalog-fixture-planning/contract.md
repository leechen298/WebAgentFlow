# 契约（Contract）

状态：documentation generated; implementation not started

## 概念 / 边界契约

11.2.4 定义 Realistic Scenario Catalog & Fixture Planning。它是 WebAgentFlow
自建真实网页验证场景库的文档级 contract，不是 fixture 实现。

11.2.4 不使用外部真实网站作为验证依赖。后续验证场景应由 WebAgentFlow 自建：

- 自建前端页面。
- 自建 mock API。
- 自建组件交互。
- 自建状态变化。
- 自建延迟、loading、toast、modal、popup、picker、form validation。
- 自建 PC / 移动端场景。

## Product Model / Scope / Roadmap Alignment

- 属于 M11.2 Runtime Observation & Realistic Web Hardening。
- 服务 L3 Actual Work replay observation。
- 不改变 L1 / L2 / L3 lifecycle。
- 不新增 Agent 角色。
- 不改变 Task Path Planner / Task Result Reporter 职责。
- 不改变 M12 recovery 边界。
- 不把外部真实网站作为稳定验证依赖。

## Business Complexity Contract

11.2.4 的页面复杂度按业务结构分类，不按单个 UI 技术行为分类。

页面业务复杂度固定为：

- `simple_business_page`
- `medium_business_page`
- `complex_business_page`
- `very_complex_business_page`

`toast`、`modal`、`loading`、`drawer`、`picker`、`virtualized list`、
`WebSocket`、`portal / teleport` 等属于 runtime behavior / interaction
pattern，不作为页面业务复杂度分类依据。

11.2.4 使用组合模型：

```text
业务页面复杂度
×
运行条件矩阵
×
runtime behavior
```

每个 scenario 应同时标明：

- business complexity。
- runtime conditions。
- runtime behavior / interaction pattern。
- current MVP expected observation。
- future expected observation。

`very_complex_business_page` 当前只进入 scenario catalog，不进入 11.2.4.1 -
11.2.4.5 的近期实现范围。它们需要后续单独拆包设计。

运行条件是横向变体，可以叠加到 `simple_business_page`、
`medium_business_page`、`complex_business_page` 和
`very_complex_business_page` 上，不作为页面类型。

## Scenario Catalog Contract

每个 scenario 至少包含：

```text
scenario_id
platform
page_type
business_domain
business_complexity
runtime_conditions
interaction_pattern
runtime_behavior
frontend_fixture_needed
backend_fixture_needed
current_mvp_expected_observation
future_expected_observation
non_goals
future_package
```

字段语义：

- `platform`：`pc`、`mobile` 或 `both`。
- `business_complexity`：`simple_business_page`、`medium_business_page`、
  `complex_business_page` 或 `very_complex_business_page`。
- `runtime_conditions`：横向运行条件变体，例如 normal network、slow
  network、timeout、validation error、server error、empty result。
- `current_mvp_expected_observation`：只能写当前 11.2.2 / 11.2.3 已支持能力。
- `future_expected_observation`：可以写未来 signal 或 component relation 方向，但必须标注未实现。
- `backend_fixture_needed`：说明该场景是否需要 11.2.4.5 mock backend。

## Fixture Contract

每个 fixture 至少包含：

```text
fixture_id
route
platform
page_type
scenario_name
trigger_action
runtime_behavior
frontend_state_change
backend_behavior
expected_visible_state
expected_wait_result
expected_observation_summary
current_mvp_limit
future_signal_support
reset_behavior
determinism_requirements
```

Fixture 必须满足：

- route 稳定。
- trigger action 可见且可重复。
- initial state deterministic。
- post-action state deterministic。
- reset behavior 明确。
- 不依赖外部网络服务。
- 不读取或保存用户真实数据。

## 当前 MVP 与未来能力边界

当前 11.2.2 / 11.2.3 已支持：

```text
url_changed
title_changed
network_idle_observed supporting only
wait_result
observation_summary
```

当前尚未支持但 fixture 需要规划：

```text
toast_shown
modal_opened
loading_finished
element_enabled
element_disabled
form_validation_message
list_changed
component-generated runtime surface relation
mobile picker / action sheet relation
```

这些 future signals 可以写入 expected future observation，但不能写成当前已实现。

## Network Delay And Error Scenario Contract

Scenario catalog 必须覆盖网络延迟和错误场景。M11.2 只记录 runtime evidence，不实现
失败后的 recovery / retry / abort。

必须纳入：

- slow search response。
- slow save response。
- slow detail loading。
- slow export preparation。
- delayed polling result。
- delayed async job completion。
- HTTP 400 validation error。
- HTTP 401 unauthorized。
- HTTP 403 forbidden。
- HTTP 404 missing resource。
- HTTP 409 conflict。
- HTTP 429 rate limited。
- HTTP 500 server error。
- network timeout。
- request cancelled / aborted。
- inline validation message。
- form item error message。
- toast error。
- modal error。
- banner / alert error。
- empty result state。
- retry button shown。
- disabled submit after error。
- loading overlay stuck then timeout。
- upload progress then failure。
- upload file type rejected。
- upload size exceeded。
- export generation failed。
- download unavailable。

## 状态 / 结果契约

11.2.4 不新增 runtime status，不改变 `WaitResult.status` 或
`ReplayObservationSummary.status`。

本轮只定义 planning 状态：

- `planned_current_mvp`：当前 MVP 可以观测或保守表达。
- `planned_future_signal`：场景应被规划，但 runtime signal 尚未实现。
- `planned_fixture_only`：先作为 fixture 页面行为存在，暂不要求 observation 自动识别。
- `out_of_scope_m12`：失败后的 retry / recovery / abort 留给 M12。

## Schema / API 契约

No runtime schema/API changes.

本轮不创建 Python / TypeScript schema，不修改 API route，不修改 DB schema，不修改 replay
response。

## Evidence / Observation 契约

11.2.4 的 evidence 是规划级 evidence，不是运行证据。

允许：

- 记录 scenario / fixture expected observation。
- 记录当前 MVP limit。
- 记录 future expected observation。
- 记录后续测试计划。

禁止：

- 声称 fixture 页面已实现。
- 声称 E2E 已运行。
- 声称 Task Result Reporter 已消费 observation evidence。
- 把 network idle 当成业务成功。
- 把前端 timer 模拟写成真实 network evidence。

## 不变契约

本轮不改变：

- Product lifecycle stages。
- Internal Agent roles。
- Public API contracts。
- Database schema。
- Replay status semantics。
- Reporter / recovery / abort boundaries。
- Observation signal implementation。

## 非目标

- 不实现 fixture 页面。
- 不实现 mock backend。
- 不实现 E2E。
- 不实现 Common Component Runtime Semantics resolver。
- 不接 Task Result Reporter。
- 不做 M12 recovery / retry / abort。
- 不调用 Page Understanding Agent。
- 不使用外部真实网站作为验证依赖。

## 未决问题

- 具体 11.2.4.x 实现包边界：由本轮 `plan.md` 建议，后续执行前再审核。
- 11.2.4.1 route shell 命名：后续实现包可按 `technical-design.md` 建议确认。
