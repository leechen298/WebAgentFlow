# 技术设计（Technical Design）

状态：documentation generated; implementation not started

## 当前状态（Current State）

- `apps/validation-site/` 已有 fixture 基础，包括 login、users、dashboard 等页面。
- `apps/validation-site/specs/` 已有 validation-site spec 基础。
- 11.2.2 已实现 step-level `wait_result`。
- 11.2.3 已实现 replay-level `observation_summary`。
- 当前实际 observation MVP 只支持 `url_changed`、`title_changed` 和
  `network_idle_observed` supporting only。
- 当前缺少系统化 PC / 移动端 scenario catalog。
- 当前缺少自建 runtime observation fixture 页面规划。
- 当前不依赖外部真实网站验证。

## Business Complexity Model

11.2.4.0 采用以下组合模型整理 scenario catalog：

```text
业务页面复杂度
×
运行条件矩阵
×
runtime behavior / interaction pattern
```

业务页面复杂度按页面业务结构分类：

- `simple_business_page`：单一目标、单一区块、少量输入、没有复杂状态切换。
- `medium_business_page`：有列表、表格、筛选、分页、简单操作，但主要围绕一个业务对象。
- `complex_business_page`：一个页面内有业务状态切换、多个操作阶段、动态字段、
  元素增减、显示隐藏、页面模式切换或组合操作。
- `very_complex_business_page`：跨页面、跨角色、长流程、强状态依赖、实时更新或
  复杂权限矩阵。

`toast`、`modal`、`loading`、`drawer`、`picker`、`virtualized list`、
`WebSocket`、`portal / teleport` 等属于 runtime behavior / interaction
pattern，不作为页面业务复杂度分类依据。

Runtime conditions are cross-cutting variants. They can be applied to simple,
medium, complex, and very complex pages, and must not be treated as page types.

`very_complex_business_page` 当前只进入 scenario catalog，不进入 11.2.4.1 -
11.2.4.5 的近期实现范围。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| 页面复杂度按业务结构分类 | 使用 business complexity model，runtime behavior 独立建 catalog。 | documentation validation | 防止把 toast / modal / loading 当成页面类型。 |
| 运行条件是横向变体 | Runtime Condition Matrix 可叠加到所有 business complexity。 | documentation validation | 弱网、错误、空结果不是页面类型。 |
| very complex 只记录 | very_complex_business_page 只进入 catalog，不进入近期 fixture 实现。 | documentation validation | 后续单独拆包。 |
| scenario catalog 不改变产品模型 | 只在 M11.2 文档中规划 fixture，不修改 product model。 | documentation validation | 不新增 Agent / lifecycle。 |
| fixture 不依赖外部网站 | 后续 fixture 放在 validation-site 和 mock backend。 | future fixture smoke | 外部网站只可作为研究参考，不作为验证依赖。 |
| fixture 必须 deterministic | 每个 fixture 记录 initial state、trigger、reset behavior。 | future route smoke | 11.2.4.2 - 11.2.4.4 可用固定 timer。 |
| fixture 可 reset | 每个 fixture contract 包含 reset behavior。 | future route smoke | 避免状态污染。 |
| fixture 不接 reporter | 11.2.4 只规划 runtime observation fixture。 | boundary tests | 11.2.5 才接 reporter。 |
| fixture 不触发 recovery | M11.2 只记录 evidence。 | boundary tests | M12 才做 retry / abort。 |
| 区分 current MVP vs future expected observation | scenario / fixture 均包含 current MVP limit 和 future signal support。 | documentation validation | 防止误称已实现。 |
| PC / mobile 都纳入规划 | catalog 分 PC / mobile 页面类型。 | documentation validation | 不只覆盖管理后台。 |
| simple -> very complex 分阶段 | catalog 使用 complexity ladder。 | documentation validation | 11.2.4.1 - 11.2.4.4 只做单页面与 shell。 |
| 前端 timer 不代表 network evidence | 前端 timer 只用于 deterministic UI state；11.2.4.5 mock backend 才覆盖 HTTP evidence。 | future fixture tests | 防止误读 slow response。 |

## 实现方案（Proposed Fixture Architecture）

本轮不实现代码。后续实现可采用以下结构：

```text
apps/validation-site/src/pages/runtime-observation/
apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue
apps/validation-site/src/pages/runtime-observation/SinglePageBasicBusiness.vue
apps/validation-site/src/pages/runtime-observation/SinglePageMediumBusiness.vue
apps/validation-site/src/pages/runtime-observation/SinglePageComplexBusiness.vue
apps/validation-site/src/pages/runtime-observation/MobileRuntimePatterns.vue
apps/validation-site/specs/runtime-observation/
apps/e2e/tests/runtime-observation/
```

后续 mock backend 可复用或扩展：

```text
apps/api/app/routers/validation_api.py
```

后续实现必须保持：

- fixture route 可直接打开。
- trigger action 可定位。
- 结果区域有 stable anchors。
- reset 操作可恢复初始状态。
- 同一场景可以重复运行。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| `docs/testing/scenarios` | Yes | 本轮扩展 scenario catalog。 | 文档级变化。 |
| validation-site pages | Planned | 后续实现 runtime observation fixture pages。 | 本轮不改源码。 |
| validation-site specs | Planned | 后续增加 fixture specs。 | 本轮不改源码。 |
| validation API mock backend | Planned | 11.2.4.5 后续实现 mock API。 | 本轮不改源码。 |
| E2E tests | Planned | 后续补 scoped E2E。 | 本轮不新增测试。 |
| API routes | No | 不新增运行时 API route。 | N/A |
| DB schema | No | 不修改 DB schema。 | N/A |
| CLI | No | 不修改 CLI。 | N/A |
| Console UI | No | 不修改 Console UI。 | N/A |
| Replay execution | No | 不修改 replay runtime。 | N/A |
| Task Result Reporter | No | 不接 reporter。 | 11.2.5 |
| M12 recovery | No | 不做 retry / abort。 | M12 |
| Docs | Yes | 新增 11.2.4 文档包。 | planning only |

## 11.2.4.1 · Single-page Runtime Fixture Shell

Shell 阶段只建立入口和约定，不实现具体业务页面：

- runtime observation fixture index。
- route shell。
- category navigation。
- reset convention。
- stable anchor convention。

每个后续 fixture 需要：

- stable heading。
- stable trigger selector。
- stable result region。
- reset button。
- deterministic timer duration when timer is used。
- visible state label。

## 11.2.4.2 · Single-page Basic Business Pages

实现 simple business pages 的单页面前端 fixture。11.2.4.2 可使用前端本地
状态和 deterministic timer 模拟 visible delay、loading、validation、empty state
和 error surface，但不代表真实 network evidence。

| Business page | Route candidate | Initial state | User action | Runtime behavior variants | Current MVP expected | Future expected |
|---|---|---|---|---|---|---|
| login | `/runtime-observation/basic/login` | empty form | submit credentials | validation, toast, URL/title navigation | title/url only if navigation happens | `form_validation_message`, `toast_shown` |
| register | `/runtime-observation/basic/register` | empty form | submit form | validation, delayed success | title/url only if navigation happens | `form_validation_message`, `toast_shown` |
| sms_login | `/runtime-observation/basic/sms-login` | phone input | request code / submit | countdown, validation | title/url only if navigation happens | `form_validation_message`, `toast_shown` |
| simple_search | `/runtime-observation/basic/search` | empty query / default result | search | loading, empty result | no primary unless URL/title changes | `list_changed`, `loading_finished` |
| simple_detail | `/runtime-observation/basic/detail` | detail region | refresh / load detail | loading, not found | title/url only if navigation happens | `text_appeared`, `loading_finished` |
| simple_settings | `/runtime-observation/basic/settings` | toggle state | save | disabled submit, toast | no primary unless URL/title changes | `toast_shown`, `element_enabled` |
| simple_confirm | `/runtime-observation/basic/confirm` | confirm action visible | confirm | modal, toast, loading | no primary unless URL/title changes | `modal_opened`, `toast_shown` |

## 11.2.4.3 · Single-page Medium Business Pages

实现 medium business pages 的单页面前端 fixture，先用本地前端状态模拟，不接真实
mock backend。

| Business page | Route candidate | Runtime behavior variants | Current MVP expected | Future expected |
|---|---|---|---|---|
| user_list | `/runtime-observation/medium/users` | filtering, pagination, empty result | no primary unless URL/title changes | `list_changed`, `loading_finished` |
| order_list | `/runtime-observation/medium/orders` | filtering, sorting, row action | no primary unless URL/title changes | `list_changed`, `toast_shown` |
| product_list | `/runtime-observation/medium/products` | enable/disable, row status | no primary unless URL/title changes | `list_changed`, `element_enabled` |
| table_management | `/runtime-observation/medium/table` | pagination, sorting, partial refresh | no primary unless URL/title changes | `list_changed` |
| create_edit_form | `/runtime-observation/medium/form` | validation, delayed success | title/url only if navigation happens | `form_validation_message`, `toast_shown` |
| file_upload | `/runtime-observation/medium/upload` | upload progress, rejection | no primary unless URL/title changes | `loading_finished`, `form_validation_message` |
| export_download | `/runtime-observation/medium/export` | preparation, artifact unavailable | no primary unless URL/title changes | `loading_finished`, artifact evidence |

## 11.2.4.4 · Single-page Complex Business Pages

实现 complex 单页面业务：

- dynamic_form。
- wizard_stepper。
- batch_operation。
- master_detail。
- view_edit_preview_mode_switch。
- permission_conditional_ui。
- conditional_fields。

这些页面可以包含 modal、drawer、field show/hide、mode switch、partial success 等
runtime behaviors，但业务复杂度来自页面业务结构，而不是单个技术行为。

`very_complex_business_page` 当前只进入 scenario catalog，不进入 11.2.4.1 -
11.2.4.5 的近期实现范围。

## 11.2.4.5 · Mock Backend Runtime Conditions

引入 mock backend 行为。它负责 HTTP 层 slow response、error status code、polling、
upload、export 和 async job completion。

计划 mock endpoints：

- mock search API。
- mock save API。
- mock validation API。
- mock async job API。
- mock polling endpoint。
- mock upload endpoint。
- mock export endpoint。

覆盖：

- slow search response。
- slow save response。
- slow detail loading。
- backend validation error。
- 401 / 403 / 404 / 409 / 429 / 500。
- network timeout。
- request cancelled / aborted。
- polling result update。
- async job completion / failure。
- upload progress then failure。
- export generation failed。
- download unavailable。

## 11.2.4.6 · Mobile Single-page Patterns

实现移动端单页面：

- mobile_login_sms。
- mobile_search。
- mobile_list。
- mobile_form。
- mobile_picker。
- mobile_action_sheet。
- mobile_pull_to_refresh。
- mobile_infinite_scroll。

Mobile picker、action sheet、bottom sheet、mobile toast 和 mobile dialog 都是 mobile
business pages 上的 runtime behavior，不是页面业务复杂度本身。

## 11.2.4.7 · E2E Evidence and Review

补 scoped E2E 和 evidence closure。必须记录实际命令、入口 URL、截图 / 日志 /
exit code，不得把未运行项写成通过。

## 数据模型 / Schema 变更（Data Model / Schema Changes）

本轮不新增 runtime schema，不修改 API request / response，不修改 database schema。

后续 fixture 实现阶段可以新增 validation-site spec metadata，但必须作为 fixture /
test artifact，而不是 WebAgentFlow runtime API contract。

未来 fixture spec 可包含：

```text
fixture_id
route
platform
page_type
scenario_id
business_complexity
runtime_conditions
runtime_behaviors
trigger_selector
result_selector
reset_selector
current_mvp_expected_observation
future_expected_observation
```

该 spec 只用于 validation-site / E2E，不进入 public API 或 DB schema。

## 服务 / 模块设计（Service / Module Design）

本轮不新增服务或模块。

后续实现阶段可按职责拆分：

- validation-site route index：展示 runtime observation fixture 入口。
- single-page basic business pages：login、register、sms_login、simple_search、
  simple_detail、simple_settings、simple_confirm。
- single-page medium business pages：user_list、order_list、product_list、
  table_management、create_edit_form、file_upload、export_download。
- single-page complex business pages：dynamic_form、wizard_stepper、batch_operation、
  master_detail、mode switch、permission conditional UI、conditional fields。
- mobile single-page patterns：mobile_login_sms、mobile_search、mobile_list、
  mobile_form、mobile_picker、mobile_action_sheet、mobile pull-to-refresh。
- validation API mock backend：slow response、error status、polling、upload、export。
- E2E specs：验证 fixture determinism 和 observation boundary。

## 数据流（Data Flow）

后续 single-page frontend fixture 数据流：

```text
open fixture route
-> deterministic initial state
-> user / replay trigger action
-> frontend local timer updates visible state
-> wait_result / observation_summary observe current MVP signals or remain conservative
-> reset restores initial state
```

后续 mock backend runtime condition 数据流：

```text
open fixture route
-> trigger action
-> frontend calls mock API
-> mock backend returns slow response / error / polling result / artifact status
-> frontend renders visible state
-> wait_result / observation_summary record supported evidence
```

Timer-based frontend flow is deterministic UI evidence only. Mock backend flow is the
first phase that can produce HTTP-layer slow response / error status evidence.

## 状态推导（Status / State Derivation）

11.2.4 不新增 runtime status。后续 fixture expectation 应按 current MVP 与 future
signal 分开写：

- URL/title route fixtures can expect current MVP primary observation.
- `network_idle_observed` remains supporting-only.
- toast / modal / loading / list refresh fixtures must not expect current MVP primary signal
  unless URL/title also changes.
- Future signals can be listed as `future_expected_observation` only.
- Error scenarios can expose visible evidence, but must not trigger retry / abort in M11.2.

## 兼容性（Compatibility）

- 旧 validation-site 页面继续有效。
- 旧 validation-site specs 继续有效。
- 11.2.2 `wait_result` 语义不变。
- 11.2.3 `observation_summary` 语义不变。
- 当前 replay status 不因 fixture planning 改变。
- 当前 API clients 不受影响。

## 失败 / 边界情况（Failure / Edge Cases）

后续 fixture 设计必须覆盖：

- initial state 未 reset。
- trigger 多次点击。
- timer 过快或过慢。
- empty result state。
- stuck loading。
- delayed async completion。
- server validation error。
- unauthorized / forbidden。
- conflict / rate limited。
- upload failure。
- export unavailable。
- only supporting signal observed。
- no current MVP signal observed。

这些 edge cases 只用于 fixture 规划，不在 11.2.4 文档包内实现。

## PC Page Scenario Catalog

PC 页面类型至少覆盖：

- 登录页。
- 注册页。
- 搜索 / 筛选页。
- 后台列表页。
- 表格管理页。
- 详情页。
- 创建 / 编辑表单页。
- 弹窗编辑页。
- 文件上传页。
- 导出 / 下载页。
- 设置页。
- 权限 / 角色管理页。
- 订单 / 用户 / 商品 / 内容管理页。
- 报表 / dashboard 页。
- 审批 / workflow 页。
- wizard / stepper 页。

## Mobile Page Scenario Catalog

移动端页面类型至少覆盖：

- 登录 / 手机验证码页。
- 搜索页。
- 列表页。
- 详情页。
- 表单页。
- 底部弹层页。
- picker 选择页。
- 地址选择页。
- 日期 / 时间选择页。
- 支付确认页。
- 订单提交页。
- 个人中心页。
- 设置页。
- 消息 / 通知页。
- 滚动加载页。
- 下拉刷新页。

## Complexity Ladder

Complexity ladder 按业务复杂度整理，不按单个 UI 技术行为整理。

Simple business pages:

- login。
- register。
- sms_login。
- forgot_password。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

Medium business pages:

- user_list。
- order_list。
- product_list。
- content_list。
- search_filter。
- table_management。
- detail_with_actions。
- create_edit_form。
- file_upload。
- export_download。

Complex business pages:

- multi_step_form。
- wizard_stepper。
- dynamic_form。
- batch_operation。
- modal_drawer_edit。
- master_detail。
- list_detail_linked。
- view_edit_preview_mode_switch。
- permission_conditional_ui。
- conditional_fields。
- upload_form_validation_combo。

Very complex business pages:

- approval_workflow。
- ticket_workflow。
- order_lifecycle。
- payment_flow。
- inventory_order_logistics_flow。
- collaborative_editing。
- websocket_realtime_status。
- cross_page_wizard。
- permission_matrix。
- report_builder。
- low_code_configurator。

Toast、modal、loading、picker、virtualized list、WebSocket / SSE、portal /
teleport 等只作为 runtime behavior / interaction pattern 叠加到业务页面类型上。

## 非目标（Non-goals）

- 不实现 Task Result Reporter integration。
- 不做 recovery / retry / abort / user takeover。
- 不实现 Common Component Runtime Semantics resolver。
- 不调用 Page Understanding Agent。
- 不实现 Page Context Bridge。
- 不读取或保存 raw HTML。
- 不修改 database schema。
- 不新增 API route。
- 不修改 CLI / UI / conversation event。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| documentation validation | scenario catalog 覆盖 PC / mobile / complexity / network errors | `test-plan.md` documentation rows |
| future fixture route smoke | route 可打开、trigger 可见、reset 生效 | `test-plan.md` future route smoke rows |
| future replay observation | current MVP 不误报 future signals | `test-plan.md` future replay rows |
| boundary tests | 不接 reporter、不触发 M12、不调用 autonomous run | `test-plan.md` boundary rows |

## 验证命令入口（Validation Commands）

本轮只运行文档级验证：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```
