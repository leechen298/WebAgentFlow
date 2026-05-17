# 契约（Contract）

状态：implementation complete, review pending

## 概念 / 边界契约

11.2.4.2 定义并实现 basic business page fixtures 的验收标准。此前 toy-like 实现 build 通过，
但因业务密度不足被人工 review 否决；当前实现已按 production-like basic fixture contract 重做，
并等待最终 review / evidence closure。

Basic business page 的含义是：

```text
业务目标单一
页面流程相对简单
页面结构完整
状态面真实可见
```

它不是：

```text
一个输入
一个按钮
一行结果
```

Runtime behaviors，例如 toast、modal、loading、validation message、disabled button，
不是业务复杂度本身。它们是完整业务 fixture 内部的状态和行为变体。

## Product Model / Scope / Roadmap Alignment

- 属于 M11.2 Runtime Observation & Realistic Web Hardening。
- 服务 L3 Actual Work replay observation 的 validation fixture 建设。
- 不改变 L1 / L2 / L3 lifecycle。
- 不新增 Agent 角色。
- 不改变 Task Path Planner / Task Result Reporter 职责。
- 不改变 M12 recovery 边界。
- 不依赖外部真实网站。

## Production-like Basic Fixture Contract

Each basic fixture must include:

- main business goal。
- primary action。
- secondary action or distractor。
- visible loading / pending state。
- visible success state。
- visible local validation or deterministic business failure state。
- stable heading。
- stable trigger。
- stable result region。
- stable status label。
- stable reset control。
- deterministic reset。
- current MVP expected observation。
- future expected observation。

Basic fixture failure states are frontend-local deterministic business states. They are not real backend
or network failures.

## Page-level Design Contract

本包页面实现必须以这些设计文档为 source of truth：

```text
fixture-designs/basic-login.md
fixture-designs/basic-register.md
fixture-designs/basic-sms-login.md
fixture-designs/basic-search.md
fixture-designs/basic-detail.md
fixture-designs/basic-settings.md
fixture-designs/basic-confirm.md
```

每个 design doc 必须包含：

- business goal。
- page anatomy。
- happy path。
- local validation / deterministic business failure states。
- loading / pending states。
- success states。
- secondary actions / distractors。
- reset behavior。
- stable anchors。
- current MVP expected observation。
- future expected observation。
- in-scope states。
- deferred states。
- implementation notes。
- business density checklist。
- acceptance checklist。

## Fixture Scope Contract

重做范围仍固定为：

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

## Error Scope Clarification

11.2.4.2 covers frontend-local deterministic success / failure / validation / empty states only.

In scope:

- required field validation。
- invalid credentials as local deterministic business error。
- email format error。
- password mismatch。
- terms not accepted。
- invalid SMS code。
- empty search result。
- missing detail / not found。
- settings warning。
- confirm cancel。
- loading / pending via deterministic frontend timer。

Out of scope:

- weak network。
- offline。
- real HTTP timeout。
- HTTP 400 / 401 / 403 / 404 / 409 / 429 / 500。
- real server validation。
- backend business conflict。
- retry after backend failure。
- user recovery / abort / takeover dialogue。

11.2.4.5 owns mock backend runtime conditions. M12 owns recovery / retry / abort / user takeover.

## Route Namespace Contract

All routes stay under `/runtime-observation/basic/*`.

Allowed routes:

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

This package uses frontend component-local TypeScript types and metadata objects only. It must not add Python
schemas, FastAPI routes, DB migrations, replay response fields, or reporter contracts.

## Compatibility Contract

Implementation must preserve:

- `/` validation-site index。
- existing `/login` fixture。
- existing `/users` fixture。
- existing `/runtime-observation` shell。
- existing Workbench deep link behavior from the validation index。
- existing validation-site specs。
- `/runtime-observation/basic/*` route namespace。

The rejected toy-like implementation is not the final acceptance standard. The current implementation may
refactor internals further, but must preserve the route namespace and shell links.

## Non-goals

- No mock backend。
- No medium / complex / mobile fixtures。
- No E2E evidence closure。
- No runtime observation signal implementation。
- No Task Result Reporter integration。
- No M12 recovery / retry / abort。
- No autonomous run / `verify-scenario` invocation。
