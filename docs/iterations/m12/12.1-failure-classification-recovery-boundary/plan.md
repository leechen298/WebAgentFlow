# 12.1 Implementation Plan

Status: documentation initialized.

## 本轮文件

本轮只创建和更新 M12 文档：

- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/README.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/intent.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/plan.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/review.md`
- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`

本轮不创建任何代码文件。

## 未来可能触及的模块

进入 12.1 implementation 前，可以考虑新增：

- `apps/api/app/schemas/recovery.py`：定义 `FailureClassification`、
  `RecoveryBoundary`、`ClassificationReason`、`EvidenceReference`、
  `BoundaryRecommendation` 等 schema。
- `apps/api/app/services/recovery/classifier.py`：从 M11.1 execution / reporter
  evidence 中派生 classification 和 boundary recommendation。
- `apps/api/tests/test_recovery_classifier.py`：覆盖 classification matrix、
  evidence references、non-execution contract 和 forbidden dependency checks。

这些文件只是未来候选路径。本轮不创建这些代码文件，不创建测试文件。

## 未来实现步骤

1. 定义 recovery schema，保持结构化、可序列化、可审计。
2. 建立 classifier 输入边界，只接受 M11.1 execution / result reporter evidence。
3. 实现确定性分类规则，先覆盖 `failed`、`blocked`、`uncertain`、
   `needs_review` 和 `success_no_recovery_needed`。
4. 为每个 classification 生成 `ClassificationReason` 和 `EvidenceReference`。
5. 为每个 classification 派生 `BoundaryRecommendation`。
6. 加入 forbidden dependency checks，确保 classifier 不调用 replay、
   autonomous run、LLM provider、raw HTML parser、LearnedPath write-back 或
   browser continuation。
7. 只在未来人工审核 plan 后进入实现，不在本轮执行。

## 未来分类优先级草案

进入 implementation 前必须人工审核最终 precedence。初始建议：

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

## 未来分类规则草案

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

## 未来测试计划

未来 implementation 应覆盖：

- successful replay without postcondition evidence -> `uncertain` +
  `needs_review` recommendation；
- failed replay -> `failure` + `stop` 或 future retry consideration boundary；
- drifted replay -> `failure` + evidence reference；
- missing `target_url` / `learned_path_id` -> `blocked` + `ask_user`；
- `needs_review=true` reporter payload -> `needs_review`；
- conflicting signals follow the documented classification precedence while
  preserving secondary evidence in reason / evidence references；
- explicit postcondition evidence + `task_verified=true` ->
  `success_no_recovery_needed`；
- repeated drift / stale path evidence -> `suggest_reteach` recommendation，
  但无 LearnedPath write-back；
- no raw HTML, no LLM provider, no autonomous run, no replay execution；
- user abort signal 不进入 12.1 classifier，交给 12.2。

## 验收标准

未来 12.1 implementation 才能声称完成的条件：

- classifier 输出包含 classification、reason、evidence references 和 boundary
  recommendation。
- classifier 不执行 retry、replan、browser continuation、recovery proposal、
  hidden relearning 或 LearnedPath write-back。
- classifier 不读取 raw HTML 做自由规划，不依赖默认 LLM provider。
- 所有 classification 和 boundary recommendation 都有 deterministic tests。
- 文档和 review 记录清楚说明 12.1 与 12.2 / 12.3 / 12.4 的边界。

## 本轮验证

本轮只运行文档级静态检查：

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

不运行 API / CLI / E2E / `verify-scenario`。
