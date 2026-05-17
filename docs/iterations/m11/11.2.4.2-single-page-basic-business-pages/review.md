# Review

Status: implementation complete, review pending

本文档记录 11.2.4.2 Single-page Basic Business Pages 的实现审查和验证证据。

## Status Clarification

11.2.4.2 的代码开发已经完成。当前状态保留为 `implementation complete, review pending`，
意思是“实现完成，等待最终 review / evidence closure”，不是“待开发”。

不要把本包重新切回 planned / pending implementation；后续开发应进入下一包
`11.2.4.3 · Single-page Medium Business Pages`。

## Implementation Summary

11.2.4.2 已将此前被人工 review 否决的 toy-like basic fixtures 重做为
production-like frontend-local fixtures。

Implemented routes:

- `/runtime-observation/basic/login`
- `/runtime-observation/basic/register`
- `/runtime-observation/basic/sms-login`
- `/runtime-observation/basic/search`
- `/runtime-observation/basic/detail`
- `/runtime-observation/basic/settings`
- `/runtime-observation/basic/confirm`

Implementation shape:

- replaced the old `BasicBusinessFixturePage.vue` monolith。
- added `BasicBusinessFixtureShell.vue` as shared heading / back link / status / result / reset shell。
- added 7 per-fixture components under `basic/fixtures/`。
- added `useFixtureTimer.ts` for deterministic timer / countdown cleanup。
- preserved `/runtime-observation/basic/*` route namespace。
- kept all state frontend-local and deterministic。
- did not add mock backend, API, replay, reporter, or M12 recovery behavior。

## Review Fixes

Follow-up review fixes applied:

- SMS submit now validates phone format in both request-code and submit paths, so `phone=abc` + `code=123456`
  cannot reach success。
- SMS submit success clears countdown before submit loading, so the request-code button cannot remain disabled。
- settings radio controls now expose value-specific stable anchors:
  - `basic-settings-frequency-daily`
  - `basic-settings-frequency-weekly`
  - `basic-settings-frequency-never`
- the group anchor `basic-settings-frequency` remains available。
- all 7 fixtures expose `basic-fixture-secondary-trigger` as an exact `data-testid` value。
- shell route switching resets status/result and remounts the active fixture with `:key="fixtureId"`。
- settings reset restores fixed initial values instead of last-saved values。
- settings initial / reset state now uses a clean combination (`notifications=true`, `frequency=daily`,
  `quietHours=false`) so the warning surface is cleared after reset。

## Validation Evidence

| Command / Surface | Expected | Actual result | Exit code | Result | Notes |
|---|---|---|---:|---|---|
| `git diff --check` | no whitespace errors | no output | 0 | PASS | rerun after fixes |
| `pnpm --filter @web-agent-flow/validation-site build` | validation-site build exits 0 | `vue-tsc --noEmit && vite build` completed; Vite build in 2.40s | 0 | PASS | chunk-size warning only |
| browser route smoke via local validation-site dev server on `127.0.0.1:5176` | 7 basic routes open; anchors / local error / happy path / reset pass | login, register, sms-login, search, detail, settings, confirm all PASS | 0 | PASS | in-app browser input was unavailable due virtual clipboard; final smoke used browser coordinates / keypresses |
| `git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'` | no backend / package / lock changes | `M package.json` | 0 | NOTE | unrelated root package script change is present in the shared workspace; not part of 11.2.4.2 validation-site implementation |
| `find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print` | report forbidden directories honestly | `docs/iterations/m11/11.3-interactive-chat-closed-loop` | 0 | NOTE | existing directory, not introduced by 11.2.4.2 |

Browser route smoke covered:

- `/runtime-observation/basic/login`: empty submit error, valid credentials success, reset。
- `/runtime-observation/basic/register`: empty submit error, valid registration success, reset。
- `/runtime-observation/basic/sms-login`: invalid phone submit error, request-code countdown, valid code success, reset。
- `/runtime-observation/basic/search`: deterministic empty result, normal result list, reset。
- `/runtime-observation/basic/detail`: local not-found, refresh success, reset。
- `/runtime-observation/basic/settings`: frequency anchors, save disabled until dirty, save success, reset。
- `/runtime-observation/basic/confirm`: confirm cancel path, confirm success, reset。

## Not Run

- E2E: not run; out of scope for 11.2.4.2。
- `verify-scenario`: not run; prohibited unless separately requested as live product evidence。
- autonomous run: not run; prohibited unless separately requested as live product evidence。
- mock backend tests: not applicable; 11.2.4.2 does not implement mock backend。

## Boundary

- No mock backend implemented。
- No medium / complex / mobile fixtures implemented。
- No API / DB / replay / wait service / reporter changes。
- No M12 recovery / retry / abort behavior。
- No current observation signal implementation changes。

## Remaining Risk

- This is browser route smoke, not E2E evidence closure。
- Future 11.2.4.7 should decide whether these fixtures need formal e2e specs。
