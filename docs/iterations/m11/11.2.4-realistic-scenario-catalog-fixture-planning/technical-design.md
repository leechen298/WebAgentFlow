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

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| scenario catalog 不改变产品模型 | 只在 M11.2 文档中规划 fixture，不修改 product model。 | documentation validation | 不新增 Agent / lifecycle。 |
| fixture 不依赖外部网站 | 后续 fixture 放在 validation-site 和 mock backend。 | future fixture smoke | 外部网站只可作为研究参考，不作为验证依赖。 |
| fixture 必须 deterministic | 每个 fixture 记录 initial state、trigger、reset behavior。 | future route smoke | Phase 1 可用固定 timer。 |
| fixture 可 reset | 每个 fixture contract 包含 reset behavior。 | future route smoke | 避免状态污染。 |
| fixture 不接 reporter | 11.2.4 只规划 runtime observation fixture。 | boundary tests | 11.2.5 才接 reporter。 |
| fixture 不触发 recovery | M11.2 只记录 evidence。 | boundary tests | M12 才做 retry / abort。 |
| 区分 current MVP vs future expected observation | scenario / fixture 均包含 current MVP limit 和 future signal support。 | documentation validation | 防止误称已实现。 |
| PC / mobile 都纳入规划 | catalog 分 PC / mobile 页面类型。 | documentation validation | 不只覆盖管理后台。 |
| simple -> very complex 分阶段 | catalog 使用 complexity ladder。 | documentation validation | Phase 1 只做单页面。 |
| 前端 timer 不代表 network evidence | Phase 1 timer 只用于 deterministic UI state；Phase 2 mock backend 才覆盖 HTTP evidence。 | future fixture tests | 防止误读 slow response。 |

## 实现方案（Proposed Fixture Architecture）

本轮不实现代码。后续实现可采用以下结构：

```text
apps/validation-site/src/pages/runtime-observation/
apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue
apps/validation-site/src/pages/runtime-observation/SinglePageBasic.vue
apps/validation-site/src/pages/runtime-observation/SinglePageAsync.vue
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
| validation API mock backend | Planned | Phase 2 后续实现 mock API。 | 本轮不改源码。 |
| E2E tests | Planned | 后续补 scoped E2E。 | 本轮不新增测试。 |
| API routes | No | 不新增运行时 API route。 | N/A |
| DB schema | No | 不修改 DB schema。 | N/A |
| CLI | No | 不修改 CLI。 | N/A |
| Console UI | No | 不修改 Console UI。 | N/A |
| Replay execution | No | 不修改 replay runtime。 | N/A |
| Task Result Reporter | No | 不接 reporter。 | 11.2.5 |
| M12 recovery | No | 不做 retry / abort。 | M12 |
| Docs | Yes | 新增 11.2.4 文档包。 | planning only |

## Phase 1 · Single-page Fixtures

Phase 1 聚焦单页面，使用前端本地状态和确定性 timer 模拟 runtime behavior。

Phase 1 不要求真实后端调用。前端 timer 模拟 delay / loading / error surface 只用于
deterministic fixture，不代表真实 network evidence。

| Fixture | Route | Initial state | User action | Runtime behavior | Visible result | Current MVP expected | Future expected |
|---|---|---|---|---|---|---|---|
| single-page-toast | `/runtime-observation/basic#toast` | no toast | click submit | toast appears then disappears | success / error toast | no primary unless URL/title changes | `toast_shown` |
| single-page-modal | `/runtime-observation/basic#modal` | modal closed | click open | modal/dialog visible | dialog with title/actions | no primary | `modal_opened` |
| single-page-loading | `/runtime-observation/async#loading` | content hidden | click load | skeleton -> content | content replaces loading | maybe supporting only | `loading_finished` |
| single-page-delayed-button | `/runtime-observation/basic#delayed-button` | submit disabled | fill / timer | disabled -> enabled | button enabled | no primary | `element_enabled` |
| single-page-search-refresh | `/runtime-observation/async#search` | old rows | click search | list region changes | new rows / empty state | no primary | `list_changed` |
| single-page-spa-update | `/runtime-observation/basic#spa-update` | panel A | click tab | content changes without URL | panel B content | no primary | `spa_content_changed` |
| single-page-validation-message | `/runtime-observation/basic#validation` | empty form | blur / submit | validation message appears | inline error | no primary | `form_validation_message` |
| single-page-same-url-reload | `/runtime-observation/async#same-url-reload` | revision A | click refresh | simulated document-like refresh | revision B | no `page_load_finished` in current MVP | future page-load evidence |
| single-page-component-surface | `/runtime-observation/basic#component-surface` | dropdown closed | click select | panel rendered outside trigger | option panel visible | no primary | component relation |
| single-page-mobile-picker | `/runtime-observation/mobile#picker` | picker closed | tap picker | mobile picker surface appears | picker wheel / options | no primary | mobile picker relation |
| single-page-mobile-action-sheet | `/runtime-observation/mobile#action-sheet` | sheet closed | tap action | bottom sheet appears | action list | no primary | action sheet relation |

每个 Phase 1 fixture 需要：

- stable heading。
- stable trigger selector。
- stable result region。
- reset button。
- deterministic timer duration。
- visible state label。

## Phase 2 · Mock Backend Runtime Fixtures

Phase 2 引入 mock backend 行为。它负责 HTTP 层 slow response、error status code、
polling、upload、export 和 async job completion。

计划 mock endpoints：

- mock search API。
- mock save API。
- mock validation API。
- mock async job API。
- mock polling endpoint。
- mock upload endpoint。
- mock export endpoint。

Phase 2 覆盖：

- slow search response。
- slow save response。
- slow detail loading。
- server validation error。
- 401 / 403 / 404 / 409 / 429 / 500。
- network timeout。
- request cancelled / aborted。
- polling result update。
- async job completion / failure。
- upload progress then failure。
- export generation failed。
- download unavailable。

## Phase 3 · Component-library-heavy Fixtures

Phase 3 覆盖复杂组件库行为：

- select option panel。
- autocomplete。
- cascader。
- date picker。
- time picker。
- drawer。
- bottom sheet。
- virtualized list。
- nested modal。
- portal / teleport runtime surface。

这些场景可作为 later 11.2.x Common Component Runtime Semantics 的输入。

## Phase 4 · Multi-page / Workflow Fixtures

Phase 4 再规划跨页面 workflow：

- list -> detail。
- create -> edit -> save。
- search -> select -> export。
- wizard / stepper。
- multi-page approval flow。

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
complexity
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
- single-page basic fixtures：toast、modal、validation、enabled state、component surface。
- single-page async fixtures：loading、search refresh、same-url reload、empty state。
- mobile pattern fixtures：picker、action sheet、bottom sheet、mobile toast。
- validation API mock backend：slow response、error status、polling、upload、export。
- E2E specs：验证 fixture determinism 和 observation boundary。

## 数据流（Data Flow）

后续 Phase 1 数据流：

```text
open fixture route
-> deterministic initial state
-> user / replay trigger action
-> frontend local timer updates visible state
-> wait_result / observation_summary observe current MVP signals or remain conservative
-> reset restores initial state
```

后续 Phase 2 数据流：

```text
open fixture route
-> trigger action
-> frontend calls mock API
-> mock backend returns slow response / error / polling result / artifact status
-> frontend renders visible state
-> wait_result / observation_summary record supported evidence
```

Phase 1 timer-based flow is deterministic UI evidence only. Phase 2 mock backend
flow is the first phase that can produce HTTP-layer slow response / error status evidence.

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

Simple:

- toast。
- modal。
- validation message。
- button enabled / disabled。
- URL changed。
- title changed。

Medium:

- loading skeleton -> content。
- search result refresh。
- partial list refresh。
- same-url reload。
- SPA content update。
- autocomplete。
- select panel。
- mobile picker。

Complex:

- virtualized list。
- portal / teleport runtime surface。
- nested modal / drawer。
- async job completion。
- polling update。
- server validation + retry input。
- file upload progress。
- export / download artifact。

Very Complex:

- multi-step wizard。
- multi-page workflow。
- role / permission dependent UI。
- real-time push。
- WebSocket / SSE。
- cross-page state。
- component library runtime relation resolver。
- mobile gesture / scroll / picker interaction。

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
