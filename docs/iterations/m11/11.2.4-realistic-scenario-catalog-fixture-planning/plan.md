# 实施计划（Implementation Plan）

状态：documentation generated; implementation not started

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`
- 11.2.1 / 11.2.2 / 11.2.3 observation 文档包

## 文件 / 模块

本轮新增：

- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/README.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/intent.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/contract.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/technical-design.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/test-plan.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/plan.md`
- `docs/iterations/m11/11.2.4-realistic-scenario-catalog-fixture-planning/review.md`

本轮轻量更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

本轮不修改：

- runtime source code。
- test code。
- package / lock files。
- `docs/roadmap.md`。
- `docs/product-model.md`。

## 后续实现路线

### 11.2.4.0 · Scenario Catalog Finalization

整理并固化 realistic scenario catalog。输出业务页面复杂度、运行条件矩阵、
runtime behavior catalog、PC / mobile business page catalog、fixture phase mapping
和 current MVP / future observation boundary。

本轮只整理 catalog：

- 不创建 validation-site 页面。
- 不创建 mock backend。
- 不新增 E2E。
- 不改 validation-site routes。

11.2.4.0 完成后，下一步建议进入 11.2.4.1 Single-page Runtime Fixture Shell。

### 11.2.4.1 · Single-page Runtime Fixture Shell

建立 runtime observation fixture index 和基础 route。目标是让后续所有 fixture 有统一入口、
reset 模式和 stable anchors。

11.2.4.1 文档包已拆出并实现到：

- `docs/iterations/m11/11.2.4.1-single-page-runtime-fixture-shell/`

已实现：

- runtime observation fixture index。
- route shell。
- category navigation。
- reset convention。
- stable anchor convention。

不实现具体业务页面，不接 mock backend，不新增 E2E。

### 11.2.4.2 · Single-page Basic Business Pages

实现 simple business pages 的单页面前端 fixture。11.2.4.2 第一版 build-passing 代码实现
因业务密度不足、过于 toy-like 被人工 review 否决；当前已按页面级设计文档重做为
production-like basic fixtures，状态为 implementation complete, review pending。

重做范围仍为：

- login。
- register。
- sms_login。
- simple_search。
- simple_detail。
- simple_settings。
- simple_confirm。

可以使用 deterministic frontend timer 模拟 loading、validation、visible error surface
和 empty state。

11.2.4.2 的错误范围只包含 frontend-local deterministic 状态；weak network、HTTP
error、server validation 和 backend conflict 进入 11.2.4.5 Mock Backend Runtime
Conditions；recovery / retry / abort / user takeover 进入 M12。

11.2.4.2 implementation package 已拆出到：

- `docs/iterations/m11/11.2.4.2-single-page-basic-business-pages/`

### 11.2.4.3 · Single-page Medium Business Pages

实现 medium business pages 的单页面前端 fixture：

- user_list。
- order_list。
- product_list。
- table_management。
- create_edit_form。
- file_upload。
- export_download。

先用本地前端状态模拟，不接真实 mock backend。

### 11.2.4.4 · Single-page Complex Business Pages

实现 complex 单页面业务：

- dynamic_form。
- wizard_stepper。
- batch_operation。
- master_detail。
- view_edit_preview_mode_switch。
- permission_conditional_ui。
- conditional_fields。

very_complex business pages 当前只进入 scenario catalog，不进入 11.2.4.1 - 11.2.4.5
的近期实现范围。

### 11.2.4.5 · Mock Backend Runtime Conditions

引入 mock API driven scenarios，覆盖 slow response、server validation、error status、
polling、async job、upload、export、download unavailable。

### 11.2.4.6 · Mobile Single-page Patterns

实现移动端单页面：

- mobile_login_sms。
- mobile_search。
- mobile_list。
- mobile_form。
- mobile_picker。
- mobile_action_sheet。
- mobile_pull_to_refresh。
- mobile_infinite_scroll。

### 11.2.4.7 · E2E Evidence and Review

补 scoped E2E 和 evidence 文档。必须记录实际命令、入口 URL、截图 / 日志 / exit code，
不得把未运行项写成通过。

## 验证

以下验证只记录 11.2.4 scenario catalog / fixture planning 文档包当时执行的检查。
后续 11.2.4.x implementation packages 按各自 `test-plan.md` 执行；不要把本父规划包
的历史验证范围当作 child package 的实现限制。

当时运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

## 复核清单（Review Checklist）

- [ ] 只出现文档变更。
- [ ] 新增完整 11.2.4 文档包。
- [ ] `contract.md` 包含 Business Complexity Contract。
- [ ] 业务页面复杂度 × 运行条件矩阵 × runtime behavior 模型清楚。
- [ ] PC / mobile scenario catalog 都存在。
- [ ] Runtime Condition Matrix 和 Runtime Behavior Catalog 都存在。
- [ ] 网络延迟 / 错误场景纳入规划。
- [ ] simple / medium / complex / very_complex 按业务页面复杂度分层。
- [ ] 不把 toast / modal / loading 等技术行为当成页面业务复杂度。
- [ ] 11.2.4.1 明确只建立 fixture shell。
- [ ] 11.2.4.2 / 11.2.4.3 / 11.2.4.4 按 basic / medium / complex business pages 拆包。
- [ ] 11.2.4.5 明确 mock backend runtime conditions。
- [ ] 当前 MVP vs future observation signals 边界清楚。
- [ ] 不依赖外部真实网站。
- [ ] 不接 Task Result Reporter。
- [ ] 不进入 M12 recovery。
- [ ] 不运行 E2E / autonomous run。
