# 12.3 Review and Reflection

Status: documentation initialized.

## 初始化记录

本轮初始化 12.3 Recovery Proposal MVP 文档。

创建：

- `README.md`
- `intent.md`
- `plan.md`
- `review.md`

更新：

- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`

## Scope Summary

12.3 被定义为 recovery proposal generator / formatter 的文档包。它基于：

- 12.1 `RecoveryBoundary`；
- 12.2 `AbortAcknowledgement`。

12.3 设计可展示给用户的 proposal options，但不执行任何 option。

## Proposal Semantics

`RecoveryProposal` 是用户可见的后续选择集合，不是 command。它必须携带：

- proposal source；
- option kind；
- user-facing title / message；
- evidence references；
- confirmation marker；
- policy-check marker；
- downstream owner；
- `non_executable=true` marker。

所有 proposal options 默认不可执行。12.3 可以排序或标记推荐选项，但不能自动
选择 proposal。

## Explicit Non-goals Preserved

本轮没有实现：

- schema；
- service；
- unit tests；
- API endpoint；
- CLI command；
- frontend UI；
- DB / migration；
- conversation dispatcher；
- retry / re-run policy；
- retry execution；
- replan execution；
- browser continuation；
- takeover；
- teaching mode；
- LearnedPath write-back；
- autonomous exploration；
- hidden relearning；
- M11.2 Runtime Observation / Wait-for-change；
- E2E；
- `verify-scenario`。

## Relationship to 12.1

12.1 已实现 evidence-bound classifier。12.3 未来可以消费 12.1 的
classification、reason、evidence references 和 boundary recommendation，
但不重新分类 failure，也不执行 recovery。

`retry_possible_requires_confirmation` 在 12.3 中只能变成
`consider_retry_later` proposal option。它不是 retry command，也不是完整 safe
retry 判断。

## Relationship to 12.2

12.2 已实现 user abort acknowledgement。12.3 未来可以基于 abort decision 和
abort evidence 展示后续选择，但不能绕过 12.2 的 no-new-browser-action boundary。

Abort 后的 proposal 不能自动触发 retry、replan、recovery proposal execution、
takeover、teaching mode 或 browser continuation。

## Relationship to 12.4 / 12.5 / 12.6

- 12.4 owns retry / re-run policy.
- 12.5 owns recovery conversation flow and user-choice routing.
- 12.6 owns recovery tests and evidence closure.

12.3 只定义 proposal 形态和 future implementation plan。

## Follow-up

发现全局入口文档仍有旧状态文案，例如 `AGENTS.md` / `CLAUDE.md` 中的 M12
documentation initialization 描述。按本轮边界，不修改这些全局文档；后续应开
单独入口文档同步任务处理。

## 未运行的验证

本轮没有运行：

- API tests；
- CLI tests；
- E2E tests；
- `verify-scenario`；
- autonomous run；
- browser UI smoke。

## Expected Validation

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.5*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.6*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
