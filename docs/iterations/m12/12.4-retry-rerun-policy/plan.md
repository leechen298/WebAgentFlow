# 12.4 Design Package Plan

状态：implemented

## 输入

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `review.md`
- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`
- 12.1 / 12.2 / 12.3 recovery code and tests

## 文件 / 模块

**设计包生成：**

- `docs/iterations/m12/12.4-retry-rerun-policy/README.md` - 新建代码型迭代包索引和门禁状态。
- `docs/iterations/m12/12.4-retry-rerun-policy/intent.md` - 新建目标、动机、边界和成功标准。
- `docs/iterations/m12/12.4-retry-rerun-policy/contract.md` - 新建 retry policy 概念、状态、schema、evidence 和兼容性契约。
- `docs/iterations/m12/12.4-retry-rerun-policy/technical-design.md` - 新建 future schema / evaluator / data flow 设计。
- `docs/iterations/m12/12.4-retry-rerun-policy/test-plan.md` - 新建 unit matrix 和未运行项。
- `docs/iterations/m12/12.4-retry-rerun-policy/review.md` - 新建本次设计包生成记录。
- `docs/iterations/m12/README.md` - 同步 12.4 状态。
- `docs/iterations/m12/m12-plan.md` - 同步 12.4 状态。

**代码实现：**

- `apps/api/app/schemas/recovery.py`
- `apps/api/app/services/recovery/retry_policy.py`
- `apps/api/tests/test_retry_policy.py`
- `apps/api/app/services/recovery/__init__.py`
- `apps/api/tests/test_recovery_exports.py`

## 步骤

**Design package generation 已完成并通过审核。代码实现已按本包完成。**

### Round 1 · Design package

1. 执行 precheck：同步 `v0.2`，确认工作区 clean，确认 12.3 proposal generator
   和 package-level recovery exports 存在。
2. 阅读 iteration templates、docs-local guidance、M12 README / plan、12.1 /
   12.2 / 12.3 文档和 recovery schema / services。
3. 创建 12.4 七件套：
   `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
   `test-plan.md`、`plan.md`、`review.md`。
4. 最小同步 M12 README / m12-plan 的 12.4 状态。
5. 运行文档级静态检查和七件套存在性检查。
6. 将实际验证结果回填到 `review.md`。
7. 只 stage `docs/iterations/m12`，确认 staged diff 只包含 M12 文档。
8. 本地提交，不 push。

### Round 2 · Code implementation

1. 阅读 12.4 `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
   `test-plan.md`、`plan.md`、`review.md`。
2. 在 `apps/api/app/schemas/recovery.py` 增加 retry policy schema。
3. 新增 `apps/api/app/services/recovery/retry_policy.py`，实现 deterministic
   `RetryPolicyEvaluator` 和 `evaluate_retry_policy`。
4. 在 `apps/api/app/services/recovery/__init__.py` 导出 12.4 entrypoints。
5. 新增 `apps/api/tests/test_retry_policy.py`，覆盖 `test-plan.md` 的 unit matrix。
6. 更新 `apps/api/tests/test_recovery_exports.py`，覆盖 package-level exports。
7. 运行 focused recovery suite、ruff 和 scope checks。
8. 将实现证据同步到 12.4 docs 和 M12 index。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细
测试矩阵。Round 1 执行文档级静态检查；Round 2 执行 focused recovery unit suite、
ruff 和 scope checks。

| Command | Expected proof | Notes |
|---|---|---|
| `git fetch --all --prune` | Remote refs refreshed. | Network / Git metadata write. |
| `git switch v0.2` | Current branch is `v0.2`. | If switch fails, stop. |
| `git pull --ff-only origin v0.2` | Branch is fast-forward synced. | If not fast-forward, stop. |
| `test -f` for 12.4 seven docs | 七件套全部存在。 | 文件存在性检查。 |
| `git diff --check` | 文档 diff 无 whitespace error。 | 静态检查。 |
| code/package status check | No code/package changes. | `*.py`, frontend files, package/lockfile status must be empty. |
| `find docs/iterations/m12 ... 12.5/12.6` | No 12.5 / 12.6 dirs. | Scope guard. |
| `git status --short docs/iterations/m11` | No M11 history docs changed. | Scope guard. |
| `git diff --name-only` | Only `docs/iterations/m12/**`. | Scope guard. |
| `git diff --cached --name-only` | Only `docs/iterations/m12/**`. | Staged scope guard. |
| `git diff --cached --check` | No staged whitespace errors. | Commit gate. |
| `cd apps/api && .venv/bin/python -m pytest tests/test_retry_policy.py -q` | Retry policy unit tests pass. | Implementation validation. |
| `cd apps/api && .venv/bin/python -m pytest tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py -q` | Focused recovery suite passes. | Regression validation. |
| `cd apps/api && .venv/bin/ruff check app/schemas/recovery.py app/services/recovery tests/test_retry_policy.py tests/test_recovery_proposal.py tests/test_recovery_classifier.py tests/test_user_abort_handler.py tests/test_recovery_exports.py` | Ruff clean. | Static validation. |

## 对齐清单（Alignment Checklist）

- [x] 12.4 是代码型迭代。
- [x] 12.4 包含 `technical-design.md`。
- [x] 12.4 technical design 已完成实现前审核。
- [x] `test-plan.md` 已存在，因为 12.4 涉及 recovery / retry policy。
- [x] `contract.md` 明确 `Retry policy is not retry execution`。
- [x] `technical-design.md` 只设计 future implementation，不创建代码。
- [x] `test-plan.md` 明确 API / UI / E2E / live run 不在本次执行。
- [x] plan 验证表格引用 `technical-design.md` 和 `test-plan.md`。
- [x] 验证命令已执行并记录到 `review.md`，未运行项写明 not run / unverified。
- [x] 12.4 retry policy schema、evaluator、exports 和 unit tests 已实现。
