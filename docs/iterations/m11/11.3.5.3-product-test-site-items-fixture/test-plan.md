# 测试计划（Test Plan）

状态：implementation complete

## 适用条件

本轮是代码型迭代，涉及新的 product-test-site 页面和后续 runtime 闭环页面基座，
因此必须维护 `test-plan.md`。

## 测试范围

- Unit：当前 product-test-site 无单元测试脚本；本包不强制新增测试框架。
- Integration：router + Vite build。
- Product Site UI：必须验证 `/items` 页面新增项目行为。
- Console UI：N/A，本包不改 Console。
- API / CLI：N/A，本包不改 API / CLI。
- `wagent chat`：N/A，留给 11.3.5.4 - 11.3.5.6。
- Live autonomous run：禁止。本包不触发 `verify-scenario` 或 autonomous-run。
- Reporter / Evidence：N/A，本包只提供页面 DOM 基座。

## 测试矩阵

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Docs | DOC-1 文档包完整 | `find docs/iterations/m11/11.3.5.3-product-test-site-items-fixture -maxdepth 1 -type f` | 七件套存在 | Yes | 文档阶段 |
| Docs | DOC-2 whitespace | `git diff --check` | clean | Yes | 文档 / 实现阶段都应跑 |
| Product site | SITE-1 build | `pnpm --filter @web-agent-flow/product-test-site build` | `vue-tsc --noEmit && vite build` 通过 | Yes | 实现阶段 |
| Product site | SITE-2 route | `http://localhost:5176/items` | 页面显示 `items-page` | Yes | `5176` 仅本地示例 |
| Product site | SITE-3 stable anchors | Browser / DOM inspect | 必须存在 P0 `data-testid` | Yes | 后续 learning / evidence 依赖 |
| Product site | SITE-4 create unique item | 输入 `测试项目B-${timestamp}` 后点击新增 | `[data-testid='item-list']` 内出现该文本 | Yes | 后续 evidence 兼容 |
| Product site | SITE-5 operation status | 新增成功后查看 `operation-status` | 显示新增成功或等价状态 | Yes | 辅助 evidence |
| Product site | SITE-6 empty input | 空输入点击新增 | 不新增空项目，状态提示输入名称 | Yes | 基础稳健性 |
| Regression | REG-1 old routes | `/workspace-login`、`/workspace-home` | 页面仍可打开 | Yes | 不破坏 11.3.3 |

## 人工 / 浏览器 Smoke 样例

启动 product-test-site：

```bash
pnpm --filter @web-agent-flow/product-test-site dev
```

打开：

```text
http://localhost:5176/items
```

操作：

```text
1. 在项目名称输入框输入：测试项目B-<timestamp>
2. 点击“新增项目”
3. 查看列表区域
```

期望：

```text
[data-testid='item-list'] 内出现 测试项目B-<timestamp>
[data-testid='operation-status'] 显示新增成功或等价状态
输入框被清空
```

空输入样例：

```text
1. 保持项目名称为空
2. 点击“新增项目”
```

期望：

```text
不新增空项目
[data-testid='operation-status'] 提示请输入项目名称
```

## E2E / Live Run 边界

- 不运行 `wagent chat`。
- 不运行 `wagent verify` / `verify-scenario`。
- 不调用 `/exploration/autonomous-runs` 或 `/stream`。
- 不声称参数化 replay、ExecutionEvidence 或 Reporter 通过。
- 没有真实打开 `/items` 并新增项目，不得声称页面 smoke 通过。

## 验收记录要求

实现阶段 `review.md` 必须记录：

- `pnpm --filter @web-agent-flow/product-test-site build` 输出。
- `/items` 页面 smoke 的目标 URL。
- 用于新增的唯一 `item_name`。
- 列表中出现该 `item_name` 的证据描述。
- 未运行项及原因。
