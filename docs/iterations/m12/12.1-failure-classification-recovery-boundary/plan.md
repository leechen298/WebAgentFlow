# 12.1 Implementation Plan

Status: implementation completed.

## 实现文件

本轮实现 12.1 deterministic recovery classifier，并更新本 12.1 文档：

- `apps/api/app/schemas/recovery.py`：定义 `FailureClassification`、
  `BoundaryRecommendation`、`ClassificationReason`、`EvidenceReference`、
  `RecoveryEvidence`、`RecoveryBoundary`。
- `apps/api/app/services/recovery/classifier.py`：确定性 classifier。入口为
  `classify_recovery_boundary(...)`，内部由 `RecoveryBoundaryClassifier`
  实现。
- `apps/api/app/services/recovery/__init__.py`：导出 recovery classifier。
- `apps/api/tests/test_recovery_classifier.py`：覆盖分类矩阵、precedence、
  retry guard、evidence references、input immutability 和 forbidden imports。
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/plan.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/review.md`

没有修改 API router、CLI、conversation dispatcher、database model、Alembic
migration、frontend console、E2E tests、Playwright tests、M11 history docs、
12.2 / 12.3 / 12.4 docs。

## 实现边界

classifier 输入是 M11.1-compatible `RecoveryEvidence`，也接受
`Mapping[str, Any]`。输出是 `RecoveryBoundary`：

- classification；
- recommendation；
- reason；
- evidence references；
- message。

schema 是纯数据结构，不包含执行逻辑。classifier 是纯服务逻辑，不访问 DB、
浏览器、网络、LLM、conversation dispatcher，也不写 LearnedPath。

## 分类优先级

```text
blocked > failure > uncertain > needs_review marker > success_no_recovery_needed
```

含义：

- `blocked` 优先，因为缺上下文、权限、目标页面状态或能力支持时，系统不能安全
  判断后续恢复边界。
- `failure` 次之，表示已有明确负面 evidence。
- `uncertain` 用于 replay 可能完成但缺 postcondition evidence 的情况。
- `needs_review` marker 不应覆盖更强的 blocked / failure / uncertain 分类，但
  应保留在 reason 和 evidence references 中。
- `success_no_recovery_needed` 只能来自明确 postcondition evidence 和
  `task_verified=true`，不能从 replay completed 推导出来。

如果多个信号同时出现，primary classification 按 precedence 选择；reason 必须
说明被保留的次级信号，不能丢失 evidence。

## 分类规则

| Input evidence | Classification | Boundary recommendation |
|---|---|---|
| `task_verified=true` with explicit postcondition evidence | `success_no_recovery_needed` | `no_recovery_needed` |
| `verification_outcome=failed` or replay failed / drifted / error | `failure` | `stop` or `retry_possible_requires_confirmation` only when evidence does not immediately forbid future retry consideration |
| `verification_outcome=blocked` or missing required context | `blocked` | `ask_user` or `stop` |
| `verification_outcome=uncertain` with missing postcondition evidence | `uncertain` | `needs_review` |
| `needs_review=true` or ambiguous evidence | `needs_review` | `needs_review` |
| repeated drift or missing path coverage evidence | `failure` / `blocked` depending on evidence | `suggest_reteach` |

`retry_possible_requires_confirmation` is not retry execution. It only marks
that later 12.3 / 12.4 / user-confirmation flow may consider retry. 12.1
must not make the complete retry allowed / denied decision; that belongs to
12.4.

`retry_candidate=True` 不能覆盖 stronger safety boundaries。blocked、
unsupported action、unsafe / unknown state、permission / auth block、missing
context、unknown side effects 等情况必须保留 `ask_user` 或 `stop`。

## 测试覆盖

- success -> `success_no_recovery_needed` + `no_recovery_needed`；
- replay failed -> `failure` + `stop`；
- drift / target missing -> `failure` + `suggest_reteach`；
- missing context -> `blocked` + `ask_user`；
- unsupported action -> `blocked` + `stop`；
- insufficient postcondition evidence -> `uncertain` + `needs_review`；
- explicit needs_review marker -> `needs_review`；
- precedence: blocked beats failure；
- precedence: failure beats uncertain；
- precedence: uncertain beats needs_review marker；
- retry candidate returns only `retry_possible_requires_confirmation` and never
  executes retry；
- retry candidate does not override permission/auth blocked；
- classifier does not mutate input evidence；
- evidence references preserve structured inputs；
- forbidden dependency imports are absent.

## 验证

本轮只运行 focused unit / static checks，不运行 API full regression、CLI、E2E、
`verify-scenario` 或 browser UI smoke。

```bash
git diff --check
cd apps/api && .venv/bin/python -m pytest tests/test_recovery_classifier.py -q
cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_recovery_classifier.py
git status --short -- '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations/m12 -maxdepth 1 -type d -name '12.2*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.3*' -print
find docs/iterations/m12 -maxdepth 1 -type d -name '12.4*' -print
git status --short docs/iterations/m11
git diff --name-only
git diff --cached --name-only
git diff --cached --check
```
