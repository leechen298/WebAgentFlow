# 实施计划

状态：**可执行**。

本迭代是 console 可视化和操作入口补齐。后端 LearnedPath 的列表、
详情和 trust patch 接口已经存在；实现时优先复用现有 API，不因为
页面需求顺手改 engine 或 replay 逻辑。

## 施工范围

### 前端页面

新增页面：

```text
apps/console/src/pages/LearnedPathCatalogPage.vue
```

建议路由：

```text
GET /exploration/learned-paths
```

注意这里的 `GET` 是浏览器页面语义；前端 router path 建议使用：

```text
/exploration/learned-paths
```

不要放在 `/exploration/autonomous/history` 下面。history 是 run
视角，LearnedPath catalog 是资产视角。

页面基本结构：

1. 顶部标题：`LearnedPath`
2. 辅助说明：这是系统从通过 gate 的运行中沉淀出的可复用路径资产。
3. 工具栏：
   - refresh
   - trust filter
4. 列表：
   - `scenario`
   - `page_template`
   - `trust`
   - `hit_count`
   - `source_run_id`
   - `created_at`
   - `updated_at`
   - actions 摘要入口
   - source run 跳转
   - trust 操作

### 路由和导航

更新：

```text
apps/console/src/router/index.ts
apps/console/src/layouts/MainLayout.vue
```

新增路由 meta：

```ts
{
  titleKey: 'nav.learnedPaths',
  menuKey: '/exploration/learned-paths',
}
```

侧边栏文案建议：

```text
LearnedPath
```

原因：这个词已经是产品概念，不要翻译成“学习路径”导致和普通流程
路径混淆。中文说明文案里可以写“可复用路径资产”。

### API wrapper

优先复用：

```text
apps/console/src/api/exploration.ts
```

现有方法：

```ts
listLearnedPaths(...)
getLearnedPath(pathId)
patchLearnedPathTrust(pathId, body)
```

如执行时发现这些方法已经满足页面需求，不新增 API wrapper。只在
类型缺字段时补类型。

### i18n

更新：

```text
apps/console/src/i18n/locales/zh.ts
apps/console/src/i18n/locales/en.ts
apps/console/src/i18n/locales/ja.ts
```

建议新增命名空间：

```text
learnedPaths
```

至少包含：

- `nav.learnedPaths`
- `learnedPaths.title`
- `learnedPaths.subtitle`
- `learnedPaths.refresh`
- `learnedPaths.trustFilter`
- `learnedPaths.allTrust`
- `learnedPaths.pageTemplate`
- `learnedPaths.scenario`
- `learnedPaths.trust`
- `learnedPaths.hitCount`
- `learnedPaths.sourceRun`
- `learnedPaths.createdAt`
- `learnedPaths.updatedAt`
- `learnedPaths.actions`
- `learnedPaths.viewActions`
- `learnedPaths.openSourceRun`
- `learnedPaths.noSourceRun`
- `learnedPaths.confirmPath`
- `learnedPaths.markFlaky`
- `learnedPaths.deprecatePath`
- `learnedPaths.confirmPathPrompt`
- `learnedPaths.markFlakyPrompt`
- `learnedPaths.deprecatePathPrompt`
- `learnedPaths.pathUpdated`
- `learnedPaths.empty`
- `learnedPaths.loadFailed`
- `learnedPaths.noActions`

中文文案重点：

```text
LearnedPath 是未来复用的路径资产，不是某一次历史运行的人工审核结果。
```

### 操作语义

#### trust tag

展示：

- `provisional`
- `confirmed`
- `flaky`
- `deprecated`

颜色沿用 history detail 里的 LearnedPath trust tag 规则，避免同一
状态在不同页面视觉含义不同。

#### trust 操作

按钮：

- `确认路径` → `confirmed`
- `标记为不稳定` → `flaky`
- `废弃路径` → `deprecated`

行为：

1. 点击按钮前弹确认框。
2. 确认框文案必须说明这是路径级操作，会影响未来复用。
3. 调用 `patchLearnedPathTrust(pathId, { status })`。
4. 更新当前行状态。
5. 当前 trust 已经等于目标状态时，不渲染对应操作按钮，或渲染为
   disabled button 且不包 `Popconfirm`。

不要在本页面提供 run review 操作。run review 只属于 history detail。

### actions 展示

最低实现可以用 drawer / modal 展示 `getLearnedPath(pathId)` 返回的
`actions`。

要求：

- 默认列表页不把完整 actions JSON 全部展开，避免列表噪声过大。
- modal / drawer 内可以先用 compact JSON 或简单 steps 列表。
- actions 为空时显示空状态，不报错。

### source run 跳转

如果 `source_run_id` 存在，提供跳转：

```text
/exploration/autonomous/history/{source_run_id}
```

如果不存在：

- 显示 `-` 或 `无 source run`
- 不渲染可点击链接

不要因为 source run 不存在就隐藏 LearnedPath。本页面的主资源是
LearnedPath。

## 后端范围

默认不改后端。

只有在执行时确认现有接口不满足页面最低需求，才允许小范围补充字段。
补字段必须满足：

- 不改 LearnedPath dedup。
- 不改 ingest。
- 不改 autonomous run 创建 / stream。
- 不新增 path 删除接口。

## 测试计划

### 前端单测

新增：

```text
apps/console/src/__tests__/components/LearnedPathCatalogPage.test.ts
```

覆盖：

1. mount 后调用 `listLearnedPaths`。
2. 有数据时渲染 scenario / page_template / trust / hit_count。
3. 空列表显示空状态。
4. 加载失败显示错误提示。
5. trust filter 改变后重新调用 `listLearnedPaths`，并带正确
   `trust` 参数。
6. 点击 source run 跳转到
   `/exploration/autonomous/history/{source_run_id}`。
7. 无 `source_run_id` 时不渲染可点击跳转。
8. 点击 actions 入口调用 `getLearnedPath` 并展示 actions。
9. actions 为空时显示空状态。
10. 点击 `确认路径` 调用 `patchLearnedPathTrust(... confirmed ...)`。
11. 点击 `标记为不稳定` 调用 `patchLearnedPathTrust(... flaky ...)`。
12. 点击 `废弃路径` 调用 `patchLearnedPathTrust(... deprecated ...)`。
13. 当前 trust 已经是目标状态时，不触发无效 patch。

更新：

```text
apps/console/src/__tests__/router/index.test.ts
apps/console/src/__tests__/i18n/locales.test.ts
```

如果全局 Ant Design Vue stubs 缺少页面用到的组件，在：

```text
apps/console/src/__tests__/setup.ts
```

补最小 stub。

### 后端测试

默认不新增后端测试。若实际修改了后端字段或列表筛选，再补对应测试。

## 验证命令

实现后至少执行：

```bash
cd apps/console && pnpm run test -- \
  LearnedPathCatalogPage router locales

pnpm run build:console

git diff --check
```

如果修改了后端，再额外执行：

```bash
cd apps/api && ../../.venv/bin/pytest tests/test_exploration_learned_paths_api.py

cd apps/api && ../../.venv/bin/ruff check \
  app/routers/exploration.py \
  app/schemas/learned_path.py \
  tests/test_exploration_learned_paths_api.py
```

## 手动验收

1. 启动项目并执行数据库迁移：

```bash
pnpm run db:migrate:api
pnpm run dev
```

2. 打开：

```text
http://localhost:5174/exploration/learned-paths
```

3. 如果当前数据库没有 LearnedPath，页面应该显示清楚的空状态。
4. 如果有 LearnedPath：
   - 能看到 scenario / page template / trust / hit count。
   - trust 过滤能正常切换。
   - source run 链接能跳到对应 history detail。
   - actions modal / drawer 能展示路径动作。
   - `确认路径` / `标记为不稳定` / `废弃路径` 修改的是
     LearnedPath trust，不影响 run review。

## 收尾要求

完成后更新本目录 `review.md`，至少记录：

- 实际做了什么。
- 是否改了后端；如果改了，为什么现有接口不够。
- 验证命令和结果。
- 是否触发 live autonomous run。正常情况下应为：否。
