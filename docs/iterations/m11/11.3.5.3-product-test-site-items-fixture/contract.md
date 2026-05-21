# 契约（Contract）

状态：implementation complete

## 范围

本包定义 `apps/product-test-site` 的 `/items` 页面 contract。它是产品级测试页，
不是 validation-site spec fixture，也不是 `wagent chat` runtime contract。

## Route Contract

新增 route：

```ts
{
  path: '/items',
  name: 'items',
  component: ItemsPage,
}
```

当前 `5176` 只是 product-test-site 本地 dev / preview 示例端口，不属于 contract。
后续 runtime 必须使用用户提供或 session 中保存的 target URL，不得硬编码端口。

## Page Contract

页面名称：

```text
ItemsPage.vue
```

页面位置：

```text
apps/product-test-site/src/pages/ItemsPage.vue
```

页面必须提供：

| 能力 | Contract |
|---|---|
| 新增项目 | 用户输入项目名称并点击新增按钮后，列表新增一行 |
| 列表展示 | 页面展示当前项目列表，新增后立即可见 |
| 操作状态 | 页面内展示新增成功或输入为空等状态 |
| 本地状态 | 数据只存在前端内存，刷新后恢复初始状态 |
| 稳定锚点 | 所有 P0 交互和观察目标都有稳定 `data-testid` |

## Data Contract

本包使用前端本地数据：

```ts
type Item = {
  id: string;
  name: string;
  createdAt: string;
};
```

初始数据应稳定，建议：

```ts
[
  { id: 'item-1', name: '默认项目A', createdAt: '...' },
  { id: 'item-2', name: '默认项目B', createdAt: '...' }
]
```

实现可以使用 deterministic timestamp 或页面初始化时间生成 `createdAt` 展示值；
P0 不依赖 `createdAt` 作为 evidence。

## Stable Anchor Contract

必须提供以下 `data-testid`：

| 元素 | `data-testid` |
|---|---|
| 页面根节点 | `items-page` |
| 项目名称输入框 | `item-name-input` |
| 新增按钮 | `item-create-button` |
| 列表容器 | `item-list` |
| 项目行 | `item-row` |
| 项目名称 | `item-row-name` |
| 操作状态 | `operation-status` |

`item-row` 和 `item-row-name` 可重复出现。需要区分行时，可以额外使用
`data-item-id`，但不能用动态 `data-testid` 替代上表中的稳定 anchor。

## Evidence Compatibility Contract

本包不实现 `ExecutionEvidence`，但页面必须为 11.3.5.5 提供可观察目标。

后续 P0 evidence 会优先在以下区域查找文本：

```text
[data-testid='item-list']
```

因此新增成功后，目标项目名必须真实出现在 `item-list` 内的可见文本中。
`operation-status` 只能作为辅助提示，不能替代列表结果。

P0 测试数据应使用唯一项目名，例如：

```text
测试项目B-20260521-001
```

## Behavior Contract

| 场景 | 期望 |
|---|---|
| 输入非空名称并点击新增 | 新增一条项目，清空输入框，状态显示新增成功 |
| 输入前后有空格 | 使用 trim 后的名称新增 |
| 输入为空或全空格 | 不新增项目，状态提示请输入项目名称 |
| 多次新增不同名称 | 列表保留所有新增项 |
| 刷新页面 | 回到初始本地数据 |

本包不强制去重。后续 P0 测试必须使用唯一项目名来避免误判。

## Boundary Contract

- 不新增 API route。
- 不新增数据库表或字段。
- 不改 conversation / learning / replay / task planning runtime。
- 不把 `/items` 接入 validation-site spec / assertion oracle。
- 不把 `operation-status` 文案设计成唯一成功证据。
- 不引入搜索、编辑、删除或高风险操作。
