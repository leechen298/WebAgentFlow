# 实施计划（Implementation Plan）

状态：implemented

## 输入

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

## Implementation Files

已存在文档包：

- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/README.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/intent.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/contract.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/technical-design.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/test-plan.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/plan.md`
- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/review.md`

本轮允许修改：

- `apps/validation-site/src/pages/IndexPage.vue`
- `apps/validation-site/src/router/index.ts`
- `apps/validation-site/src/pages/runtime-observation/RuntimeObservationIndex.vue`
- `apps/validation-site/src/pages/runtime-observation/RuntimeObservationShell.vue`（如需要）
- `apps/validation-site/src/i18n/locales/*.ts`（如入口文案需要本地化）

本轮不修改：

- backend source code。
- package / lock files。
- `docs/roadmap.md`。
- `docs/product-model.md`。

## 实现路线

### Step 1 · Inspect current validation-site structure

读取：

```text
apps/validation-site/src/pages/IndexPage.vue
apps/validation-site/src/router*
apps/validation-site/src/main*
apps/validation-site/specs/
```

确认 route / catalog / i18n / test command 结构。

### Step 2 · Add Runtime Observation catalog entry

在现有 `PAGES` catalog 中新增 Runtime Observation 分类入口。

不得重写首页架构，不得删除 `/login`、`/users`。

### Step 3 · Add runtime observation route shell

新增 `/runtime-observation` route 和 index page。

Route namespace 保持完整路径：

```text
/runtime-observation
/runtime-observation/basic
/runtime-observation/medium
/runtime-observation/complex
/runtime-observation/mobile
```

### Step 4 · Add category navigation

展示：

- Basic Business Pages。
- Medium Business Pages。
- Complex Business Pages。
- Mobile Single-page Patterns。
- Mock Backend Runtime Conditions。

### Step 5 · Add planned fixture cards

只展示 planned cards，不实现具体业务页面。

每张 card 展示：

- fixture id。
- platform。
- business complexity。
- phase。
- runtime behaviors。
- runtime conditions。
- current MVP expected observation。
- future expected observation。
- status。

### Step 6 · Add stable anchors and reset convention docs

在 shell 页面中展示 stable anchor / reset convention。

### Step 7 · Add scoped tests or smoke notes

根据现有 validation-site 测试能力决定。当前 validation-site 有 `build` script，未提供
`test` script；不能虚构 component test PASS。

## 验证

本轮运行：

```bash
git diff --check
pnpm --filter @web-agent-flow/validation-site build
git status --short -- '*.py' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

## 复核清单（Review Checklist）

- [ ] validation-site 首页新增 Runtime Observation 入口。
- [ ] `/runtime-observation` shell route 可构建。
- [ ] 明确已有 `IndexPage.vue` / `PAGES` catalog。
- [ ] 只新增 Runtime Observation 分类入口，不重写首页架构。
- [ ] 明确 route namespace。
- [ ] 明确 shell metadata contract。
- [ ] 明确 stable anchor convention。
- [ ] 明确 reset convention。
- [ ] 明确 PC 优先，mobile 后移到 11.2.4.6。
- [ ] 明确 current MVP / future signal label 分离。
- [ ] 不实现具体业务 fixture。
- [ ] 不出现 backend / test / package 变更。
- [ ] `git diff --check` clean。
- [ ] validation-site build PASS。
- [ ] package status check 无输出。
- [ ] forbidden directory check 无输出。
