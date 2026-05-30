# 实施计划

状态：可执行。只执行 M10 `10.1.1`，不要顺手实现 `10.2` 及
后续主线任务。

## 执行前必读与硬约束

开始施工前，请先阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/m10/m10-plan.md`
4. `docs/iterations/m10/10.1.1-autonomous-use-case-catalog/intent.md`
5. `docs/iterations/m10/10.1.1-autonomous-use-case-catalog/plan.md`

施工边界：

- 只执行 `10.1.1 Autonomous use-case catalog`。
- 不实现 `10.2` 到 `10.6`。
- 不改 autonomous engine、Supervisor、pass gate 或 LearnedPath
  ingest 逻辑。
- 不新增或修改 `/exploration/autonomous-run`、
  `/exploration/autonomous-run/stream` 后端接口。
- 用户点击“批量运行”时，console 页面可以复用现有
  `apps/console/src/api/autonomousStream.ts` 的 `streamAutonomousRun`；
  但测试 / 验证不得替用户触发真实 autonomous run。
- 本轮只做 console 用例目录页、路由、导航、i18n、deep link 到
  workbench、批量选择 / 批量运行 UI，以及必要测试。

## 触及的文件 / 模块

- `apps/console/src/pages/AutonomousUseCasesPage.vue`（新增）——
  用例目录页，负责加载 specs、展示 scenarios、生成 workbench
  deep link，并管理多选 / 全选 / 批量运行队列状态。
- `apps/console/src/api/autonomousStream.ts`（只 import 使用，不改
  contract）—— 批量运行复用 `streamAutonomousRun`。
- `apps/console/src/router/index.ts` —— 新增
  `/exploration/autonomous/cases` 路由。
- `apps/console/src/layouts/MainLayout.vue` —— 侧边栏新增“自主探索
  用例”，放在 workbench 与 history 之间。
- `apps/console/src/i18n/locales/zh.ts` / `en.ts` / `ja.ts` ——
  新增导航和页面文案。
- `apps/console/src/env.d.ts` —— 增加
  `VITE_FIXTURE_SITE_ORIGIN?: string` 类型声明。
- `apps/console/src/__tests__/i18n/locales.test.ts` —— 如果测试对
  locale key 有显式断言，补对应断言。
- 可选：`apps/console/src/__tests__/autonomousUseCases.spec.ts` ——
  覆盖 specs 加载、empty/error、deep link 参数、多选 / 全选 /
  批量运行 payload 和 abort。

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
   - 批量工具条：已选数量、全选可运行用例、清空选择、批量运行、
     中止运行中任务。
2. 主体：
   - 每个 spec 一个 section / card。
   - 显示 `spec_id`、`url_pattern`、`description`。
   - scenario 用 `a-table` 或 `a-list` 展示。
3. scenario 行：
   - checkbox：可运行 scenario 可勾选；缺少 `url_pattern` 时禁用。
   - scenario key。
   - description。
   - inputs / selections 用 `a-tag` 或紧凑 key-value block。
   - expected verdict：优先显示 `expected_verdict`，否则显示
     `not <expected_verdict_not>`。
   - 操作按钮：`在工作台运行`。
   - 批量状态：未运行 / queued / running / completed / failed /
     aborted；失败时展示错误摘要。

## Deep link 规则

新增本地常量：

```ts
const validationOrigin =
  import.meta.env.VITE_FIXTURE_SITE_ORIGIN || 'https://example.invalid';
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
- 单条 deep link 不在本页发起 run；只跳转 workbench。

## 批量运行规则

批量运行是目录页增量能力，不改变 autonomous engine。实现方式：

```ts
import { streamAutonomousRun, type AutonomousStreamPayload } from '@/api/autonomousStream';

function batchPayload(spec: SpecSummary, scenario: SpecScenarioSummary): AutonomousStreamPayload {
  return {
    url: `${validationOrigin}${spec.url_pattern}`,
    goal: scenario.description || spec.description || undefined,
    fill_values: Object.keys(scenario.inputs ?? {}).length > 0 ? scenario.inputs : undefined,
    toggle_values: Object.keys(scenario.selections ?? {}).length > 0 ? scenario.selections : undefined,
    headless: true,
    spec_id: spec.spec_id,
    scenario: scenario.key,
  };
}
```

状态模型：

- `idle`：未进入本轮批量运行。
- `queued`：已选中，等待并发槽位。
- `running`：已调用 `streamAutonomousRun`。
- `completed`：收到 `run_completed` 或 stream 正常 done。
- `failed`：收到 `run_failed` 或 `onError`。
- `aborted`：用户点击中止后调用该任务的 abort 函数。

并发与中止：

- 默认最多同时运行 3 个 scenario；其余保持 `queued`。
- 每个 running 任务保存 `abort` 函数。
- 页面提供“中止运行中任务”按钮，只中止 `running`，并把未开始的
  `queued` 标成 `aborted`。
- 运行中禁止刷新 specs 或清空选择，避免队列和选中状态错位。

可选状态展示：

- 每个任务展示 spec id、scenario、状态、错误摘要。
- 如果 SSE 事件里包含 `run_id`，记录并显示；没有则不造 URL、不猜
  run_id。
- 完成后可以提供“查看历史”按钮跳到
  `/exploration/autonomous/history`。

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

### 4. 实现多选 / 全选

- 维护 `selectedKeys: Set<string>`，key 建议为
  `${spec.spec_id}::${scenario.key}`。
- `runnableScenarios` 只包含 `spec.url_pattern` 非空的 scenario。
- 每行 checkbox 根据 `isRunnable(spec)` 决定是否 disabled。
- “全选可运行用例”只选择 `runnableScenarios`。
- “清空选择”在未运行时清空 `selectedKeys`。
- 顶部展示 `selectedCount / runnableCount`。

### 5. 实现批量运行

- 从 `selectedKeys` 还原选中的 spec / scenario。
- 为每个选中 scenario 构造 `AutonomousStreamPayload`。
- 复用 `streamAutonomousRun(payload, handlers)`。
- 默认并发上限 3。
- 收到 `run_completed` / `run_failed` / `onError` 时更新对应任务状态，
  并启动下一个 queued task。
- 组件 `onBeforeUnmount` 时 abort 所有 running task。
- 不把批量运行结果写成新的 verdict；真实结果以 backend persisted
  run history 为准。

### 6. 接入导航和路由

- `router/index.ts` import 新页面并新增 route。
- meta:
  - `titleKey: 'nav.autonomousUseCases'`
  - `menuKey: '/exploration/autonomous/cases'`
- `MainLayout.vue` 加菜单项，图标可用 Ant Design Vue 的
  `UnorderedListOutlined` 或相近列表图标。

### 7. 补 i18n

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
- `autonomousUseCases.selectAllRunnable`
- `autonomousUseCases.clearSelection`
- `autonomousUseCases.runSelected`
- `autonomousUseCases.abortRunning`
- `autonomousUseCases.selectFirst`
- `autonomousUseCases.notRunnable`
- `autonomousUseCases.selectedCount`
- `autonomousUseCases.runnableCount`
- `autonomousUseCases.batchStatus`
- `autonomousUseCases.statusQueued`
- `autonomousUseCases.statusRunning`
- `autonomousUseCases.statusCompleted`
- `autonomousUseCases.statusFailed`
- `autonomousUseCases.statusAborted`

三份 locale 都补齐，避免 `i18n/locales.test.ts` 失败。

### 8. 测试与验证

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

批量能力测试必须用 mock，不触发真实 run：

1. mock `listSpecs()` 返回至少两个可运行 scenario 和一个不可运行
   scenario。
2. 断言“全选可运行用例”只选择可运行 scenario。
3. 断言“清空选择”清空 selected keys。
4. mock `streamAutonomousRun()`，点击“批量运行选中用例”，断言 payload
   包含 `url`、`goal`、`fill_values`、`toggle_values`、`spec_id`、
   `scenario`、`headless=true`。
5. 断言默认最多同时启动 3 个 running task。
6. 断言 abort 会调用 running task 的 abort 函数，并更新状态。

## 执行提示词

可以直接使用下面这段执行提示词：

```text
你在 /Users/leechen/projects/WebAgentFlow 工作。先阅读 AGENTS.md、
docs/product-model.md、docs/iterations/m10/m10-plan.md、
docs/iterations/m10/10.1.1-autonomous-use-case-catalog/intent.md、
docs/iterations/m10/10.1.1-autonomous-use-case-catalog/plan.md。

只执行 M10 10.1.1：优化 console 自主探索用例目录页，增加
scenario 勾选、全选可运行用例、清空选择、批量运行选中用例和中止运行中任务。
不要实现 10.2+。不要改 autonomous engine，不要新增或修改后端
/exploration/autonomous-run 接口。批量运行只能复用现有
apps/console/src/api/autonomousStream.ts 的 streamAutonomousRun。
测试必须 mock streamAutonomousRun，不要在测试或验证中替用户触发真实 autonomous run。
不要新增后端接口，除非 listSpecs 返回字段确实无法满足页面展示。
实现后运行 pnpm run test 和 pnpm run build:console；如果需要先
build packages，就先跑 pnpm run build:packages。

交付时说明改了哪些文件、验证命令结果、是否触发 live autonomous run，
以及 lint 如有既有失败要明确区分是否由本次新增文件引入。
```

## 收尾要求

- 实现完成后，把实际改动和验证结果追加到
  `docs/iterations/m10/10.1.1-autonomous-use-case-catalog/review.md`。
- 如果实现中发现必须改后端接口，在 `review.md` 说明原因，并同步
  更新本 `plan.md`。
