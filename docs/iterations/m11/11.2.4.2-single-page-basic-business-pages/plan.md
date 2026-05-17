# 实施计划（Implementation Plan）

状态：implementation complete, review pending

## Inputs

- `docs/iterations/m11/11.2.4.2-single-page-basic-business-pages/README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `fixture-designs/*.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

## Current Decision

第一版 `/runtime-observation/basic/*` 代码实现不作为最终验收标准。它已经 build 通过，但被人工 review
否决，原因是页面业务密度不足、过于 toy-like。

当前实现已在保留 route namespace 和 shell links 的前提下重构为 shared shell + per-fixture components。

## Step 0 · Complete Page-level Fixture Designs

Before writing code, read and satisfy:

- `fixture-designs/basic-login.md`
- `fixture-designs/basic-register.md`
- `fixture-designs/basic-sms-login.md`
- `fixture-designs/basic-search.md`
- `fixture-designs/basic-detail.md`
- `fixture-designs/basic-settings.md`
- `fixture-designs/basic-confirm.md`

Status: complete.

## Step 1 · Inspect Existing Implementation

Read:

```text
apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue
apps/validation-site/src/pages/runtime-observation/basic/BasicBusinessFixturePage.vue
apps/validation-site/src/pages/runtime-observation/basic/basicFixtures.ts
apps/validation-site/src/router/index.ts
apps/validation-site/package.json
```

Confirm what can be reused and what must be replaced.

Status: complete.

## Step 2 · Choose Structure

Recommended:

```text
shared shell + per-fixture components
```

The implementer may keep one component only if each fixture remains readable and fully satisfies its design doc.

Status: complete; selected shared shell + per-fixture components.

## Step 3 · Redesign Fixture Metadata

Keep metadata for:

- basic-login。
- basic-register。
- basic-sms-login。
- basic-search。
- basic-detail。
- basic-settings。
- basic-confirm。

Metadata must include fixture id, route, platform, business complexity, runtime behaviors,
runtime conditions, current MVP expected observation, future expected observation, and status.

Status: complete.

## Step 4 · Preserve Basic Routes

Preserve routes under:

```text
/runtime-observation/basic/login
/runtime-observation/basic/register
/runtime-observation/basic/sms-login
/runtime-observation/basic/search
/runtime-observation/basic/detail
/runtime-observation/basic/settings
/runtime-observation/basic/confirm
```

Do not create global `/basic/*` routes.

Status: complete.

## Step 5 · Rebuild Production-like Basic Fixtures

Each fixture must implement:

- complete page anatomy。
- primary business flow。
- secondary action or distractor。
- local validation / deterministic business failure。
- loading / pending。
- success state。
- deterministic reset。
- stable anchors。
- current MVP / future observation labels where useful。

Do not implement weak network, HTTP errors, real server validation, retry, recovery, abort, or takeover.

Status: complete.

## Step 6 · Update Shell Cards

Update `RuntimeObservationIndex.vue` only as needed:

- basic category lists all seven fixtures。
- implemented basic routes stay clickable。
- not-yet-implemented medium / complex / mobile / mock-backend cards remain planned or deferred.
- future signal labels remain future labels.

Status: complete.

## Step 7 · Validate Implementation

Run:

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Optional route smoke may be run only if explicitly requested. Do not run E2E / `verify-scenario` /
autonomous run unless separately requested.

Status: in progress; record final evidence in `review.md`.

## Review Checklist

- [ ] Seven page-level design documents are read.
- [ ] Seven basic routes remain registered.
- [ ] Seven basic fixtures render production-like local business pages.
- [ ] Each fixture has happy path, local error path, loading / pending, success, reset.
- [ ] Stable anchors exist.
- [ ] Reset clears visible state and pending timers.
- [ ] Shell basic cards link only implemented routes.
- [ ] Future signal labels are not current support.
- [ ] No backend / API / replay / reporter changes.
- [ ] validation-site build passes.
