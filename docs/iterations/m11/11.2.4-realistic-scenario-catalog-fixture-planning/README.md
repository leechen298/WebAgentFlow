# 11.2.4 · Realistic Scenario Catalog & Fixture Planning

状态：文档生成完成，fixture 页面 / mock backend / E2E 尚未实现
里程碑：M11.2
类型：docs

## 迭代定位

11.2.4 规划 WebAgentFlow 自建真实网页验证场景库。它不是直接开发 fixture
页面，也不是找线上网站做一次性验证。

本轮产出后续页面、mock backend 和 E2E 的开发文档，供后续 11.2.4.x 实现包读取：

- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`

后续实现包再在 validation-site 中建设自有 fixture 页面、mock API、可复现状态变化
和对应验证证据。

## 为什么先做场景目录

11.2.2 已实现 step-level `wait_result`。11.2.3 已实现 replay-level
`observation_summary`。当前这些能力主要通过 mock / service tests 验证。

下一步需要先把真实网页常见场景系统化，而不是立刻实现某几个页面：

- PC 常见页面类型。
- 移动端常见页面类型。
- 常见交互和组件库运行时 surface。
- 网络慢响应、错误响应、空结果、权限错误、上传 / 导出失败。
- simple / medium / complex / very complex 复杂度分层。
- 11.2.4.1 - 11.2.4.4 单页面 fixture 与 11.2.4.5 mock backend 的边界。

11.2.4.0 已将 scenario catalog 固化为“业务页面复杂度 × 运行条件矩阵 ×
runtime behavior”模型。Toast、modal、loading、picker 等属于 runtime behavior，
不作为页面业务复杂度分类依据。

## 文档

- [Intent](./intent.md)
- [Contract](./contract.md)
- [Technical Design](./technical-design.md)
- [Test Plan](./test-plan.md)
- [Plan](./plan.md)
- [Review](./review.md)

## 当前 MVP 边界

Current MVP observation signals:

- `url_changed`
- `title_changed`
- `network_idle_observed` supporting only

Current evidence capabilities:

- `wait_result`
- `observation_summary`

当前尚未支持，但 11.2.4 需要纳入 fixture 规划：

- `toast_shown`
- `modal_opened`
- `loading_finished`
- `element_enabled`
- `element_disabled`
- `form_validation_message`
- `list_changed`
- component-generated runtime surface relation
- mobile picker / action sheet relation

这些可以进入场景规划和未来 fixture 预期，但不能写成当前 runtime observation 已实现。

## Phase 策略

- [11.2.4.1](../11.2.4.1-single-page-runtime-fixture-shell/)：Single-page Runtime Fixture Shell，建立入口、route shell、reset
  convention 和 stable anchor convention。状态：implemented。
- [11.2.4.2](../11.2.4.2-single-page-basic-business-pages/)：Single-page Basic Business Pages，覆盖 login、register、
  sms_login、simple_search、simple_detail、simple_settings、simple_confirm。状态：
  implementation-ready。
- 11.2.4.3：Single-page Medium Business Pages，覆盖 user_list、order_list、
  product_list、table_management、create_edit_form、file_upload、export_download。
- 11.2.4.4：Single-page Complex Business Pages，覆盖 dynamic_form、wizard_stepper、
  batch_operation、master_detail、mode switch 和 permission conditional UI。
- 11.2.4.5：Mock Backend Runtime Conditions，覆盖 slow response、server
  validation、HTTP error、polling、upload / export 和 async job completion。
- 11.2.4.6：Mobile Single-page Patterns，覆盖 mobile_login_sms、mobile_search、
  mobile_list、mobile_form、mobile_picker、mobile_action_sheet 等。
- 11.2.4.7：E2E Evidence and Review。

前端 timer 只用于 deterministic fixture，不代表真实 network evidence。
Mock backend 才负责 HTTP 层 slow response、error status code、polling、upload 和
export。

## Planning Package Boundary

This parent planning package only defines the scenario catalog and fixture roadmap.
Implementation packages under `11.2.4.x` are allowed to modify the files listed in
their own `plan.md`.

Parent-package boundary:

- no runtime source was implemented in this planning package。
- no tests or E2E were added in this planning package。
- no fixture pages or mock backend were implemented in this planning package。
- no API / DB / CLI / Reporter contract changed in this planning package。
- Task Result Reporter, M12 recovery / retry / abort, autonomous run, and
  `verify-scenario` remain outside this planning package。
- external real websites are not validation dependencies。
- 不读取或保存 raw HTML。
