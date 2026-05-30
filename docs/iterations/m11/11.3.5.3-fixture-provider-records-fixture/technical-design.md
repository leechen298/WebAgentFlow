# 技术设计（Technical Design）

状态：implementation complete

## 现状

`apps/fixture-site` 当前结构很小：

```text
apps/fixture-site/src/router/index.ts
apps/fixture-site/src/pages/WorkspaceLoginPage.vue
apps/fixture-site/src/pages/WorkspaceHomePage.vue
```

`package.json` 只有：

```text
dev
dev:lan
build
preview
```

没有现成单元测试脚本。本包实现后至少应通过 fixture-site build。

## Contract Alignment

| Contract | Design |
|---|---|
| 新增 `/records` route | 在 `src/router/index.ts` import `ItemsPage` 并新增 route |
| 页面本地状态 | 在 `ItemsPage.vue` 内用 Vue local state 管理 items / input / status |
| 稳定 anchor | 所有 P0 交互元素写入固定 `data-testid` |
| 列表 evidence 兼容 | 项目名称作为可见文本渲染在 `[data-testid='record-list']` 内 |
| 不接 runtime | 不触碰 `apps/api`、`apps/cli`、conversation、learning、replay |

## 文件变更

### 新增

```text
apps/fixture-site/src/pages/ItemsPage.vue
```

### 修改

```text
apps/fixture-site/src/router/index.ts
```

如实现阶段补测试，只能新增 fixture-site 范围内的测试文件；当前设计不要求测试
基础设施重构。

## ItemsPage 设计

### State

建议状态：

```ts
type Item = {
  id: string;
  name: string;
  createdAt: string;
};

const items = ref<Item[]>([
  { id: 'item-1', name: '默认项目A', createdAt: '...' },
  { id: 'item-2', name: '默认项目B', createdAt: '...' },
]);

const itemName = ref('');
const operationStatus = ref('等待新增项目');
```

实现可以使用 `reactive` 或 `ref`，但 contract 行为不变。

### Create Flow

```text
读取 itemName
-> trim
-> 为空则不新增，更新 operation-status
-> 非空则 append item
-> 清空 input
-> operation-status 显示新增成功
```

`id` 可以用递增计数生成，例如 `item-${nextId}`。P0 不要求持久化。

### Template Anchors

必须存在：

```vue
<main data-testid="records-page">
  <input data-testid="record-name-input" />
  <button data-testid="record-create-button">新增项目</button>
  <section data-testid="operation-status">...</section>
  <ul data-testid="record-list">
    <li data-testid="item-row" data-item-id="...">
      <span data-testid="item-row-name">...</span>
    </li>
  </ul>
</main>
```

可以使用 `table` 或 `ul`。关键是 target 文本必须在 `record-list` 内可见。

## Router 设计

在 `src/router/index.ts` 新增：

```ts
import ItemsPage from '../pages/ItemsPage.vue';
```

并加入 route：

```ts
{
  path: '/records',
  name: 'items',
  component: ItemsPage,
}
```

保留现有 `/` redirect、`/target-login` 和 `/workspace-home` 行为。

## UI 设计边界

`fixture-site` 是产品级验收靶场，不是营销页。页面应保持清晰、可扫读：

- 标题说明当前是项目列表。
- 表单和列表同屏可见。
- 按钮文案明确。
- 状态提示靠近操作区域。
- 不使用复杂动画或依赖网络图片。

## Test Matrix

| Layer | Scenario | Command / Surface | Expected |
|---|---|---|---|
| Build | SITE-1 fixture-site build | `pnpm --filter @web-agent-flow/fixture-site build` | vue-tsc + vite build 通过 |
| Router | SITE-2 `/records` 可访问 | `http://localhost:<fixture-port>/records` 或 runtime dev URL | 页面根节点 `records-page` 可见 |
| UI | SITE-3 新增项目 | 输入唯一名称并点击新增 | `record-list` 内出现该名称 |
| UI | SITE-4 空输入保护 | 空输入点击新增 | 不新增空行，`operation-status` 提示输入名称 |
| Regression | REG-1 旧 route 不破坏 | `/target-login`、`/workspace-home` | 现有页面仍可打开 |

`<fixture-port>` 是本地脚本默认端口，只用于 smoke 示例，不写成 runtime contract。

## 风险与约束

| 风险 | 处理 |
|---|---|
| 后续 evidence 全页面误判 | P0 页面必须让目标文本出现在 `record-list` 内；后续 evidence 使用 selector 限定 |
| 页面过度实现 | 本包只做新增，不做搜索 / 编辑 / 删除 |
| 与 fixture-site 混淆 | 本包只在 `apps/fixture-site` 内实现，不接 spec / assertions |
| build 未覆盖真实点击 | test-plan 要求实现阶段补浏览器 smoke 或等价 DOM 验证记录 |
