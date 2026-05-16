# 契约（Contract）

状态：implemented

## 概念 / 边界契约

11.2.4.1 实现 Single-page Runtime Fixture Shell。它是 validation-site runtime
observation fixture 的入口、分类和元数据壳，不是具体业务 fixture 页面实现。

Shell 只提供导航和规划级 metadata，不接 replay runtime、不接 wait service、不接
Task Result Reporter、不接 mock backend。

## Product Model / Scope / Roadmap Alignment

- 属于 M11.2 Runtime Observation & Realistic Web Hardening。
- 服务 L3 Actual Work replay observation 的 validation fixture 建设。
- 不改变 L1 / L2 / L3 lifecycle。
- 不新增 Agent 角色。
- 不改变 Task Path Planner / Task Result Reporter 职责。
- 不改变 M12 recovery 边界。
- 不依赖外部真实网站。

## Shell Contract

后续 shell 至少包含：

```text
runtime_observation_index
route_namespace
category_navigation
fixture_card_list
fixture_metadata
reset_convention
stable_anchor_convention
current_mvp_label
future_signal_label
```

## Route Namespace Contract

后续 route namespace 建议为：

```text
/runtime-observation
/runtime-observation/basic
/runtime-observation/medium
/runtime-observation/complex
/runtime-observation/mobile
```

11.2.4.1 实现包可以创建这些 routes。实现前必须确认 validation-site 当前 router
结构，并确保不创建 `/medium`、`/complex` 这类全局 route。

## Fixture Metadata Contract

每个 fixture card 后续至少包含：

```text
fixture_id
title
platform
business_complexity
page_type
route
phase
runtime_behaviors
runtime_conditions
current_mvp_expected_observation
future_expected_observation
status
```

`business_complexity` 允许值：

- `simple_business_page`
- `medium_business_page`
- `complex_business_page`
- `very_complex_business_page`

`status` 允许值：

- `planned`
- `implemented`
- `tested`
- `deferred`

`very_complex_business_page` 可以出现在 future / deferred card 中，但不进入
11.2.4.1 - 11.2.4.5 的近期实现范围。

## Stable Anchor Contract

后续 fixture 页面必须提供稳定定位点：

- `data-testid` 或等价稳定 selector。
- stable heading。
- stable trigger element。
- stable result region。
- stable reset control。
- stable status label。

这些 anchor 用于后续 route smoke、component tests、E2E 和 replay observation
验证。不得依赖视觉顺序、随机文本或外部网站内容作为唯一定位依据。

## Reset Convention Contract

每个 fixture 后续必须能 reset 到 deterministic initial state。

Reset 至少要求：

- 清空输入。
- 关闭 modal / drawer / picker。
- 清空 toast / alert。
- 恢复按钮 enabled / disabled 初始状态。
- 恢复列表初始数据。
- 停止 pending timer。
- 恢复 visible status label。

Reset 不代表 recovery / retry / abort。它只是 fixture 的可重复测试能力。

## Current MVP vs Future Signal Boundary

Current MVP observation signals:

```text
url_changed
title_changed
network_idle_observed supporting only
```

Current evidence capabilities:

```text
wait_result
observation_summary
```

Future labels that may appear in the shell but are not implemented:

```text
toast_shown
modal_opened
loading_finished
element_enabled
element_disabled
form_validation_message
list_changed
field_show_hide
mode_switch
component-generated runtime surface relation
mobile picker / action sheet relation
```

Future labels must be rendered as planned / future capabilities, not as current
runtime observation support.

## 状态 / 结果契约

11.2.4.1 不新增 runtime status，不改变 `WaitResult.status` 或
`ReplayObservationSummary.status`。

Shell card `status` 只表示 fixture planning / implementation state：

- `planned`：已规划但未实现。
- `implemented`：fixture 页面后续已实现。
- `tested`：fixture 后续有可复查验证证据。
- `deferred`：已记录但不进入近期实现范围。

## Schema / API 契约

No runtime schema/API changes.

本轮不创建 Python schema，不修改 API route，不修改 DB schema，不修改 replay response。
前端 shell 可以使用组件内静态 TypeScript metadata 类型。

## Evidence / Observation 契约

11.2.4.1 的 runtime evidence 仍由后续 replay observation 流程产生。Shell 本身只提供
可导航、可审查的 fixture planning metadata，不产生 `wait_result` 或
`observation_summary`。

允许：

- 实现 `/runtime-observation` shell route。
- 在 validation-site 首页增加 Runtime Observation 入口。
- 展示 shell metadata contract。
- 展示 current MVP / future signal labels。

禁止：

- 把 planned fixture card 链接成已实现业务页面。
- 声称 E2E 已运行。
- 声称 future signals 已被 runtime observation 支持。

## 兼容性契约

后续实现必须保持：

- 不破坏现有 `/` 首页。
- 不删除 `/login`、`/users`。
- 不改变已有 specs。
- 不改变 workbench deep link 逻辑。
- 不改变 API。
- 不改变 replay。
- 不改变 reporter。

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

- 不实现具体业务 fixture。
- 不实现 mock backend。
- 不实现 E2E。
- 不接 replay / reporter。
- 不做 M12 recovery / retry / abort。
- 不调用 autonomous run / `verify-scenario`。
- 不使用外部真实网站作为验证依赖。

## 未决问题

- 后续实现前需确认 validation-site 当前实际 router 文件和测试命令。
