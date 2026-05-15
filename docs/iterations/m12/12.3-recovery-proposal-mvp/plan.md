# 12.3 Implementation Plan

状态：proposed

## 输入

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `review.md`
- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`

## 文件 / 模块

- `docs/iterations/m12/12.3-recovery-proposal-mvp/README.md` - 更新为代码型迭代包索引和门禁状态。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/intent.md` - 更新目标、动机、边界和成功标准。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/contract.md` - 新增 proposal 概念、状态、schema、evidence 和兼容性契约。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/technical-design.md` - 新增 future schema / service / data flow 设计。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/test-plan.md` - 新增 future unit matrix 和未运行项。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/review.md` - 按新模板记录本轮实际验证证据。
- `docs/iterations/m12/README.md` - 同步 12.3 为 proposed / design package。
- `docs/iterations/m12/m12-plan.md` - 同步 12.3 为 current design package。

本轮不修改 `apps/**`、`packages/**`、`docs/iterations/templates/**`、
`docs/iterations/m11/**`、AGENTS / CLAUDE / roadmap / product model / architecture /
scope-boundaries。

## 步骤

1. 执行 precheck：确认当前分支是 `v0.2-local`，工作区 clean，并审计
   `v0.2-local` 相对 `v0.2` 的本地堆叠差异。
2. 按最新 iteration templates 重写 12.3 `README.md`、`intent.md`、`plan.md`、
   `review.md`。
3. 新增 `contract.md`、`technical-design.md`、`test-plan.md`。
4. 最小同步 M12 README / m12-plan 的 12.3 状态。
5. 运行文档级静态检查和七件套存在性检查。
6. 将实际验证结果回填到 `review.md`。
7. 只 stage `docs/iterations/m12`，确认 staged diff 只包含 M12 文档。
8. 本地提交，不 push。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细
测试矩阵。本轮是 docs-only alignment，因此只执行文档级静态检查；future unit
tests 只写入 `test-plan.md`，不在本轮运行。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `test -f docs/iterations/m12/12.3-recovery-proposal-mvp/README.md` and six sibling checks | 12.3 七件套全部存在。 | Yes | 文件存在性检查。 |
| `git diff --check` | 文档 diff 无 whitespace error。 | Yes | 静态检查。 |
| `git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'` | 无代码 / package 改动。 | Yes | Scope guard。 |
| `find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print` | 无输出。 | Yes | 未创建 12.4。 |
| `find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print` | 无输出。 | Yes | 未创建 12.5。 |
| `find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print` | 无输出。 | Yes | 未创建 12.6。 |
| `git status --short docs/iterations/m11` | 无输出。 | Yes | 未改 M11 history docs。 |
| `git diff --name-only` | 只显示 `docs/iterations/m12/**`。 | Yes | Scope guard。 |
| `git diff --cached --name-only` | stage 后只显示 `docs/iterations/m12/**`。 | Yes | Commit scope guard。 |
| `git diff --cached --check` | 无输出。 | Yes | Staged whitespace check。 |

## 复核清单（Review Checklist）

- [ ] 12.3 仍然匹配 `contract.md`。
- [ ] 12.3 是代码型迭代，已经包含 `technical-design.md`。
- [ ] `test-plan.md` 已存在并与技术设计 Test Matrix 一致。
- [ ] plan 验证表格引用 `technical-design.md` 和 `test-plan.md`。
- [ ] 本轮没有代码、API、CLI、DB、frontend、E2E、live run 改动。
- [ ] 验证命令已执行并记录到 `review.md`，未运行项写明 not run / unverified。
