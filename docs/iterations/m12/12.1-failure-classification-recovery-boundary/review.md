# Review and Reflection

Status: implementation completed.

## 初始化记录

- 创建 12.1 Failure Classification and Recovery Boundary 文档目录。
- 实现 deterministic recovery boundary classifier。
- 新增 schema、service、focused unit tests。
- 本轮没有创建 12.2 / 12.3 / 12.4 目录。
- 本轮没有修改 `docs/iterations/m11/**` 历史文档。

## Created / Modified Files

- `apps/api/app/schemas/recovery.py`
- `apps/api/app/services/recovery/__init__.py`
- `apps/api/app/services/recovery/classifier.py`
- `apps/api/tests/test_recovery_classifier.py`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/plan.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/review.md`

## Scope Summary

12.1 被定义为 M12 的 evidence-bound classifier 和 recovery boundary
recommender。它从 M11.1 structured execution / result reporting evidence 出发，
输出：

- classification；
- reason；
- evidence references；
- boundary recommendation。

12.1 不执行：

- retry；
- replan；
- browser continuation；
- user-facing recovery dialogue；
- recovery proposal generation；
- autonomous exploration；
- hidden relearning；
- LearnedPath write-back；
- user abort handling。

## Classification Precedence

实现固化的 precedence：

```text
blocked > failure > uncertain > needs_review marker > success_no_recovery_needed
```

含义：

- blocked 是最强边界，不能被 retry candidate 覆盖。
- failure 表示明确负面 evidence。
- uncertain 表示 replay 可能完成但缺 postcondition evidence。
- needs_review marker 保留在 evidence references 中，但不覆盖 blocked /
  failure / uncertain。
- success 只能来自 `task_verified=True` 加 explicit postcondition evidence。

## Retry Guard

`retry_candidate=True` 只可能把安全边界标记为
`retry_possible_requires_confirmation`，并且只作为 later 12.3 / 12.4 /
user-confirmation consideration。

它不能覆盖：

- blocked；
- unsupported action；
- unsafe / unknown state；
- permission / auth blocked；
- missing required context；
- unknown side effects。

这些场景必须保持 `ask_user` 或 `stop`。

## Follow-up References

本轮未发现必须立即修改的 `docs/iterations/m12/**` 外部 stale reference。若后续
全局状态文档需要同步，应在单独文档同步任务中处理，不混入 12.1 初始化提交。

## Test Evidence

```bash
cd apps/api && .venv/bin/python -m pytest tests/test_recovery_classifier.py -q
```

Result: `16 passed`

```bash
cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_recovery_classifier.py
```

Result: `All checks passed!`

Covered:

- success -> `success_no_recovery_needed`；
- replay failed -> `failure`；
- drift / target missing -> `suggest_reteach`；
- missing context -> `ask_user`；
- unsupported action -> `stop`；
- insufficient postcondition evidence -> `uncertain`；
- explicit needs_review marker；
- blocked / failure / uncertain precedence；
- retry candidate boundary marker；
- retry guard for permission / auth blocked；
- input immutability；
- evidence references；
- forbidden dependency imports。

## 未运行的验证

本轮没有运行：

- CLI tests；
- E2E tests；
- `verify-scenario`；
- autonomous run；
- browser UI smoke。

## 进入 implementation 前的人工审核

进入 12.1 implementation 前，需要人工审核：

- classification values 是否稳定；
- classification precedence 是否已明确，尤其是 blocked / failure /
  uncertain / needs_review marker 的冲突处理；
- boundary recommendation 是否足够保守；
- `retry_possible_requires_confirmation` 是否仍然不会被误解为 retry command
  或完整 safe-retry 判断；
- user abort 是否继续留在 12.2；
- 未来 schema / service / tests 路径是否需要调整。

## Expected Validation

```bash
git diff --check
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.2*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.3*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
