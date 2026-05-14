# 11.2.0 实施计划

## 触及文件

新增：

- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/intent.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/review.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

轻量更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/roadmap.md`

不修改：

- 源码。
- 测试代码。
- package 文件。
- 根目录 README。
- architecture 或 product-model 文档。
- M12 / 12.x / v0.2 文件或分支。

## 步骤

1. 用 `git branch --show-current` 和 `git status --short` 确认分支和工作区状态。
2. 阅读当前 M11 README、M11 plan、roadmap 和 M11.1 收口文档。
3. 创建 11.2 总览文档，说明与 M11.1 的关系、M12 边界、Post-action
   Observation、Passive Runtime Observation 和后续拆包。
4. 创建 11.2.0 intent 文档，写清文档初始化目标和硬边界。
5. 创建本 plan 文档，记录触及文件、步骤和验证方式。
6. 初始化 `review.md`，仅作为状态占位，不声明 implementation review 已完成。
7. 在 `docs/testing/scenarios/` 下创建 realistic web runtime case catalog。
8. 在 `docs/iterations/m11/README.md` 中新增一条 11.2 索引。
9. 在 `docs/iterations/m11/m11-plan.md` 中新增 M11.2 章节，记录 scope、边界和
   11.2.0-11.2.7 拆包。
10. 在 `docs/roadmap.md` 中只新增高层 M11.2 说明。
11. 运行允许的验证命令。

## Scenario Catalog 规则

`docs/testing/scenarios/realistic-web-runtime-cases.md` 是 runtime case catalog，
不是测试计划或证据报告。

每个 case 应包含：

- case name。
- scenario。
- why it matters。
- M11.2 expected observation。
- not in scope。
- future M12 implication。
- future package。

catalog 不得声称这些 case 已经自动化、人工验证或被 E2E 覆盖。

## 与 11.2.1 的关系

11.2.1 在 11.2.0 的 scope 和 case catalog 基础上定义 Observation Signal
Contract。它应覆盖本目录和
`docs/testing/scenarios/realistic-web-runtime-cases.md` 中列出的核心 runtime
cases，但不实现观察、wait-for-change、replay integration 或 reporter integration。

11.2.1 必须明确：

- `page_load_started` / `page_load_finished` 是浏览器级 page load /
  document reload signal。
- `loading_started` / `loading_finished` 是页面内 visible loading UI signal。
- timeout / not-observed 不属于 11.2.1 signal kind。

## 验证

只运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 3 -type d \( -name 'm12' -o -name '12.*' \) -print
```

预期：

- `git diff --check` 退出码为 0。
- code / package status check 无输出。
- M12 directory check 无输出。
- `git status --short` 只出现这些范围：
  - `docs/iterations/m11/`
  - `docs/testing/scenarios/`
  - `docs/roadmap.md`

## 完成措辞

使用：`11.2.0 文档初始化完成`。

不要写：

- `runtime support implemented`。
- `observation feature complete`。
- `wait-for-change implemented`。
- `result reporter observation integrated`。
- `M12 started`。
