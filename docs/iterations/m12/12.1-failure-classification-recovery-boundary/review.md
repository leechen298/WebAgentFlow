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


## 2026-05-14 Code Review (Claude, codex-review unavailable)

**背景**: 用户触发 `codex-review` skill 对 commit `c84de75` 做独立第二意见审核，
但 Codex CLI (v0.123.0) 在当前 ChatGPT 账户环境下无法调用任何可用模型
(gpt-5.5 / o3 / gpt-4o / o4-mini / o3-mini 均报 `not supported when using Codex with a ChatGPT account`)。
因此本次审核由 Claude 基于完整代码阅读完成，**不是 Codex 的独立第二意见**。

**审核范围**: commit `c84de75493e3a9077d0d4964b8f57b15b63142fe`
- `apps/api/app/schemas/recovery.py`
- `apps/api/app/services/recovery/__init__.py`
- `apps/api/app/services/recovery/classifier.py`
- `apps/api/tests/test_recovery_classifier.py`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/plan.md`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/review.md`

**测试状态**: `16 passed` (pytest), ruff clean.

**重点审核的 6 个边界结论**:

1. **只做 deterministic classifier + boundary recommendation** — ✅ 符合。
   无 API router、CLI、DB、conversation dispatcher、retry execution、abort handling、
   proposal generation、LearnedPath write-back 等代码或依赖。

2. **retry_candidate 不覆盖强安全边界** — ✅ 符合。
   `retry_candidate=True` 仅在 `_failure_recommendation` 中且 `reason == "replay_failed"`
   时返回 `retry_possible_requires_confirmation`。blocked/unsupported/unsafe/auth/missing
   context 均返回 `ask_user` 或 `stop`，测试也覆盖了 permission/auth block 场景。

3. **success 只来自 task_verified=True + explicit postcondition_evidence** — ✅ 符合。
   `classify` 中 success 路径的条件是 `data.task_verified and data.postcondition_evidence`，
   空列表因 `bool([])` 为 False 不会进入 success。

4. **uncertain / needs_review / replay completed 不会被说成 success** — ✅ 符合。
   replay completed 但无 postcondition evidence 被 `_is_uncertain` 拦截；needs_review
   在 success 之前检查；无信号输入 fallback 到 needs_review。

5. **无超出 12.1 范围的依赖** — ✅ 符合。
   classifier 仅导入 `collections.abc.Mapping`、`typing.Any` 和内部 schema。
   `test_classifier_module_has_no_forbidden_dependencies` 覆盖了常见禁忌 token。

6. **tests 覆盖 precedence、retry guard、input immutability、forbidden imports** — ✅ 符合。
   测试覆盖了 blocked>failure、failure>uncertain、uncertain>needs_review、
   retry candidate boundary marker、retry guard、input immutability、evidence references、
   forbidden dependency source scan。

---

### 分级发现

#### Critical
无。

#### Should-fix

- `classifier.py:222-224` — `_message` 在 `classification == "failure"` 且
  `data.retry_candidate` 为 True 时，统一返回 "stronger safety policy still applies"。
  但当 `reason` 为 `target_missing` / `replay_drifted` / `stale_or_missing_path_coverage`
  时，`_failure_recommendation` 实际返回的是 `suggest_reteach`，而非
  `retry_possible_requires_confirmation`。message 与 recommendation 不一致，
  可能误导调用方。建议按 `recommendation` 分发 message，而不是仅按 `retry_candidate` flag。

#### Nit

- `classifier.py:156` — `_failure_recommendation` 返回类型注解为 `str`，
  应为 `BoundaryRecommendation`（或至少与 Literal 对齐）。
- `test_recovery_classifier.py:230-247` — forbidden dependency 检查只覆盖了
  `classifier.py` 源码，未覆盖 `__init__.py`。当前 `__init__.py` 无额外 import，
  但建议扩展检查范围或留注释说明。
- `test_recovery_classifier.py:169` — `assert "execut" not in result.message.lower()`
  过于宽泛（会同时排除 execution/executive 等），建议改为更明确的子串检查。

#### Disagree
无。


## M12.1 P3 Review-Fix Report

### Priority summary

- P0/P1/P2: none
- P3 fixed:
  - P3-1: `_message` now dispatches by final `recommendation` instead of `retry_candidate` flag alone.
  - P3-2: Added future adapter follow-up note in review.md.
  - P3-3: Confirmed "unknown side effect(s)" maps to `unsafe_or_unknown_state` + `stop`.
- Nit fixed:
  - Nit-1: `_failure_recommendation` return type changed from `str` to `BoundaryRecommendation`.
  - Nit-2: Forbidden dependency test now covers both `classifier.py` and `services/recovery/__init__.py`.
  - Nit-3: Retry message assertions tightened to exclude specific execution phrases.

### Modified files

- `apps/api/app/services/recovery/classifier.py`
- `apps/api/tests/test_recovery_classifier.py`
- `docs/iterations/m12/12.1-failure-classification-recovery-boundary/review.md`

### Behavior changes

- **Message / recommendation consistency**: `failure` messages now align with the actual boundary recommendation:
  - `retry_possible_requires_confirmation` -> future retry policy message.
  - `suggest_reteach` -> re-teach / update learned path message.
  - `stop` -> stop or route to later recovery planning.
- **Retry candidate guard**: Unchanged; still only allows `retry_possible_requires_confirmation` for `replay_failed`, and never overrides blocked / unsafe / auth / missing context.
- **Unknown side effects handling**: `blocked_reason` containing "unknown side effect" or "unknown side effects" now correctly maps to `unsafe_or_unknown_state` with recommendation `stop`.
- **Forbidden dependency test scope**: Expanded to scan both implementation files in the recovery service package.

### P3-2 Follow-up: TaskResultReporter -> RecoveryEvidence adapter

Future integration should add a `TaskResultReporter.event_payload -> RecoveryEvidence` adapter or integration test.

Current classifier success requires:

```text
task_verified=True + explicit postcondition_evidence
```

But Task Result Reporter's existing payload is closer to:

```text
evidence_summary
missing_evidence_summary
task_verified
verification_outcome
```

Before connecting conversation / recovery flow, the mapping from reporter payload to `RecoveryEvidence` must be confirmed, to avoid verified results being downgraded to `uncertain` due to missing `postcondition_evidence`.

This is a follow-up only; no adapter implementation in this round.

### P3-3 Confirmation: unknown side effects

Confirmed that `blocked_reason` values containing "unknown side effect" or "unknown side effects" are classified as `unsafe_or_unknown_state` with recommendation `stop`.

### Tests

- `git diff --check`: clean
- pytest: `19 passed` (was 16, added 3 new tests)
- ruff: `All checks passed!`
- frontend/package/lockfile status: no changes
- 12.2/12.3/12.4 dirs: not created
- M11 history docs: untouched

### Commit

- Commit hash: see `git log --oneline -1` on `v0.2-local`
- Commit message: `fix(m12): polish recovery classifier boundaries`

### Notes / risks

- No API / CLI / DB / frontend / E2E / M11 docs / 12.2+ docs modified.
- No behavioral regression in classification precedence or safety boundaries.
- Message changes are additive / clarifying; they do not alter the deterministic classification logic.
