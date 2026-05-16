# 技术设计（Technical Design）

状态：redesign required

## 当前状态（Current State）

- 11.2.4.1 已实现 runtime observation shell、category navigation 和 route namespace。
- 11.2.4.2 当前代码已实现 7 个 `/runtime-observation/basic/*` routes，并通过 build 级验证。
- 人工 review 否决当前 basic fixtures：页面业务密度不足，更像 toy UI demo。
- 当前实现不作为最终验收标准；后续重做必须以 `fixture-designs/*.md` 为 source of truth。
- validation-site 当前没有 mock backend dependency。
- validation-site 当前 package 有 `build` script，没有独立 `test` script。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| production-like basic fixtures | 每个页面按 fixture design doc 实现完整页面结构 | future route smoke / review | business-simple, not UI-minimal |
| page-level design first | 代码重做前读取 7 个 `fixture-designs/*.md` | review | design docs 是 source of truth |
| basic pages only | 只重做 `/runtime-observation/basic/*` routes | build / route review | 不加 medium / complex / mobile |
| deterministic frontend state | 前端本地 state + deterministic timer | build / future route smoke | 不代表真实 network evidence |
| local error scope only | 只做本地校验 / deterministic business failure | route smoke / review | 不模拟真实 HTTP failure |
| stable anchors | 每页提供 heading、primary trigger、secondary trigger、result、reset、status anchors | future route smoke | anchors 必须稳定 |
| reset convention | 每页 reset 回 initial state，并清 pending timer / countdown / confirm surface | future route smoke | reset 不是 recovery |
| current/future boundary | UI 文案区分 current MVP signals 与 future labels | review | future signals 不写成 implemented |
| no backend dependency | 不调用 API，不新增 mock backend | build / review | 11.2.4.5 才接 mock backend |
| no reporter / M12 | 不调用 reporter，不做 retry / abort / recovery | review | 仅 fixture 页面 |
| shell compatibility | 保留 `/runtime-observation` shell 和 basic links | build / review | 不重写 shell 架构 |

## 影响面（Affected Surfaces）

| Surface | Changed? in redesign docs | Future implementation impact | Compatibility notes |
|---|---|---|---|
| `fixture-designs/*.md` | Yes | 作为页面实现 source of truth | 新增文档 |
| `apps/validation-site/src/pages/runtime-observation/basic/*` | No in this docs pass | 重做 richer business fixture 页面 / 组件 | 保留 route namespace |
| validation-site router | No in this docs pass | 可能保留现有 routes | 不新增全局 basic routes |
| validation-site index `/` | No | 通常不需要改首页 | 已有 Runtime Observation 入口 |
| validation-site i18n | No in this docs pass | 未来需要同步 en / zh / ja labels | 不强制本轮 |
| validation-site specs | No | 可后续补 route smoke/spec | 不跑 E2E 假通过 |
| API routes | No | 不新增 API | N/A |
| DB schema | No | 不新增 migration | N/A |
| Replay / wait service | No | 不改 observation runtime | N/A |
| Task Result Reporter | No | 不接 reporter | N/A |
| E2E tests | No | 11.2.4.7 | 本轮不运行 |

## Recommended Future Implementation Structure

当前单个 `BasicBusinessFixturePage.vue` 可以保留，但必须支持更丰富的页面结构。如果继续把全部页面逻辑塞进
一个巨大组件，会降低可读性和后续维护质量。

推荐方案：

```text
apps/validation-site/src/pages/runtime-observation/basic/
apps/validation-site/src/pages/runtime-observation/basic/BasicBusinessFixtureShell.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicLoginFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicRegisterFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicSmsLoginFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicSearchFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicDetailFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicSettingsFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/fixtures/BasicConfirmFixture.vue
apps/validation-site/src/pages/runtime-observation/basic/basicFixtures.ts
```

Design intent:

- shared shell handles fixture header, metadata, reset hook, current/future labels, and layout。
- per-fixture components own their local fields, local validation, local success/error surfaces, and page anatomy。
- shared utilities may manage deterministic timers so reset behavior is consistent。
- existing route namespace stays unchanged。

Alternative:

- one `BasicBusinessFixturePage.vue` with per-fixture sections is acceptable only if each section remains readable and each
  page-level design requirement is explicitly represented.

## Fixture Design Source of Truth

Future implementation must satisfy these documents:

| Fixture | Design doc | Route |
|---|---|---|
| login | `fixture-designs/basic-login.md` | `/runtime-observation/basic/login` |
| register | `fixture-designs/basic-register.md` | `/runtime-observation/basic/register` |
| sms_login | `fixture-designs/basic-sms-login.md` | `/runtime-observation/basic/sms-login` |
| simple_search | `fixture-designs/basic-search.md` | `/runtime-observation/basic/search` |
| simple_detail | `fixture-designs/basic-detail.md` | `/runtime-observation/basic/detail` |
| simple_settings | `fixture-designs/basic-settings.md` | `/runtime-observation/basic/settings` |
| simple_confirm | `fixture-designs/basic-confirm.md` | `/runtime-observation/basic/confirm` |

## Stable Anchor Design

Every fixture page should expose:

```text
data-testid="basic-fixture-heading"
data-testid="basic-fixture-primary-trigger"
data-testid="basic-fixture-secondary-trigger"
data-testid="basic-fixture-result"
data-testid="basic-fixture-status"
data-testid="basic-fixture-reset"
```

Page-specific controls should use stable selectors, for example:

```text
basic-login-username
basic-register-confirm-password
basic-sms-request-code
basic-search-category-filter
basic-settings-save
basic-confirm-surface
```

Do not rely on random text, CSS order, or translated labels as the only selector.

## Timer / State Design

- Use deterministic durations, preferably 300-600 ms for submit/search/save/confirm.
- SMS countdown may be short and deterministic; avoid real-time waits longer than needed for local smoke.
- Store timer handles and clear them during reset, route switch, and component unmount.
- Keep all data local to the fixture component.
- Do not call real HTTP APIs.
- Do not use random values or current time in visible result state.

## Data Flow

```text
router basic route
-> BasicBusinessFixtureShell
-> fixture-specific component
-> local state transition after user action
-> stable status / result region
-> reset returns local state to initial values
```

Shell card flow:

```text
RuntimeObservationIndex basic category
-> implemented basic fixture card
-> /runtime-observation/basic/<fixture>
```

No data flows through API, DB, replay, reporter, `wait_result`, or `observation_summary` in this package.

## State Derivation

Fixture state is local and deterministic:

- `idle`：initial fixture state。
- `editing`：input has changed but no result is shown。
- `validating`：frontend validation is being evaluated。
- `loading` / `pending`：short deterministic timer is pending。
- `success`：visible success / saved / result state。
- `error`：visible frontend validation or deterministic business error surface。
- `empty`：search fixture has no result。
- `not_found`：detail fixture local missing item state。
- `confirming`：confirm fixture shows modal-like confirmation surface。
- `dirty`：settings fixture has unsaved local changes。

These states are fixture UI states only. They do not change `WaitResult.status`,
`ReplayObservationSummary.status`, or runtime task success semantics.

## Failure / Edge Cases

- Reset while timer is pending must clear the timer before restoring initial state.
- Route key missing from metadata should render a stable fallback state or redirect within the
  `/runtime-observation` namespace; it must not create a blank page.
- Search empty result and detail not-found must be deterministic.
- Validation errors must be frontend-local and must not imply backend validation support.
- Implemented cards must link only to routes that exist.
- Medium / complex / mobile cards remain planned / deferred.
- Weak network / HTTP status / backend validation are deferred to 11.2.4.5.
- Recovery / retry / abort / takeover are deferred to M12.

## Compatibility

- Existing `/login` and `/users` remain unchanged.
- Existing `/runtime-observation` shell remains the entrypoint.
- `/runtime-observation/basic/*` route namespace remains stable.
- Planned medium / complex / mobile / mock-backend cards remain planned or deferred.
- Current MVP observation signal labels remain unchanged.

## Non-goals

- No source code changes in this documentation pass。
- No backend service。
- No mock API。
- No E2E / Playwright tests。
- No autonomous run。
- No reporter integration。
- No new observation signal policy。

## Validation Commands For This Docs Pass

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Do not run E2E, `verify-scenario`, or autonomous run for this documentation revision.
