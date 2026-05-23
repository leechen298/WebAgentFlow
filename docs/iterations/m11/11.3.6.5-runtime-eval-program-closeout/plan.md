# 实施计划（Plan）

状态：draft_for_review

## Step 1：复核当前仓库状态

- `git fetch origin v0.1`
- `git status --short --branch`
- `git log --oneline --decorate --max-count=12 origin/v0.1`
- 确认 11.3.6.3 / 11.3.6.4 是否已有 implementation commits。
- 确认 `docs/testing/results/` 和 `artifacts/wagent-eval/` 中已有 result。

## Step 2：复核 runner 覆盖范围

- 检查 `package.json` eval scripts。
- 检查 `scripts/evals/wagent_runtime_eval.py` 的 `SCHEMA_VERSION`、`ALL_CASES`、case evaluators。
- 确认 runner 没有 direct autonomous-run / direct replay / direct Planner call。

## Step 3：运行或记录 pending-choice closeout

优先运行：

```bash
pnpm run eval:wagent:pending-choice
```

记录：

- exit code；
- status；
- JSON artifact；
- Markdown result；
- live / non-live / blocked；
- redaction grep 结果。

## Step 4：运行或记录 planner-choice closeout

优先运行：

```bash
pnpm run eval:wagent:planner-choice
```

记录：

- exit code；
- status；
- JSON artifact；
- Markdown result；
- `planner_single_path_bypass_regression` section；
- live / non-live / blocked；
- redaction grep 结果。

## Step 5：可选回归

如时间和环境允许，运行：

```bash
pnpm run eval:wagent:items
pnpm run eval:wagent:failure-recovery
```

如果未运行，必须在 closeout result 写 `not_run`，不影响 11.3.6.3 / 11.3.6.4 本次收口，
但影响 program 是否能标 `closed_live`。

## Step 6：回填子包 review

按实际结果更新：

- `docs/iterations/m11/11.3.6.3-pending-choice-multi-candidate-eval/review.md`
- `docs/iterations/m11/11.3.6.4-planner-backed-choice-eval/review.md`

必须写清：

- Code：implemented / not_started / blocked；
- Live eval：pass / not_run / blocked；
- Non-live checks；
- artifact paths；
- not run items。

## Step 7：同步 program / M11 索引

更新：

- `docs/iterations/m11/11.3.6-wagent-runtime-eval-program/README.md`
- `docs/iterations/m11/11.3.6-wagent-runtime-eval-program/review.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`

状态必须与子包 review 一致。

## Step 8：写 program-level closeout result

新增：

```text
docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-<timestamp>.md
```

内容包括：

- Summary status；
- commit；
- per-package status table；
- commands run / not run；
- artifact links；
- redaction checks；
- remaining gaps；
- final recommendation。

## Step 9：最终验证

至少运行：

```bash
git diff --check
```

如修改了 Markdown 文档较多，可补：

```bash
rg -n "Code: not_started|Code：not_started|ready_for_implementation" docs/iterations/m11/11.3.6* docs/iterations/m11/README.md docs/iterations/m11/m11-plan.md
```

确认剩余 `ready_for_implementation` 是有意保留，不是状态漏改。

## Step 10：提交边界

建议分开提交：

1. 11.3.6.5 closeout iteration docs。
2. closeout execution artifacts + review/index status updates。

如果 closeout 发现 runner bug，不提交“完成”状态；另开代码型 fix 迭代。
