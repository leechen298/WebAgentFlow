# 实施计划（Plan）

状态：implementation complete

## 施工前提

- 已阅读本目录的 `intent.md`、`contract.md`、`technical-design.md` 和 `test-plan.md`。
- 已阅读父包：
  - [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-construction.md)
  - [`../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md`](../11.3.5-customer-facing-agent-router-skill-runtime/working-runtime-iteration-plan.md)
- 本包只实现 `/records` 页面基座，不改 runtime。

## 实施步骤

### Step 1 · 新增 ItemsPage

新增：

```text
apps/fixture-site/src/pages/ItemsPage.vue
```

实现：

- 页面根节点 `data-testid="records-page"`。
- 项目名称输入框 `data-testid="record-name-input"`。
- 新增按钮 `data-testid="record-create-button"`。
- 操作状态 `data-testid="operation-status"`。
- 列表容器 `data-testid="record-list"`。
- 每行 `data-testid="item-row"`，建议额外带 `data-item-id`。
- 项目名称 `data-testid="item-row-name"`。

行为：

- 初始数据包含 `默认项目A` 和 `默认项目B`。
- 非空名称新增到列表。
- 新增后清空输入框并更新状态。
- 空名称不新增，状态提示输入名称。

### Step 2 · 注册 `/records` route

修改：

```text
apps/fixture-site/src/router/index.ts
```

新增 import 和 route，保留现有 `/`、`/target-login`、`/workspace-home`。

### Step 3 · 运行构建验证

运行：

```bash
pnpm --filter @web-agent-flow/fixture-site build
```

期望：

```text
vue-tsc --noEmit 通过
vite build 通过
```

### Step 4 · 页面 smoke

启动：

```bash
pnpm --filter @web-agent-flow/fixture-site dev
```

打开：

```text
http://localhost:<fixture-port>/records
```

验证：

- 页面可访问。
- 新增唯一项目名后，`record-list` 内出现该文本。
- 空输入不会新增空项目。
- `/target-login` 和 `/workspace-home` 仍可访问。

### Step 5 · 更新 review

在 `review.md` 记录：

- 变更文件。
- build 输出。
- smoke URL。
- smoke 使用的唯一项目名。
- 未运行项及原因。

## 不允许顺手做

- 不改 `apps/api`。
- 不改 `apps/cli`。
- 不改 `apps/fixture-site`。
- 不实现 `record_name` slot extraction。
- 不实现 `slot_overrides` / `value_slot`。
- 不采集 `ExecutionEvidence`。
- 不接 `TaskResultReporter`。
- 不运行 autonomous-run。

## 交付清单

| Deliverable | Required |
|---|---:|
| `ItemsPage.vue` | Yes |
| `/records` route | Yes |
| Stable `data-testid` | Yes |
| fixture-site build evidence | Yes |
| `/records` create-item smoke evidence | Yes |
| `review.md` 更新 | Yes |
