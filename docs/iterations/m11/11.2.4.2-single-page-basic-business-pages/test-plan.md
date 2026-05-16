# 测试计划（Test Plan）

状态：implementation-ready

## Test Scope

本轮实现后必须覆盖：

- validation-site build。
- `/runtime-observation/basic/*` route registration by TypeScript/Vue compile。
- basic fixture metadata renders without type errors。
- package / backend boundary unchanged。

本轮不覆盖：

- E2E evidence closure。
- `verify-scenario`。
- autonomous run。
- Task Result Reporter。
- M12 recovery。
- mock backend HTTP behavior。

## Required Commands

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Expected:

- `git diff --check`: no output。
- validation-site build: exit 0。
- package/backend status check: no output。
- forbidden directory check: no output。

## Optional Manual Route Smoke

If a local dev server is started explicitly, a lightweight browser smoke may check:

- `/runtime-observation/basic/login`
- `/runtime-observation/basic/register`
- `/runtime-observation/basic/sms-login`
- `/runtime-observation/basic/search`
- `/runtime-observation/basic/detail`
- `/runtime-observation/basic/settings`
- `/runtime-observation/basic/confirm`

For each route:

- heading is visible。
- trigger is visible。
- result region is visible。
- reset control is visible。
- status label is visible。

Do not report browser smoke as E2E. Do not trigger `verify-scenario` or autonomous run.

## Boundary Checks

- No API call is added.
- No replay / wait service / reporter import is added.
- No package / lock file changes unless explicitly justified before implementation.
- Future signal labels are not presented as current runtime observation support.
- Timer delay is deterministic and frontend-local.

## Evidence Requirements

Future `review.md` update must record:

- command。
- expected result。
- actual result。
- exit code。
- pass / fail / skip count where available。
- not run reason for optional browser smoke / E2E / autonomous run。

Do not write `E2E passed`, `verified`, or `works` without actual evidence.
