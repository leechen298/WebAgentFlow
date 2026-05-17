# 测试计划（Test Plan）

状态：implementation complete, review pending

## Test Scope For Implementation Closure

本轮验证 11.2.4.2 production-like fixture implementation：

- validation-site build。
- `/runtime-observation/basic/*` route registration。
- per-fixture happy path。
- per-fixture local validation / deterministic business failure path。
- per-fixture loading / pending state。
- per-fixture success state。
- per-fixture reset behavior。
- stable anchors。
- current MVP / future observation label separation。
- package / backend boundary unchanged。

本轮不覆盖：

- E2E evidence closure。
- `verify-scenario`。
- autonomous run。
- Task Result Reporter。
- M12 recovery。
- mock backend HTTP behavior。

## Per-fixture State Matrix

| Fixture | Happy path | Local error path | Loading / pending | Reset check |
|---|---|---|---|---|
| basic-login | valid username/password -> success panel | required fields, invalid credentials | submit loading | clear fields, remember me false, hide alert/success |
| basic-register | valid form + terms -> success panel | invalid email, password mismatch, terms not accepted | submit loading | clear fields, terms false, hide errors/success |
| basic-sms-login | phone -> request code -> valid code -> success | invalid phone, missing code, invalid code | countdown, submit loading | clear phone/code, stop countdown |
| basic-search | query/filter -> result list/count | empty query hint, empty result | search loading | clear query/filter/results/empty |
| basic-detail | refresh -> updated detail | load missing -> not found | refresh/loading missing | restore initial detail card |
| basic-settings | change controls -> save -> saved | warning surface for invalid local combination | saving | restore controls, dirty false, save disabled |
| basic-confirm | open confirm -> confirm -> success | cancel confirm | pending after confirm | close confirm, clear pending/success |

## Route Smoke

If a local dev server is started explicitly, a lightweight browser smoke checks:

- `/runtime-observation/basic/login`
- `/runtime-observation/basic/register`
- `/runtime-observation/basic/sms-login`
- `/runtime-observation/basic/search`
- `/runtime-observation/basic/detail`
- `/runtime-observation/basic/settings`
- `/runtime-observation/basic/confirm`

For each route:

- heading is visible。
- primary trigger is visible。
- secondary action / distractor is visible。
- result region is visible。
- status label is visible。
- reset control is visible。
- happy path can reach success。
- local error path can reach visible error / empty / not-found state。
- reset restores deterministic initial state。

Do not report browser smoke as E2E. Do not trigger `verify-scenario` or autonomous run.

## Boundary Checks

- No API call is added.
- No replay / wait service / reporter import is added.
- No package / lock file changes unless explicitly justified before implementation.
- Future signal labels are not presented as current runtime observation support.
- Timer delay is deterministic and frontend-local.
- Weak network / HTTP errors are not tested in 11.2.4.2.
- Recovery / retry / abort are not tested in 11.2.4.2.

## Required Commands

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Expected:

- `git diff --check`: no output。
- validation-site build exits 0。
- backend / package / lock status check: no output。
- forbidden directory check: report output honestly; existing directories may be noted as not introduced by this package。

## Evidence Requirements

Future `review.md` update must record:

- command。
- expected result。
- actual result。
- exit code。
- pass / fail / skip count where available。
- not run reason for optional browser smoke / E2E / autonomous run。

Do not write `E2E passed`, `verified`, or `works` without actual evidence.
