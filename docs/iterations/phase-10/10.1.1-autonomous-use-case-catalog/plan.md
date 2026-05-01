# 实施计划

状态：可执行。只执行 Phase 10 `10.1.1`，不要顺手实现 `10.2` 及
后续主线任务。

## 触及的文件 / 模块

- `apps/console/src/pages/AutonomousUseCasesPage.vue`（新增）——
  用例目录页，负责加载 specs、展示 scenarios、生成 workbench
  deep link。
- `apps/console/src/router/index.ts` —— 新增
  `/exploration/autonomous/cases` 路由。
- `apps/console/src/layouts/MainLayout.vue` —— 侧边栏新增“自主探索
  用例”，放在 workbench 与 history 之间。
- `apps/console/src/i18n/locales/zh.ts` / `en.ts` / `ja.ts` ——
  新增导航和页面文案。
- `apps/console/src/env.d.ts` —— 增加
  `VITE_VALIDATION_SITE_ORIGIN?: string` 类型声明。
- `apps/console/src/__tests__/i18n/locales.test.ts` —— 如果测试对
  locale key 有显式断言，补对应断言。
- 可选：`apps/console/src/__tests__/autonomousUseCases.spec.ts` ——
  覆盖 specs 加载、empty/error 和 deep link 参数。

## 页面设计

数据源只用：

```ts
import { listSpecs, type SpecSummary } from '@/api/exploration';
```

页面结构建议：

1. 顶部 `a-card`：
   - 标题：自主探索用例
   - 右侧：刷新按钮、进入 workbench 按钮
   - 简短说明：这些条目来自 authored specs，不是历史运行结果。
2. 主体：
   - 每个 spec 一个 section / card。
   - 显示 `spec_id`、`url_pattern`、`description`。
   - scenario 用 `a-table` 或 `a-list` 展示。
3. scenario 行：
   - scenario key。
   - description。
   - inputs / selections 用 `a-tag` 或紧凑 key-value block。
   - expected verdict：优先显示 `expected_verdict`，否则显示
     `not <expected_verdict_not>`。
   - 操作按钮：`在工作台运行`。

## Deep link 规则

新增本地常量：

```ts
const validationOrigin =
  import.meta.env.VITE_VALIDATION_SITE_ORIGIN || 'http://localhost:5175';
```

构造 workbench URL：

```ts
function workbenchQuery(spec: SpecSummary, scenarioKey: string, description: string) {
  const params = new URLSearchParams();
  params.set('url', `${validationOrigin}${spec.url_pattern}`);
  params.set('spec_id', spec.spec_id);
  params.set('scenario', scenarioKey);
  if (description || spec.description) {
    params.set('goal', description || spec.description);
  }
  return `/exploration/autonomous?${params.toString()}`;
}
```

说明：

- `AutonomousWorkbenchPage.vue` 现在会根据 `url` 自动匹配 spec，并
  读取 `scenario` / `goal`。
- `spec_id` 仍然带上，便于未来 workbench 需要直接读取时兼容；当前
  即使 workbench 忽略它也无害。
- 不在本页发起 run。

## 步骤

### 1. 新增页面骨架

- 创建 `AutonomousUseCasesPage.vue`。
- `onMounted` 调 `listSpecs()`。
- 实现 `loading`、`errorMessage`、`specs` 三个状态。
- 空数据时显示 `a-empty`。

### 2. 实现 scenario 展示

- 每个 spec 下展示 scenarios。
- inputs / selections 都要展示；空对象显示 `—`。
- expected verdict 显示规则：
  - `expected_verdict` 存在：显示该值。
  - `expected_verdict_not` 存在：显示 `not <value>`。
  - 都不存在：显示 `—`。

### 3. 实现 workbench 跳转

- 点击 scenario 的操作按钮时 `router.push(workbenchQuery(...))`。
- 只做页面跳转，不自动运行。
- 如果 `url_pattern` 为空，按钮 disabled，并给 tooltip 说明不能构造
  fixture URL。

### 4. 接入导航和路由

- `router/index.ts` import 新页面并新增 route。
- meta:
  - `titleKey: 'nav.autonomousUseCases'`
  - `menuKey: '/exploration/autonomous/cases'`
- `MainLayout.vue` 加菜单项，图标可用 Ant Design Vue 的
  `UnorderedListOutlined` 或相近列表图标。

### 5. 补 i18n

新增 key 建议：

- `nav.autonomousUseCases`
- `autonomousUseCases.title`
- `autonomousUseCases.subtitle`
- `autonomousUseCases.refresh`
- `autonomousUseCases.openWorkbench`
- `autonomousUseCases.runInWorkbench`
- `autonomousUseCases.specId`
- `autonomousUseCases.urlPattern`
- `autonomousUseCases.scenario`
- `autonomousUseCases.inputs`
- `autonomousUseCases.selections`
- `autonomousUseCases.expected`
- `autonomousUseCases.empty`
- `autonomousUseCases.loadFailed`
- `autonomousUseCases.noUrlPattern`

三份 locale 都补齐，避免 `i18n/locales.test.ts` 失败。

### 6. 测试与验证

至少执行：

```bash
pnpm run test
pnpm run build:console
```

如果 console build 依赖 packages 产物，先执行：

```bash
pnpm run build:packages
pnpm run build:console
```

手动 smoke（不触发真实 run）：

1. 启动 console 和 api。
2. 打开 `http://localhost:5174/exploration/autonomous/cases`。
3. 确认能看到 `login`、`users` 及其 scenarios。
4. 点击 `login.valid_credentials` 的“在工作台运行”。
5. 确认地址变成 `/exploration/autonomous?...`，且 workbench 中 URL /
   scenario / fill values 被带入。
6. 不点击 workbench 的运行按钮。

## 外包执行 brief

可以把下面这段直接给外部编码 Agent：

```text
你在 /Users/leechen/projects/WebAgentFlow 工作。先阅读 AGENTS.md、
docs/product-model.md、docs/iterations/phase-10/phase-plan.md、
docs/iterations/phase-10/10.1.1-autonomous-use-case-catalog/intent.md、
docs/iterations/phase-10/10.1.1-autonomous-use-case-catalog/plan.md。

只执行 Phase 10 10.1.1：新增 console 自主探索用例目录页。
不要改 autonomous engine，不要调用 /exploration/autonomous-run，
不要新增后端接口，除非 listSpecs 返回字段确实无法满足 deep link。
实现后运行 pnpm run test 和 pnpm run build:console；如果需要先
build packages，就先跑 pnpm run build:packages。

交付时说明改了哪些文件、验证命令结果，以及是否有未验证项。
```

## 收尾要求

- 实现完成后，把实际改动和验证结果追加到
  `docs/iterations/phase-10/10.1.1-autonomous-use-case-catalog/review.md`。
- 如果实现中发现必须改后端接口，在 `review.md` 说明原因，并同步
  更新本 `plan.md`。
