# 真实网页运行时场景目录（Realistic Web Runtime Cases）

状态：场景目录已初始化

本文档记录 M11.2 的真实网页运行时场景。它不是测试计划，也不是证据报告。

下列场景不代表已经自动化、人工验证或被 E2E 覆盖。它们是后续 11.2.x 设计、
fixture、实现、QA 和 evidence 包的输入。

## 观察边界

M11.2 负责观察和记录运行时变化。M12 决定当这些变化表示失败、不确定、中断
或需要 recovery 时应该怎么处理。

Post-action Observation 覆盖用户或 replay 动作后短时间内的页面变化。Passive
Runtime Observation 覆盖不是由当前动作直接触发的页面变化。

## Business Page Complexity Model

11.2.4.0 使用业务页面复杂度，而不是单个 UI 技术行为，作为 scenario catalog
的主分类。

分类模型：

```text
业务页面复杂度
×
运行条件矩阵
×
runtime behavior / interaction pattern
```

`toast`、`modal`、`loading`、`drawer`、`picker`、`virtualized list`、
`WebSocket`、`portal / teleport` 等属于 runtime behavior，不作为页面业务复杂度
分类依据。

### simple_business_page

定义：单一目标、单一区块、少量输入、没有复杂状态切换。

页面类型：

- login。
- register。
- sms_login。
- forgot_password。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

说明：

- 当前 validation-site 已有 `/login` 属于 simple business page。
- simple 页面也可以叠加弱网、后端错误、前端校验、空结果等运行条件。
- simple 不代表没有错误状态，只代表业务结构简单。

### medium_business_page

定义：有列表、表格、筛选、分页、简单操作，但主要仍围绕一个业务对象。

页面类型：

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

说明：

- 当前 validation-site 已有 `/users` 类页面通常属于 medium business page。
- 表格默认归为 medium。
- 如果表格包含复杂动态列、批量操作、权限差异、行内编辑、主从联动，可以升级为
  complex。

### complex_business_page

定义：一个页面内存在明显业务状态切换、多个操作阶段、动态字段、元素增减、显示
隐藏、页面模式切换或组合操作。

页面类型：

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

说明：

- 页面元素增减 / 显示隐藏 / 页面类型切换属于 complex。
- complex 仍可以是单页面。
- 11.2.4.4 优先覆盖 complex 单页面业务。

### very_complex_business_page

定义：跨页面、跨角色、长流程、强状态依赖、实时更新或复杂权限矩阵。

页面类型：

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

说明：

- very_complex 当前只进入 scenario catalog。
- very_complex 不进入 11.2.4.1 - 11.2.4.5 的近期实现范围。
- 后续需要单独拆包设计。

## PC Business Page Catalog

PC 场景目录用于覆盖常见后台、SaaS、运营、内容和业务管理页面。后续 fixture
应优先自建在 validation-site 中，不依赖外部真实网站。

| scenario_id | business_complexity | page_type | common_user_goal | runtime_behaviors | condition_variants | recommended_phase | current MVP | future observation |
|---|---|---|---|---|---|---|---|---|
| pc_login_basic | simple_business_page | login | 用户登录系统 | submit, validation, toast/error | normal_network, slow_network, backend_validation_error, frontend_validation_error, unauthorized_401 | 11.2.4.2 / 11.2.4.5 | title/url only if navigation happens | form_validation_message, toast_shown |
| pc_register_basic | simple_business_page | register | 创建账号或提交注册信息 | submit, validation, delayed success | normal_network, backend_validation_error, server_error_500 | 11.2.4.2 / 11.2.4.5 | title/url only if navigation happens | form_validation_message, toast_shown |
| pc_simple_search | simple_business_page | simple_search | 输入关键词并查看结果 | input, search, empty result | normal_network, slow_network, empty_result, timeout | 11.2.4.2 / 11.2.4.5 | no primary unless URL/title changes | list_changed, loading_finished |
| pc_simple_detail | simple_business_page | simple_detail | 查看单个对象详情 | load detail, status label | normal_network, slow_detail_loading, not_found_404 | 11.2.4.2 / 11.2.4.5 | title/url only if navigation happens | text_appeared, loading_finished |
| pc_simple_settings | simple_business_page | simple_settings | 修改简单设置 | toggle, save, toast | normal_network, slow_save_response, backend_business_conflict | 11.2.4.2 / 11.2.4.5 | no primary unless URL/title changes | toast_shown, element_enabled |
| pc_simple_confirm | simple_business_page | simple_confirm | 确认一个单步操作 | click confirm, modal, toast | normal_network, slow_save_response, server_error_500 | 11.2.4.2 / 11.2.4.5 | no primary unless URL/title changes | modal_opened, toast_shown |
| pc_user_list | medium_business_page | user_list | 查询、筛选、分页用户 | filter, pagination, partial refresh | normal_network, slow_search_response, empty_result, rate_limited_429 | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, loading_finished |
| pc_order_list | medium_business_page | order_list | 筛选订单并查看状态 | filter, sort, row action | normal_network, slow_search_response, backend_business_conflict, empty_result | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, toast_shown |
| pc_product_list | medium_business_page | product_list | 管理商品列表 | search, enable/disable, row action | normal_network, partial_success, server_error_500 | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, element_enabled |
| pc_content_list | medium_business_page | content_list | 管理内容条目 | filter, batch status, preview | normal_network, empty_result, forbidden_403 | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, modal_opened |
| pc_search_filter | medium_business_page | search_filter | 组合筛选并刷新结果 | form filters, partial refresh | normal_network, slow_search_response, empty_result, timeout | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, loading_finished |
| pc_table_management | medium_business_page | table_management | 管理表格数据 | sort, pagination, row action | normal_network, empty_result, rate_limited_429 | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed |
| pc_detail_with_actions | medium_business_page | detail_with_actions | 在详情页执行简单动作 | click action, modal, toast | normal_network, slow_save_response, conflict_409 | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | modal_opened, toast_shown |
| pc_create_edit_form | medium_business_page | create_edit_form | 创建或编辑业务对象 | form submit, validation | normal_network, frontend_validation_error, backend_validation_error, server_error_500 | 11.2.4.3 / 11.2.4.5 | title/url only if navigation happens | form_validation_message, toast_shown |
| pc_modal_edit | complex_business_page | modal_edit | 在弹窗中编辑对象 | modal open, form submit, list update | normal_network, backend_validation_error, conflict_409 | 11.2.4.4 / 11.2.4.5 | no primary unless URL/title changes | modal_opened, form_validation_message, list_changed |
| pc_drawer_edit | complex_business_page | drawer_edit | 在抽屉中编辑对象 | drawer open, conditional fields | normal_network, backend_validation_error, forbidden_403 | 11.2.4.4 / 11.2.4.5 | no primary unless URL/title changes | modal_opened, field_show_hide |
| pc_file_upload | medium_business_page | file_upload | 上传文件并查看结果 | upload progress, validation | normal_network, upload_file_type_rejected, upload_size_exceeded, upload_progress_then_failure | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | loading_finished, form_validation_message |
| pc_export_download | medium_business_page | export_download | 导出并下载文件 | export preparation, artifact link | normal_network, slow_export_preparation, export_generation_failed, download_unavailable | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | loading_finished, toast_shown |
| pc_dashboard_report | complex_business_page | dashboard_report | 查看报表和局部刷新 | cards, charts, partial refresh | normal_network, slow_detail_loading, partial_success, stuck_loading | 11.2.4.4 / 11.2.4.5 | no primary unless URL/title changes | list_changed, loading_finished |
| pc_role_permission | complex_business_page | role_permission | 配置角色权限 | tree/table, conditional UI | normal_network, forbidden_403, conflict_409, partial_success | 11.2.4.4 / 11.2.4.5 | no primary unless URL/title changes | field_show_hide, element_enabled |
| pc_approval_workflow | very_complex_business_page | approval_workflow | 处理多状态审批流 | multi-step state, role-dependent actions | normal_network, forbidden_403, conflict_409, partial_success | future package | planning only | workflow-level evidence, reporter integration |
| pc_wizard_stepper | complex_business_page | wizard_stepper | 按步骤完成配置 | step transition, validation, mode switch | normal_network, backend_validation_error, stuck_loading | 11.2.4.4 / future workflow package | no primary unless URL/title changes | mode_switch, form_validation_message |

## Mobile Business Page Catalog

移动端场景目录用于覆盖常见 H5、移动 Web、移动组件库和窄屏交互。

| scenario_id | business_complexity | page_type | common_user_goal | runtime_behaviors | condition_variants | recommended_phase | current MVP | future observation |
|---|---|---|---|---|---|---|---|---|
| mobile_login_sms | simple_business_page | mobile_login_sms | 使用手机号验证码登录 | input, countdown, validation | normal_network, slow_network, backend_validation_error, unauthorized_401 | 11.2.4.2 / 11.2.4.6 / 11.2.4.5 | title/url only if navigation happens | form_validation_message, toast_shown |
| mobile_search | simple_business_page | mobile_search | 搜索并查看结果 | input, loading, empty result | normal_network, slow_search_response, empty_result, timeout | 11.2.4.2 / 11.2.4.6 / 11.2.4.5 | no primary unless URL/title changes | list_changed, loading_finished |
| mobile_list | medium_business_page | mobile_list | 浏览列表并筛选 | list, infinite scroll, pull refresh | normal_network, slow_network, empty_result, rate_limited_429 | 11.2.4.3 / 11.2.4.6 / 11.2.4.5 | no primary unless URL/title changes | list_changed |
| mobile_detail | simple_business_page | mobile_detail | 查看详情 | load detail, status region | normal_network, slow_detail_loading, not_found_404 | 11.2.4.2 / 11.2.4.6 / 11.2.4.5 | title/url only if navigation happens | text_appeared, loading_finished |
| mobile_form | medium_business_page | mobile_form | 提交移动端表单 | form submit, validation, toast | normal_network, frontend_validation_error, backend_validation_error | 11.2.4.3 / 11.2.4.6 / 11.2.4.5 | no primary unless URL/title changes | form_validation_message, toast_shown |
| mobile_bottom_sheet | complex_business_page | mobile_bottom_sheet | 在底部弹层中选择动作 | bottom sheet, action selection | normal_network, request_cancelled, forbidden_403 | 11.2.4.4 / 11.2.4.6 | no primary | mobile action sheet relation |
| mobile_picker | complex_business_page | mobile_picker | 通过 picker 选择值 | picker open, option select | normal_network, frontend_validation_error | 11.2.4.4 / 11.2.4.6 | no primary | mobile picker relation |
| mobile_address_picker | complex_business_page | mobile_address_picker | 选择省市区地址 | cascaded picker, field update | normal_network, backend_validation_error | 11.2.4.4 / 11.2.4.6 | no primary | mobile picker relation, field_show_hide |
| mobile_date_time_picker | complex_business_page | mobile_date_time_picker | 选择日期或时间 | date/time picker, validation | normal_network, frontend_validation_error | 11.2.4.4 / 11.2.4.6 | no primary | mobile picker relation |
| mobile_payment_confirm | very_complex_business_page | mobile_payment_confirm | 确认支付 | confirm, loading, redirect/status | normal_network, timeout, request_cancelled, server_error_500 | future package | planning only | payment-flow evidence |
| mobile_order_submit | complex_business_page | mobile_order_submit | 提交订单 | form, confirm, loading, toast | normal_network, backend_business_conflict, server_error_500 | 11.2.4.4 / 11.2.4.5 / 11.2.4.6 | title/url only if navigation happens | toast_shown, loading_finished |
| mobile_profile | simple_business_page | mobile_profile | 查看个人中心 | load profile, simple navigation | normal_network, unauthorized_401 | 11.2.4.2 / 11.2.4.6 | title/url only if navigation happens | text_appeared |
| mobile_settings | simple_business_page | mobile_settings | 修改移动端设置 | toggle, save, toast | normal_network, slow_save_response, backend_business_conflict | 11.2.4.2 / 11.2.4.6 / 11.2.4.5 | no primary unless URL/title changes | toast_shown, element_enabled |
| mobile_notification | medium_business_page | mobile_notification | 查看通知列表 | list, mark read, partial refresh | normal_network, empty_result, delayed_polling_result | 11.2.4.3 / 11.2.4.6 / 11.2.4.5 | no primary unless URL/title changes | list_changed |
| mobile_infinite_scroll | medium_business_page | mobile_infinite_scroll | 滚动加载更多 | infinite scroll, loading footer | normal_network, slow_network, empty_result, rate_limited_429 | 11.2.4.3 / 11.2.4.6 / 11.2.4.5 | no primary | list_changed, loading_finished |
| mobile_pull_to_refresh | medium_business_page | mobile_pull_to_refresh | 下拉刷新列表 | pull refresh, list update | normal_network, timeout, server_error_500 | 11.2.4.3 / 11.2.4.6 / 11.2.4.5 | no primary | list_changed, loading_finished |

## Runtime Condition Matrix

运行条件是横向变体，可以叠加到 simple / medium / complex / very_complex 页面上，
不作为页面类型。M11.2 只记录 runtime evidence，recovery / retry / abort 属于 M12。

| condition_id | description | typical_visible_surface | requires_backend | recommended_phase | m12_boundary_note |
|---|---|---|---|---|---|
| normal_network | 正常响应和正常 UI 变化 | success state, result content | No | 11.2.4.2 / 11.2.4.3 / 11.2.4.4 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| slow_network | 响应变慢但最终完成 | loading, skeleton, delayed result | 11.2.4.5 for HTTP evidence | 11.2.4.2 timer / 11.2.4.5 backend | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| timeout | 等待窗口内未出现预期结果 | stuck loading, timeout note | 11.2.4.5 for HTTP evidence | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| request_cancelled | 请求被取消或中断 | cancelled state, stale result | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| frontend_validation_error | 前端校验阻止提交 | inline field error | No | 11.2.4.2 / 11.2.4.3 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| backend_validation_error | 后端校验拒绝提交 | form error, toast error | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| backend_business_conflict | 服务端业务冲突 | conflict toast, row state unchanged | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| unauthorized_401 | 未登录或登录失效 | login prompt, error banner | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| forbidden_403 | 无权限操作 | forbidden message, disabled action | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| not_found_404 | 资源不存在 | not found state | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| conflict_409 | 状态冲突或版本冲突 | conflict message, reload prompt | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| rate_limited_429 | 请求频率受限 | rate limit banner/toast | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| server_error_500 | 服务端错误 | error toast, error page region | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| empty_result | 查询结果为空 | empty state | No for timer, Yes for backend | 11.2.4.3 / 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| partial_success | 部分操作成功 | mixed status rows, partial warning | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| stuck_loading | loading 未结束 | loading overlay remains visible | No for timer, Yes for backend | 11.2.4.3 / 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| retry_available | UI 显示重试入口 | retry button shown | Yes | 11.2.4.5 | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |

## Runtime Behavior / Interaction Pattern Catalog

Runtime behavior 是页面类型下的行为变体，不是业务复杂度本身。

| interaction_id | runtime_behavior | business_page_applicability | recommended_phase | current_mvp_expected_observation | future_expected_observation | needs_backend |
|---|---|---|---|---|---|---|
| click_to_toast | click -> toast | simple / medium / complex | 11.2.4.2 | no primary unless URL/title changes | `toast_shown` | No |
| click_to_modal | click -> modal | simple / medium / complex | 11.2.4.2 | no primary | `modal_opened` | No |
| click_to_drawer | click -> drawer | medium / complex | 11.2.4.4 | no primary | drawer / modal relation | No |
| click_to_dropdown | click -> dropdown / select panel | medium / complex | 11.2.4.4 | no primary | component-generated runtime surface relation | No |
| click_to_loading_then_result | click -> loading -> result | simple / medium / complex | 11.2.4.3 / 11.2.4.5 | supporting only unless URL/title changes | `loading_finished`, `list_changed` | Optional |
| input_to_autocomplete | input -> autocomplete | medium / complex | 11.2.4.4 | no primary | component relation, list_changed | Optional |
| input_to_validation_message | input -> validation message | simple / medium / complex | 11.2.4.2 | no primary | `form_validation_message` | No |
| submit_to_delayed_success | submit -> delayed success | simple / medium / complex | 11.2.4.3 / 11.2.4.5 | title/url only if navigation happens | toast_shown, loading_finished | Optional |
| submit_to_server_validation_error | submit -> server validation error | simple / medium / complex | 11.2.4.5 | no primary unless URL/title changes | form_validation_message, toast_shown | Yes |
| button_disabled_to_enabled | button disabled -> enabled | simple / medium / complex | 11.2.4.2 | no primary | `element_enabled`, `element_disabled` | Optional |
| field_show_hide | field show/hide | complex | 11.2.4.4 | no primary | field_show_hide | No |
| mode_switch_view_edit_preview | view/edit/preview mode switch | complex | 11.2.4.4 | no primary unless title changes | mode_switch | No |
| partial_list_refresh | partial list refresh | medium / complex | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | `list_changed` | Optional |
| spa_content_update_without_url_change | SPA content update without URL change | simple / medium / complex | 11.2.4.3 | no primary | `spa_content_changed` | No |
| same_url_reload | same-url reload | simple / medium | 11.2.4.3 / future page-load package | no `page_load_finished` in current MVP | page-load evidence | Optional |
| url_changed_navigation | URL changed navigation | simple / medium / complex | 11.2.4.2 | `url_changed` primary | route-level observation | No |
| title_changed_navigation | title changed navigation | simple / medium / complex | 11.2.4.2 | `title_changed` primary | route-level observation | No |
| infinite_scroll | infinite scroll | medium / very_complex | 11.2.4.6 | no primary | `list_changed`, loading_finished | Optional |
| virtualized_list | virtualized list | complex / very_complex | later 11.2.x | no primary | component runtime semantics | Optional |
| mobile_bottom_sheet | mobile bottom sheet | complex | 11.2.4.6 | no primary | mobile bottom sheet relation | No |
| mobile_action_sheet | mobile action sheet | complex | 11.2.4.6 | no primary | mobile action sheet relation | No |
| mobile_picker | mobile picker | complex | 11.2.4.6 | no primary | mobile picker relation | No |
| mobile_toast | mobile toast | simple / medium | 11.2.4.6 | no primary unless URL/title changes | `toast_shown` | No |
| mobile_dialog | mobile dialog | simple / medium / complex | 11.2.4.6 | no primary | `modal_opened` | No |

## Network Delay and Error Scenario Catalog

真实网页运行时不只有 UI 弹层和内容变化，也包括慢响应、失败响应、服务端校验、
空结果、权限错误和异步任务失败。11.2.4 只规划这些 fixture；M11.2 记录 runtime
evidence，不实现 recovery / retry / abort。

| scenario_id | condition_type | business_page_applicability | visible_error_surface | requires_mock_backend | recommended_phase | current_mvp_expected_observation | future_expected_observation | m12_boundary_note |
|---|---|---|---|---|---|---|---|---|
| slow_search_response | network_delay | simple_search / list / search_filter | loading then result | Yes for HTTP evidence | 11.2.4.5 | supporting only unless URL/title changes | loading_finished, list_changed | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| slow_save_response | network_delay | settings / form / detail action | disabled submit, loading, toast | Yes | 11.2.4.5 | supporting only unless URL/title changes | loading_finished, toast_shown | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| slow_detail_loading | network_delay | detail / dashboard | skeleton then detail | Yes | 11.2.4.5 | supporting only unless URL/title changes | loading_finished, text_appeared | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| slow_export_preparation | network_delay | export_download | preparing state, artifact link | Yes | 11.2.4.5 | supporting only unless URL/title changes | loading_finished, artifact evidence | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| delayed_polling_result | async_delay | notification / async job / dashboard | pending -> completed | Yes | 11.2.4.5 | no primary unless URL/title changes | list_changed, server_push_update | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| delayed_async_job_completion | async_delay | export / import / batch operation | job status changes | Yes | 11.2.4.5 | no primary unless URL/title changes | loading_finished, list_changed | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_400_validation_error | api_error | forms | form item error | Yes | 11.2.4.5 | no primary | form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_401_unauthorized | api_error | login-gated pages | login prompt / unauthorized banner | Yes | 11.2.4.5 | title/url only if navigation happens | toast_shown, form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_403_forbidden | api_error | role / permission pages | forbidden banner / disabled action | Yes | 11.2.4.5 | no primary unless URL/title changes | element_disabled, toast_shown | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_404_missing_resource | api_error | detail pages | not found state | Yes | 11.2.4.5 | title/url only if navigation happens | text_appeared, loading_finished | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_409_conflict | api_error | edit / approval / order | conflict message | Yes | 11.2.4.5 | no primary | toast_shown, form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_429_rate_limited | api_error | search / submit / export | rate limit banner | Yes | 11.2.4.5 | no primary | toast_shown, banner alert | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| http_500_server_error | api_error | any backend page | error toast / alert | Yes | 11.2.4.5 | no primary | toast_shown, banner alert | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| network_timeout | network_error | search / save / detail | stuck loading / timeout surface | Yes | 11.2.4.5 | timeout wait outcome only | loading_finished absent, timeout evidence | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| request_cancelled | network_error | search / save / detail | stale state or cancelled message | Yes | 11.2.4.5 | no primary | toast_shown, uncertainty note | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| inline_validation_message | ui_error_surface | forms | inline field text | No | 11.2.4.2 | no primary | form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| form_item_error_message | ui_error_surface | forms | form item error | No | 11.2.4.2 | no primary | form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| toast_error | ui_error_surface | any submit action | error toast | No | 11.2.4.2 | no primary | toast_shown | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| modal_error | ui_error_surface | detail / form / confirm | modal with error | No | 11.2.4.2 | no primary | modal_opened | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| banner_alert_error | ui_error_surface | list / detail / dashboard | banner alert | No | 11.2.4.3 | no primary | text_appeared, banner alert | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| empty_result_state | ui_error_surface | search / list | empty state | Optional | 11.2.4.3 / 11.2.4.5 | no primary unless URL/title changes | list_changed, text_appeared | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| retry_button_shown | ui_error_surface | async / backend pages | retry button | Yes | 11.2.4.5 | no primary | element_appeared, element_enabled | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| disabled_submit_after_error | ui_error_surface | forms | disabled submit | Optional | 11.2.4.2 / 11.2.4.5 | no primary | element_disabled | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| loading_overlay_stuck_then_timeout | timeout_surface | async pages | loading overlay remains | Optional | 11.2.4.3 / 11.2.4.5 | timeout wait outcome only | loading_finished absent, timeout evidence | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| upload_progress_then_failure | file_error | file_upload | progress then failure message | Yes | 11.2.4.5 | no primary | loading_finished, toast_shown | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| upload_file_type_rejected | file_error | file_upload | file type error | Optional | 11.2.4.3 / 11.2.4.5 | no primary | form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| upload_size_exceeded | file_error | file_upload | size error | Optional | 11.2.4.3 / 11.2.4.5 | no primary | form_validation_message | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| export_generation_failed | file_error | export_download | export failure message | Yes | 11.2.4.5 | no primary | toast_shown, loading_finished absent | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |
| download_unavailable | file_error | export_download | unavailable artifact | Yes | 11.2.4.5 | no primary | toast_shown, artifact evidence | M11.2 records runtime evidence only. Recovery / retry / abort belongs to M12. |

## Complexity Ladder

Complexity ladder 按业务复杂度整理，不按单个 UI 技术行为整理。

### simple

页面类型：

- login。
- register。
- sms_login。
- forgot_password。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

可叠加 runtime behavior：

- validation message。
- toast。
- loading。
- url/title navigation。

可叠加 conditions：

- normal_network。
- slow_network。
- frontend_validation_error。
- backend_validation_error。
- server_error_500。
- unauthorized_401。

### medium

页面类型：

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

可叠加 runtime behavior：

- partial list refresh。
- pagination。
- sorting。
- filtering。
- empty result。
- upload progress。
- export preparation。
- modal/drawer simple edit。

可叠加 conditions：

- slow_search_response。
- empty_result。
- backend_business_conflict。
- rate_limited_429。
- upload failure。
- export failure。

### complex

页面类型：

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

可叠加 runtime behavior：

- field show/hide。
- step transition。
- mode switch。
- nested modal/drawer。
- partial success。
- server validation + retry input。
- permission-dependent UI。

可叠加 conditions：

- backend_validation_error。
- conflict_409。
- partial_success。
- forbidden_403。
- stuck_loading。
- retry_available。

### very_complex

页面类型：

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

处理方式：

- 记录为 future scenario。
- 当前不进入 11.2.4.1 - 11.2.4.5 的近期实现。
- 后续需要单独拆包设计。

## Fixture Phase Mapping

### 11.2.4.1 · Single-page Runtime Fixture Shell

只建立 runtime observation fixture index、route shell、category navigation、
reset convention 和 stable anchor convention。不实现具体业务页面。

### 11.2.4.2 · Single-page Basic Business Pages

实现 simple business pages 的单页面前端 fixture：

- login。
- register。
- sms_login。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

可以使用 deterministic frontend timer 模拟 loading、validation、visible error surface
和 empty state。

### 11.2.4.3 · Single-page Medium Business Pages

实现 medium business pages 的单页面前端 fixture：

- user_list。
- order_list。
- product_list。
- table_management。
- create_edit_form。
- file_upload。
- export_download。

先用本地前端状态模拟，不接真实 mock backend。

### 11.2.4.4 · Single-page Complex Business Pages

实现 complex 单页面业务：

- dynamic_form。
- wizard_stepper。
- batch_operation。
- master_detail。
- view_edit_preview_mode_switch。
- permission_conditional_ui。
- conditional_fields。

### 11.2.4.5 · Mock Backend Runtime Conditions

引入 mock backend：

- slow response。
- backend validation。
- 401 / 403 / 404 / 409 / 429 / 500。
- timeout。
- polling。
- upload / export failure。
- async job completion。

### 11.2.4.6 · Mobile Single-page Patterns

实现移动端单页面：

- mobile_login_sms。
- mobile_search。
- mobile_list。
- mobile_form。
- mobile_picker。
- mobile_action_sheet。
- mobile_pull_to_refresh。
- mobile_infinite_scroll。

### 11.2.4.7 · E2E Evidence and Review

补充 scoped E2E 和 evidence closure。

## Current MVP vs Future Observation Boundary

当前 11.2.2 / 11.2.3 已支持：

```text
url_changed
title_changed
network_idle_observed supporting only
wait_result
observation_summary
```

当前不支持但纳入规划：

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

文档不得把 future signals 写成当前已实现。

## 场景目录

### 点击后出现 Modal（Modal After Click）

- 场景名称（case name）：modal after click。
- 场景（scenario）：点击某个操作后打开确认、详情或表单 modal。
- 价值（why it matters）：如果下一步必需 UI 在 modal 内，replay 不能把 click
  完成误判为业务任务完成。
- M11.2 预期观察（expected observation）：记录 modal 出现、title / role /
  visible text，以及预期 modal 是否在点击后变为可见。
- 不在范围（not in scope）：modal 未出现时选择 recovery path。
- 后续 M12 含义（future M12 implication）：modal 缺失或出现非预期 modal，
  后续可能进入 recovery 或 takeover 决策。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  scenario catalog / fixture planning。

### 提交后出现 Toast（Toast After Submit）

- 场景名称（case name）：toast after submit。
- 场景（scenario）：提交表单后显示短暂的 success、warning 或 error toast。
- 价值（why it matters）：toast 可能是唯一结果信号，而且可能在 result reporting
  读取最终状态前消失。
- M11.2 预期观察（expected observation）：记录 toast 出现、可见 severity、文本内容，
  以及可观察到的消失时间。
- 不在范围（not in scope）：判断 error toast 是否应该触发 retry。
- 后续 M12 含义（future M12 implication）：error toast 或 missing toast 后续
  可能需要 recovery dialogue。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.5
  observation evidence into Task Result Reporter。

### 按钮延迟变为可用（Delayed Button Enabled）

- 场景名称（case name）：delayed button enabled。
- 场景（scenario）：按钮在 validation、async permission check 或 network data
  完成前保持 disabled。
- 价值（why it matters）：如果不能观察 enabled 状态变化，replay 可能过早点击。
- M11.2 预期观察（expected observation）：记录 disabled -> enabled transition、
  目标元素 identity，以及 timeout / not-observed 状态。
- 不在范围（not in scope）：重试点击或要求用户修复输入。
- 后续 M12 含义（future M12 implication）：按钮一直未 enabled 后续可能成为
  blocked execution 或 recovery prompt。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.2
  wait-for-change MVP。

### 网络延迟后的搜索结果（Search Result After Network Delay）

- 场景名称（case name）：search result after network delay。
- 场景（scenario）：输入搜索词或点击 Search 后，结果行在延迟的网络请求完成后更新。
- 价值（why it matters）：立即读取结果可能读到旧行。
- M11.2 预期观察（expected observation）：记录 loading transition、row count /
  empty state change、可见结果文本，以及 action 后内容是否发生变化。
- 不在范围（not in scope）：修改搜索词或 retry 请求。
- 后续 M12 含义（future M12 implication）：timeout 或结果未变化后续可能需要
  用户选择或 recovery。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  scenario catalog / fixture planning。

### 局部列表刷新（Partial List Refresh）

- 场景名称（case name）：partial list refresh。
- 场景（scenario）：URL 和页面 shell 不变，只有 table、list 或 card region 刷新。
- 价值（why it matters）：很多 SPA 和 dashboard flow 不能只靠 page-level
  navigation signals。
- M11.2 预期观察（expected observation）：记录 region-level content mutation、
  row count change、updated item text，以及 stale-vs-new evidence。
- 不在范围（not in scope）：从任意 list content 判断业务正确性。
- 后续 M12 含义（future M12 implication）：没有刷新或刷新了错误 region，后续
  可能变成 blocked / needs-review state。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.3
  replay integration with observation。

### URL 不变的 SPA 内容更新（SPA Content Update Without URL Change）

- 场景名称（case name）：SPA content update without URL change。
- 场景（scenario）：route-like state change 替换 main content，但浏览器 URL 不变。
- 价值（why it matters）：只等待 URL 会漏掉客户端状态切换。
- M11.2 预期观察（expected observation）：记录不依赖 URL 变化的 title、heading、
  landmark、visible text 或 main-region change。
- 不在范围（not in scope）：实现完整 SPA router 语义。
- 后续 M12 含义（future M12 implication）：预期内容一直不出现，后续可能需要
  explanation 或 takeover。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.3 replay
  integration with observation。

### 动作后延迟完整页面刷新（Delayed Full Page Reload After Action）

- 场景名称（case name）：delayed full page reload after action。
- 场景（scenario）：用户点击提交、保存、跳转或确认按钮后，页面触发完整
  document reload。URL 可能变化，也可能保持不变。刷新完成前，新内容不会立即出现。
- 价值（why it matters）：replay 不能在点击后立即判断结果，否则会误判页面尚未
  稳定。same-url reload 也不能只靠 URL 变化判断。
- M11.2 预期观察（expected observation）：记录 `page_load_started` 和
  `page_load_finished`；可选记录 `url_changed`、`title_changed`、
  `text_appeared`、`network_idle_observed`。
- 不在范围（not in scope）：不判断刷新失败后是否 retry，不处理 timeout
  recovery，不自动 abort。
- 后续 M12 含义（future M12 implication）：如果 page load 长时间未完成，M12
  可基于 observation evidence 决定是否提出 retry / recovery / user takeover。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.2
  wait-for-change MVP / 11.2.3 replay integration。

### 校验错误信息（Validation Error Message）

- 场景名称（case name）：validation error message。
- 场景（scenario）：表单提交或字段 blur 后显示 inline validation errors。
- 价值（why it matters）：replay 可能机械完成，但实际任务被 validation 拒绝。
- M11.2 预期观察（expected observation）：记录可见 validation message、可观察到的
  field association 和 error text。
- 不在范围（not in scope）：修复 input values 或重新绑定 slots。
- 后续 M12 含义（future M12 implication）：validation failure 后续可能路由到
  recovery、用户澄清或教学阶段。
- 后续执行包（future package）：11.2.5 observation evidence into Task Result
  Reporter / 11.2.7 runtime observation tests and evidence。

### 骨架屏后出现内容（Loading Skeleton Then Content）

- 场景名称（case name）：loading skeleton then content。
- 场景（scenario）：skeleton、spinner 或 placeholder 被真实内容替换。
- 价值（why it matters）：skeleton 仍可见时读取页面，可能产生 false uncertainty
  或 stale evidence。
- M11.2 预期观察（expected observation）：记录 skeleton / loading presence、
  disappearance，以及后续 content appearance。
- 不在范围（not in scope）：内容一直不加载时选择 fallback action。
- 后续 M12 含义（future M12 implication）：loading 持续存在后续可能成为 blocked
  或 recovery dialogue。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  scenario catalog / fixture planning。

### 延迟出现的 Popup（Delayed Popup）

- 场景名称（case name）：delayed popup。
- 场景（scenario）：popup、dropdown、date picker、cascader 或 menu 在延迟 click
  或 hover-related UI update 后出现。
- 价值（why it matters）：如果 replay 预期 popup 立即可见，就可能漏掉
  popup-based controls。
- M11.2 预期观察（expected observation）：记录 popup visibility、可观察到的
  anchor relation，以及 option text / role signals。
- 不在范围（not in scope）：实现新的 popup control operation logic。
- 后续 M12 含义（future M12 implication）：popup 缺失后续可能需要 takeover 或
  teaching。
- 后续执行包（future package）：11.2.2 wait-for-change MVP / 11.2.4 realistic
  scenario catalog / fixture planning。

### 组件库交互后生成运行时界面片段（Component-generated Runtime Surface After Interaction）

- 场景名称（case name）：component-generated runtime surface after interaction。
- 场景（scenario）：用户点击、聚焦、选择或输入后，常用组件库生成新的运行时
  界面片段。该片段可能插入到 `body`、当前元素内部、兄弟节点、portal / teleport
  容器，或只表现为 class / aria / selected / disabled / active 状态变化。
- 价值（why it matters）：replay 不能只依赖 URL / title / 原节点子树变化。真实
  组件库经常把 option panel、picker、toast、modal、drawer、action sheet、
  validation message 等渲染到触发元素之外。
- M11.2 预期观察（expected observation）：记录 `element_appeared`、
  `element_disappeared`、`modal_opened`、`modal_closed`、`toast_shown`、
  `loading_finished`、`element_enabled`、`element_disabled`、
  `form_validation_message`、`list_changed`，以及 future component relation
  evidence。
- 关联提示（relation hints）：action timing、aria-expanded / aria-controls /
  aria-owns、role=listbox / option / menu / dialog、focus movement、active
  descendant、bounding rect proximity、component class pattern as supporting
  evidence。
- PC 组件库示例（PC component examples）：Ant Design、Element Plus、Naive UI、
  Arco Design、TDesign、MUI / Material-ish、Bootstrap-style components。
- 移动端组件库示例（mobile component examples）：Ant Design Mobile、Vant、NutUI、
  Varlet、Ionic、Framework7-style mobile components。
- 不在范围（not in scope）：不在 11.2.2 MVP 中完整实现组件库行为识别；不调用
  LLM 判断 popup / panel 归属；不让 Agent 进入 per-step execution loop；不把
  组件库 class 作为唯一依据。
- 后续 M12 含义（future M12 implication）：组件库界面片段缺失、状态未变化或
  关联不确定时，后续可成为 result reporter uncertainty 或 M12 recovery / takeover
  的输入，但 M11.2 不做决策。
- 后续执行包（future package）：later 11.2.x Common Component Runtime Semantics /
  11.2.4 realistic scenario catalog / fixture planning / 11.2.5 reporter evidence
  integration。

### 服务端推送消息（Server Push Message）

- 场景名称（case name）：server push message。
- 场景（scenario）：backend event 在没有用户动作的情况下向页面推送新
  notification、message 或 status。
- 价值（why it matters）：页面独立变化可能改变 replay result evidence。
- M11.2 预期观察（expected observation）：记录 passive message appearance、可见
  timestamp、visible text 和 affected region。
- 不在范围（not in scope）：决定是否 interrupt 当前 execution。
- 后续 M12 含义（future M12 implication）：passive changes 后续可能需要
  v0.2 / M12 的 interruption 或 recovery handling。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.3
  replay integration with observation。

### WebSocket / SSE / Polling 更新

- 场景名称（case name）：WebSocket / SSE / polling update。
- 场景（scenario）：live transport 或 polling 更新 task status、list content
  或 counters。
- 价值（why it matters）：runtime evidence 可能在 replay action 之后、普通
  navigation 或 click completion 之外到达。
- M11.2 预期观察（expected observation）：记录 live update 造成的 DOM / text
  changes；11.2.0 不要求 transport-level interception。
- 不在范围（not in scope）：实现 WebSocket、SSE 或 polling protocol inspection。
- 后续 M12 含义（future M12 implication）：live failure status 后续可能需要
  recovery 或 abort dialogue。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.5
  observation evidence into Task Result Reporter。

### 被动 DOM 变化（Passive DOM Mutation）

- 场景名称（case name）：passive DOM mutation。
- 场景（scenario）：ads、personalization、timer、counter、banner 或 background
  scripts 在没有直接用户动作的情况下改变 DOM。
- 价值（why it matters）：不是每个 DOM mutation 都应该被当成 task evidence。
- M11.2 预期观察（expected observation）：记录 passive mutation category、
  affected region，以及它是否可能和当前 replay / result boundary 有关。
- 不在范围（not in scope）：完整 relevance classification 或 recovery policy。
- 后续 M12 含义（future M12 implication）：相关 passive mutation 后续可能驱动
  interruption 或 user-choice flows。
- 后续执行包（future package）：11.2.1 observation signal contract / 11.2.6
  Codex realistic web QA。
