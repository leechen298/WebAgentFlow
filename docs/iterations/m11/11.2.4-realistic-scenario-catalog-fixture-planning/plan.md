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

完成 PC / mobile scenario catalog，确认每个 scenario 的 platform、page type、
complexity、interaction pattern、current MVP limit 和 future observation。

### 11.2.4.1 · Single-page Runtime Fixture Shell

建立 runtime observation fixture index 和基础 route。目标是让后续所有 fixture 有统一入口、
reset 模式和 stable anchors。

### 11.2.4.2 · Single-page Basic Interactions

实现 toast、modal、validation message、button enabled / disabled、component surface
等单页面基础交互。

### 11.2.4.3 · Single-page Async Interactions

实现 loading、delayed search、partial refresh、same-url reload、empty state 和
timer-based error surface。该阶段使用前端 timer，不代表真实 HTTP evidence。

### 11.2.4.4 · Mobile Single-page Patterns

实现 mobile picker、action sheet、bottom sheet、mobile toast、mobile dialog、
scroll / refresh 基础模式。

### 11.2.4.5 · Mock Backend Runtime Fixtures

引入 mock API driven scenarios，覆盖 slow response、server validation、error status、
polling、async job、upload、export、download unavailable。

### 11.2.4.6 · E2E Evidence and Review

补 scoped E2E 和 evidence 文档。必须记录实际命令、入口 URL、截图 / 日志 / exit code，
不得把未运行项写成通过。

## 验证

本轮只运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

## 复核清单（Review Checklist）

- [ ] 只出现文档变更。
- [ ] 新增完整 11.2.4 文档包。
- [ ] PC / mobile scenario catalog 都存在。
- [ ] 网络延迟 / 错误场景纳入规划。
- [ ] simple / medium / complex / very complex 分层清楚。
- [ ] Phase 1 明确单页面 fixture，不要求后端。
- [ ] Phase 2 明确 mock backend。
- [ ] 当前 MVP vs future observation signals 边界清楚。
- [ ] 不依赖外部真实网站。
- [ ] 不接 Task Result Reporter。
- [ ] 不进入 M12 recovery。
- [ ] 不运行 E2E / autonomous run。
