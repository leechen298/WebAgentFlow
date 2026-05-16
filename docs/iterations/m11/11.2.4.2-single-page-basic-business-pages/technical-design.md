# 技术设计（Technical Design）

状态：implementation-ready

## 当前状态（Current State）

- `apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue` 已实现
  runtime observation shell。
- `/runtime-observation` 和 `/runtime-observation/basic` 等 category routes 已存在。
- Shell 中 basic category 目前只展示 planned fixture card，不提供全部 basic business pages。
- validation-site 当前没有 mock backend dependency。
- validation-site 当前 package 有 `build` script，没有独立 `test` script。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| basic pages only | 只新增 `/runtime-observation/basic/*` routes | build / route review | 不加 medium / complex / mobile |
| deterministic frontend state | 组件内固定 state + short timer | build / future route smoke | 不代表真实 network evidence |
| stable anchors | 每页提供 heading、trigger、result、reset、status `data-testid` | future route smoke | anchors 必须稳定 |
| reset convention | 每页 reset 回 initial state，并清 pending timer | future route smoke | reset 不是 recovery |
| current/future boundary | UI 文案区分 current MVP signals 与 future labels | review | future signals 不写成 implemented |
| no backend dependency | 不调用 API，不新增 mock backend | build / review | 11.2.4.5 才接 mock backend |
| no reporter / M12 | 不调用 reporter，不做 retry / abort / recovery | review | 仅 fixture 页面 |
| shell compatibility | 更新 RuntimeObservationIndex cards link 到 implemented routes | build / review | 不重写 shell 架构 |

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| `apps/validation-site/src/pages/runtime-observation/*` | Yes | 新增 basic fixtures 页面 / 组件 | 保留 shell |
| validation-site router | Yes | 新增 `/runtime-observation/basic/*` routes | 不新增全局 basic routes |
| validation-site index `/` | No / optional | 通常不需要改首页 | 已有 Runtime Observation 入口 |
| validation-site i18n | Optional | 如新增共享文案可更新 | 不强制 |
| validation-site specs | Optional | 本轮可不新增 spec；若新增必须不跑 E2E 假通过 | 不影响现有 specs |
| API routes | No | 不新增 API | N/A |
| DB schema | No | 不新增 migration | N/A |
| Replay / wait service | No | 不改 observation runtime | N/A |
| Task Result Reporter | No | 不接 reporter | N/A |
| E2E tests | No | 不新增 / 不运行 | 11.2.4.7 |

## Proposed Implementation

Recommended structure:

```text
apps/validation-site/src/pages/runtime-observation/basic/
apps/validation-site/src/pages/runtime-observation/basic/BasicBusinessFixturePage.vue
apps/validation-site/src/pages/runtime-observation/basic/basicFixtures.ts
```

Alternative with one component per fixture is acceptable if it stays small and does not duplicate reset /
timer handling. Prefer a single metadata-driven component if it keeps the implementation clearer.

Implementation steps:

1. Add basic fixture metadata for seven fixtures.
2. Add `/runtime-observation/basic/<fixture>` routes.
3. Render one page per route with stable heading / trigger / result / reset / status anchors.
4. Implement deterministic local state transitions:
   - validation message。
   - delayed success / loading。
   - empty result。
   - confirm surface。
   - disabled / enabled state。
5. Update `RuntimeObservationIndex.vue` basic fixture cards:
   - include all seven fixtures。
   - mark implemented routes as `implemented` only after the routes exist。
   - link only implemented basic routes。
   - keep future signal labels as future expected observation。
6. Preserve existing `/runtime-observation` shell and category navigation.

## Fixture Details

| Fixture | Route | Initial state | Trigger | Visible result | Current MVP expected | Future expected |
|---|---|---|---|---|---|---|
| login | `/runtime-observation/basic/login` | empty username/password | submit | validation error or success status | title/url only if route title changes | form_validation_message, toast_shown |
| register | `/runtime-observation/basic/register` | empty registration form | submit | inline validation or delayed success | title/url only if route title changes | form_validation_message, toast_shown |
| sms_login | `/runtime-observation/basic/sms-login` | phone/code inputs | request code / submit | countdown, validation, success status | title/url only if route title changes | form_validation_message, element_enabled |
| simple_search | `/runtime-observation/basic/search` | default result list | search | loading then results or empty state | no primary unless URL/title changes | list_changed, loading_finished |
| simple_detail | `/runtime-observation/basic/detail` | detail card visible | refresh / load missing | loading then detail or not found | title/url only if route title changes | text_appeared, loading_finished |
| simple_settings | `/runtime-observation/basic/settings` | toggle + save button | toggle/save | disabled/enabled and saved status | no primary unless URL/title changes | element_enabled, toast_shown |
| simple_confirm | `/runtime-observation/basic/confirm` | action visible | open confirm / confirm | confirm surface and success status | no primary unless URL/title changes | modal_opened, toast_shown |

## Stable Anchor Design

Every fixture page should expose:

```text
data-testid="basic-fixture-heading"
data-testid="basic-fixture-trigger"
data-testid="basic-fixture-result"
data-testid="basic-fixture-reset"
data-testid="basic-fixture-status"
```

If a fixture has multiple triggers, suffix the selector:

```text
basic-fixture-trigger-primary
basic-fixture-trigger-secondary
```

Do not rely on random text, CSS order, or translated labels as the only selector.

## Timer / State Design

- Use deterministic durations, preferably 300-600 ms.
- Store timer handles and clear them during reset and component unmount.
- Keep all data local to the fixture component.
- Do not call real HTTP APIs.
- Do not use random values or current time in visible result state.

## Compatibility

- Existing `/login` and `/users` remain unchanged.
- Existing `/runtime-observation` shell remains the entrypoint.
- Basic cards can link to implemented basic fixture routes after this package.
- Planned medium / complex / mobile / mock-backend cards remain planned or deferred.
- Current MVP observation signal labels remain unchanged.

## Non-goals

- No backend service。
- No mock API。
- No E2E / Playwright tests。
- No autonomous run。
- No reporter integration。
- No new observation signal policy。

## Test Matrix

| Test area | Coverage goal | Command / evidence |
|---|---|---|
| Build | Vue + TypeScript compiles | `pnpm --filter @web-agent-flow/validation-site build` |
| Diff hygiene | No whitespace errors | `git diff --check` |
| Package boundary | No package / lock / backend changes | `git status --short -- '*.py' 'package.json' ...` |
| Future route smoke | Route opens and anchors visible | not required in this package unless explicitly run |
