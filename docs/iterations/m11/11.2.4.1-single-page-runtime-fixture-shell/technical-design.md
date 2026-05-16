# 技术设计（Technical Design）

状态：implemented

## 当前状态（Current State）

- `apps/validation-site/src/pages/IndexPage.vue` 已有 `PAGES` catalog 和页面卡片。
- 当前已有 `/login` 和 `/users` 页面入口。
- 当前没有 `/runtime-observation` 专用入口。
- 当前没有 runtime observation fixture shell。
- 11.2.4.0 已完成业务页面复杂度 catalog。
- 11.2.4.1 实现 shell，但不实现具体业务页面。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| 不重写现有 IndexPage 架构 | 仅在 `PAGES` catalog 增加 Runtime Observation 分类入口 | route smoke / component test | 保留 `/login`、`/users` |
| route namespace 完整 | 使用 `/runtime-observation/*` 命名空间 | route smoke | 不创建 `/medium` 这类全局 route |
| fixture metadata 与 11.2.4.0 catalog 对齐 | card metadata 使用 `business_complexity`、`runtime_conditions`、`runtime_behaviors` | component test | 不按 toast/modal/loading 定义业务复杂度 |
| current MVP / future signal label 分离 | UI label 分成 current signals、evidence capabilities、future labels | component test / review | future labels 不得写成 implemented |
| stable anchors 约定 | 后续 fixture 页面提供 heading、trigger、result、reset、status anchors | route smoke / E2E | 本轮只定义，不实现 |
| reset convention 约定 | 后续每个 fixture 提供 deterministic reset | component test / E2E | reset 不是 recovery |
| PC 优先 | 11.2.4.1 - 11.2.4.5 优先 PC fixture | review | mobile 仅预留分类 |
| 不依赖外部网站 | shell metadata 静态展示，自建 fixture 规划 | boundary test | 不使用线上网站作为验证依赖 |
| 不接 reporter / M12 | shell 不调用 reporter，不做 recovery / retry / abort | boundary test | 只服务 fixture navigation |

## 实现方案（Proposed Implementation）

实现阶段建议新增：

```text
apps/validation-site/src/pages/runtime-observation/
apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue
apps/validation-site/src/pages/runtime-observation/RuntimeObservationShell.vue
```

实现应：

1. 读取 `apps/validation-site/src/pages/IndexPage.vue` 的当前 `PAGES` catalog。
2. 在 `PAGES` catalog 中新增 Runtime Observation 分类入口。
3. 新增 `/runtime-observation` route。
4. 新增 runtime observation index 页面。
5. 展示后续 fixture categories：
   - Basic Business Pages。
   - Medium Business Pages。
   - Complex Business Pages。
   - Mobile Single-page Patterns。
   - Mock Backend Runtime Conditions。
6. 每个 category 展示 planned fixture cards。
7. 每张 card 展示 business complexity、platform、phase、current MVP expected observation、
   future expected observation 和 status。
8. 展示统一 reset convention。
9. 展示 stable anchor convention。

11.2.4.1 实现阶段执行上述 shell 代码改动，但不实现具体业务 fixture。

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| `apps/validation-site/src/pages/IndexPage.vue` | Yes | 增加 Runtime Observation catalog entry | 不重写首页架构 |
| validation-site route config | Yes | 新增 `/runtime-observation` namespace | 保留现有 routes |
| runtime observation fixture index page | Yes | 新增 shell index 页面 | 不实现具体业务 fixture |
| validation-site specs | No | 本轮不改；后续可新增 runtime-observation specs | 不影响现有 specs |
| E2E tests | No | 本轮不新增 | 后续实现后再补 |
| API routes | No | 不新增 API | N/A |
| DB schema | No | 不新增 migration | N/A |
| CLI | No | 不改 CLI | N/A |
| Console UI | No | 不改 console | N/A |
| Replay execution | No | 不接 replay | N/A |
| Task Result Reporter | No | 不接 reporter | N/A |
| Docs | Yes | 新增 11.2.4.1 文档包 | 文档级变更 |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No runtime schema changes.

Shell 可以使用静态 frontend metadata，但不创建共享 TypeScript schema 文件。
Metadata fields must follow `contract.md`:

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

## 服务 / 模块设计（Service / Module Design）

No backend service changes.

Frontend module responsibility:

- `RuntimeObservationIndex.vue`：展示 shell index、category navigation 和 fixture cards。
- `RuntimeObservationShell.vue`：可选共享 shell layout，承载 reset / stable anchor convention。
- Existing `IndexPage.vue`：只新增入口 card，不改变既有 card rendering contract。

## 数据流（Data Flow）

Shell 静态数据流：

```text
IndexPage PAGES catalog
-> /runtime-observation entry
-> RuntimeObservationIndex
-> category cards
-> future fixture links
```

11.2.4.1 shell 不接 replay runtime，不读取 `wait_result`，不读取
`observation_summary`，不调用 API，只提供 fixture navigation metadata。

## PC Priority

PC fixtures are prioritized for 11.2.4.1 - 11.2.4.5.

Mobile fixture category is planned in the shell but not prioritized until 11.2.4.6.

移动端分类可以在 shell 中预留，但移动端具体 fixture 后移到 11.2.4.6。

## 状态推导（Status / State Derivation）

Shell card `status` does not derive runtime success.

Allowed fixture card status values:

- `planned`
- `implemented`
- `tested`
- `deferred`

`tested` requires future reviewable evidence. This documentation package must not mark any future
fixture card as `implemented` or `tested`.

## 兼容性（Compatibility）

实现必须：

- 不破坏现有 `/` 首页。
- 不删除 `/login`、`/users`。
- 不改变已有 specs。
- 不改变 workbench deep link 逻辑。
- 不改变 API。
- 不改变 replay。
- 不改变 reporter。

## 失败 / 边界情况（Failure / Edge Cases）

- validation-site 当前 router 结构和 test command 需要后续实现前确认。
- Future labels may render in the shell, but must be marked as future / planned.
- Missing future fixture route should not be linked as an implemented route.
- Reset convention is descriptive until concrete fixture pages exist.
- Stable anchor convention is descriptive until concrete fixture pages exist.

## 非目标（Non-goals）

- 不实现具体业务 fixture。
- 不实现 mock backend。
- 不新增 tests。
- 不运行 E2E / UI smoke / `verify-scenario` / autonomous run。
- 不接 replay / reporter / M12。

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Documentation validation | 文档包完整，shell contract 存在 | `test-plan.md` |
| Future component tests | category cards、fixture metadata、future labels | `test-plan.md` |
| Future route smoke | `/runtime-observation` 可打开且首页入口存在 | `test-plan.md` |
| Boundary tests | 不调用 API / replay / reporter / autonomous run | `test-plan.md` |

## 验证命令入口（Validation Commands）

实现后运行 scoped validation：

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```
