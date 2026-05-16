# 实施计划（Implementation Plan）

状态：implementation-ready

## Inputs

- `docs/iterations/m11/11.2.4.2-single-page-basic-business-pages/README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

## Allowed Files

Implementation may modify:

- `apps/validation-site/src/router/index.ts`
- `apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue`
- `apps/validation-site/src/pages/runtime-observation/basic/*`
- `apps/validation-site/src/i18n/locales/*.ts` if needed for visible labels

Implementation should not modify:

- backend source code。
- API routers。
- replay / wait / reporter services。
- package / lock files。
- docs outside this package unless a design conflict is found and reported first。

## Step 1 · Inspect Existing Shell

Read:

```text
apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue
apps/validation-site/src/router/index.ts
apps/validation-site/src/pages/IndexPage.vue
apps/validation-site/package.json
```

Confirm current shell route and build command.

## Step 2 · Add Basic Fixture Metadata

Add metadata for:

- basic-login。
- basic-register。
- basic-sms-login。
- basic-search。
- basic-detail。
- basic-settings。
- basic-confirm。

Metadata must include fixture id, route, platform, business complexity, runtime behaviors,
runtime conditions, current MVP expected observation, future expected observation, and status.

## Step 3 · Add Basic Routes

Add routes under:

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

## Step 4 · Implement Basic Fixture Page

Implement either:

- one metadata-driven `BasicBusinessFixturePage.vue`; or
- separate small fixture components if that is simpler.

Each route must expose stable anchors:

- heading。
- trigger。
- result region。
- reset control。
- status label。

## Step 5 · Implement Deterministic Behaviors

Use frontend local state:

- validation message。
- delayed success via short deterministic timer。
- loading then result。
- empty result。
- confirm surface。
- disabled / enabled button state。

Reset must clear pending timer and restore initial state.

## Step 6 · Update Shell Cards

Update `RuntimeObservationIndex.vue`:

- basic category lists all seven fixtures。
- implemented basic routes become clickable。
- not-yet-implemented medium / complex / mobile / mock-backend cards remain planned or deferred.
- future signal labels remain future labels.

## Step 7 · Validate

Run:

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

Do not run E2E / `verify-scenario` / autonomous run unless the user separately asks.

## Review Checklist

- [ ] Seven basic routes are registered.
- [ ] Seven basic fixtures render deterministic local state.
- [ ] Stable anchors exist.
- [ ] Reset clears visible state and pending timers.
- [ ] Shell basic cards link only implemented routes.
- [ ] Future signal labels are not current support.
- [ ] No backend / API / replay / reporter changes.
- [ ] validation-site build passes.
