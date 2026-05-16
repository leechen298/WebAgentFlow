# 契约（Contract）

状态：implementation-ready

## 概念 / 边界契约

11.2.4.2 实现 basic business page fixtures。它们是 validation-site 中自建、确定性、
单页面、前端本地状态驱动的 fixture 页面。

Basic business page 的定义来自 11.2.4.0：

```text
单一目标、单一区块、少量输入、没有复杂状态切换。
```

Runtime behaviors，例如 toast、modal、loading、validation message、disabled button，
不是业务复杂度本身。它们是 fixture 页面里的行为变体。

## Product Model / Scope / Roadmap Alignment

- 属于 M11.2 Runtime Observation & Realistic Web Hardening。
- 服务 L3 Actual Work replay observation 的 validation fixture 建设。
- 不改变 L1 / L2 / L3 lifecycle。
- 不新增 Agent 角色。
- 不改变 Task Path Planner / Task Result Reporter 职责。
- 不改变 M12 recovery 边界。
- 不依赖外部真实网站。

## Fixture Scope Contract

本轮实现的 fixture 范围固定为：

| fixture_id | route | page_type | business_complexity |
|---|---|---|---|
| basic-login | `/runtime-observation/basic/login` | login | simple_business_page |
| basic-register | `/runtime-observation/basic/register` | register | simple_business_page |
| basic-sms-login | `/runtime-observation/basic/sms-login` | sms_login | simple_business_page |
| basic-search | `/runtime-observation/basic/search` | simple_search | simple_business_page |
| basic-detail | `/runtime-observation/basic/detail` | simple_detail | simple_business_page |
| basic-settings | `/runtime-observation/basic/settings` | simple_settings | simple_business_page |
| basic-confirm | `/runtime-observation/basic/confirm` | simple_confirm | simple_business_page |

Do not add medium / complex / mobile / mock-backend fixtures in this package.

## Fixture Behavior Contract

Each fixture must provide:

- stable heading。
- stable trigger element。
- stable result region。
- stable reset control。
- stable status label。
- deterministic initial state。
- deterministic visible state transition after action。
- visible current MVP / future observation boundary where useful。

Each fixture must support reset:

- clear inputs。
- clear validation / status messages。
- close confirm / modal-like surface。
- restore initial list / detail / settings state。
- stop pending timer。
- restore button enabled / disabled initial state。

## Route Namespace Contract

All routes stay under `/runtime-observation/basic/*`.

Allowed new routes:

```text
/runtime-observation/basic/login
/runtime-observation/basic/register
/runtime-observation/basic/sms-login
/runtime-observation/basic/search
/runtime-observation/basic/detail
/runtime-observation/basic/settings
/runtime-observation/basic/confirm
```

Do not create global `/login-basic`, `/register`, `/search-basic`, `/basic/*`, `/medium/*`,
or `/complex/*` routes.

## Runtime Behavior Contract

Allowed deterministic frontend behaviors:

- input validation message。
- delayed status change via frontend timer。
- loading region。
- empty result。
- toast-like status region。
- modal-like confirm region。
- disabled / enabled button state。
- title / URL change only when intentionally navigating within validation-site.

Timer behavior must be deterministic and short enough for local build / smoke workflows. It does not
represent true network evidence. HTTP slow response / status code evidence belongs to 11.2.4.5 mock
backend runtime conditions.

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

Current MVP should not be described as supporting these future signals:

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
```

Fixtures may display future expected observation labels, but they must remain planned / future labels.

## Schema / API Contract

No backend schema/API changes.

This package may add frontend component-local TypeScript types or metadata objects. It must not add Python
schemas, FastAPI routes, DB migrations, replay response fields, or reporter contracts.

## Compatibility Contract

Implementation must preserve:

- `/` validation-site index。
- existing `/login` fixture。
- existing `/users` fixture。
- existing `/runtime-observation` shell。
- existing Workbench deep link behavior from the validation index。
- existing validation-site specs.

## Non-goals

- No mock backend。
- No medium / complex / mobile fixtures。
- No E2E evidence closure。
- No runtime observation signal implementation。
- No Task Result Reporter integration。
- No M12 recovery / retry / abort。
- No autonomous run / `verify-scenario` invocation。
