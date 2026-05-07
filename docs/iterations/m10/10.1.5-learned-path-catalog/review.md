# Review

状态：已完成。

## 实际做了什么

- 新增 `apps/console/src/pages/LearnedPathCatalogPage.vue`
  - 顶部标题 + 副标题说明这是系统沉淀出的可复用路径资产。
  - 工具栏：trust filter（all / provisional / confirmed / flaky / deprecated）+ refresh。
  - 列表列：scenario、page_template、trust（带颜色 tag）、hit_count、source_run_id（可跳转）、created_at、updated_at、actions。
  - 路径级操作：确认路径、标记为不稳定、废弃路径，均带 Popconfirm 并说明是路径级操作。
  - actions 展示：a-drawer 内调用 `getLearnedPath` 展示详情和 actions timeline。
  - 空状态、加载失败处理。
- 更新 `apps/console/src/router/index.ts`
  - 新增 `/exploration/learned-paths` 路由 `exploration-learned-paths`。
- 更新 `apps/console/src/layouts/MainLayout.vue`
  - 侧边栏新增 `LearnedPath` 入口，使用 `BookOutlined` 图标。
- 更新 i18n
  - `zh.ts` / `en.ts` / `ja.ts` 新增 `nav.learnedPaths` 和完整的 `learnedPaths` 命名空间。
- 新增单测 `apps/console/src/__tests__/components/LearnedPathCatalogPage.test.ts`
  - 覆盖 list / render / empty / error / filter / source run 跳转 / actions drawer / trust patch（confirmed / flaky / deprecated）/ disabled 状态 等 13 条用例。
- 更新现有单测
  - `router/index.test.ts`：断言新路由名。
  - `i18n/locales.test.ts`：断言三语都包含 `learnedPaths`。
- 补充清理 history detail 的 LearnedPath 操作入口
  - `AutonomousRunDetailPage.vue` 的 LearnedPath 区块只保留只读关联
    信息：id、trust、relation、hit_count、source_run_id。
  - 移除 history detail 中的 `确认路径` / `废弃路径` 操作按钮。
  - 移除该页面对 `patchLearnedPathTrust` 的调用。
  - 更新 `AutonomousRunDetailPage.test.ts`，断言 LearnedPath 区块只读，
    run review 按钮仍保留。
- 补充 history 列表上的 run review 入口
  - `AutonomousRunHistoryPage.vue` 列表新增审核状态列。
  - 每条 run 增加 `确认` / `标记错误` 按钮，调用 run review API。
  - 这些按钮只修改当前 run 的 `operator_review_status`，不修改
    LearnedPath trust。

## 后端 / 接口投影改动

LearnedPath catalog 本身完全复用现有接口：

- `GET /exploration/learned-paths`
- `GET /exploration/learned-paths/{path_id}`
- `PATCH /exploration/learned-paths/{path_id}/trust`

为支持 history 列表直接显示和操作 run review，列表投影补充返回：

- `GET /exploration/autonomous-runs`
  - `operator_review_status`

## 验证命令与结果

```bash
cd apps/console && pnpm run test -- LearnedPathCatalogPage router locales
# LearnedPathCatalogPage 13/13 通过
# router 2/2 通过
# locales 4/4 通过

cd apps/console && pnpm run build
# vue-tsc --noEmit && vite build 通过

pnpm exec vitest run src/__tests__/components/AutonomousRunDetailPage.test.ts
# 1 file / 8 tests 通过

pnpm run build:console
# vue-tsc --noEmit && vite build 通过

git diff --check
# 无尾随空白问题
```

注：`AutonomousUseCasesPage.test.ts` 有 2 条预设失败（`abortRunning is not a function`），与本次迭代无关。

## 是否触发 live autonomous run

否。本次迭代仅在前端新增 LearnedPath catalog 页面和配套测试，未调用任何 autonomous run 创建接口。
