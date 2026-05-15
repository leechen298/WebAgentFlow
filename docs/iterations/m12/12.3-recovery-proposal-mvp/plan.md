# 12.3 Implementation Plan

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

## 文件 / 模块

**Round 1 — Design package alignment:**

- `docs/iterations/m12/12.3-recovery-proposal-mvp/README.md` - 更新为代码型迭代包索引和准备状态。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/intent.md` - 更新目标、动机、边界和成功标准。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/contract.md` - 新增 proposal 概念、状态、schema、evidence 和兼容性契约。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/technical-design.md` - 新增 schema / service / data flow 设计。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/test-plan.md` - 新增 unit matrix 和未运行项。
- `docs/iterations/m12/12.3-recovery-proposal-mvp/review.md` - 按新模板记录实际验证证据。
- `docs/iterations/m12/README.md` - 同步 12.3 状态。
- `docs/iterations/m12/m12-plan.md` - 同步 12.3 状态。

**Round 2 — Code implementation（commit `b139aab`）:**

- `apps/api/app/schemas/recovery.py` - 新增 proposal schema definitions。
- `apps/api/app/services/recovery/proposal.py` - 新增 deterministic proposal generator。
- `apps/api/app/services/recovery/__init__.py` - 新增 proposal generator 导出。
- `apps/api/tests/test_recovery_proposal.py` - 新增 35 unit tests。

**Round 3 — Docs sync（commit `f37eeba`）:**

- 更新 12.3 七件套 + M12 README / m12-plan 状态为 implemented。

## 步骤

**Round 1 — Design package alignment:**

1. 执行 precheck：显式切到 `v0.2-local`，确认工作区 clean，并审计
   `v0.2-local` 相对 `v0.2` 的本地堆叠差异。
2. 按最新 iteration templates 重写 12.3 `README.md`、`intent.md`、`plan.md`、
   `review.md`。
3. 新增 `contract.md`、`technical-design.md`、`test-plan.md`。
4. 最小同步 M12 README / m12-plan 的 12.3 状态。
5. 运行文档级静态检查和七件套存在性检查。
6. 将实际验证结果回填到 `review.md`。
7. 只 stage `docs/iterations/m12`，确认 staged diff 只包含 M12 文档。
8. 本地提交，不 push。

**Round 2 — Code implementation:**

1. 按 `contract.md` 和 `technical-design.md` 实现 proposal schema（`recovery.py`）。
2. 实现 deterministic proposal generator（`proposal.py`）。
3. 实现 unit tests（`test_recovery_proposal.py`）。
4. 运行 `pytest tests/test_recovery_proposal.py -v` 和 `ruff check`。
5. 验证 12.1 / 12.2 测试无回归。
6. 本地提交，不 push。

**Round 3 — Docs sync:**

1. 更新 12.3 七件套状态为 implemented。
2. 同步 M12 README / m12-plan。
3. 本地提交，不 push。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细
测试矩阵。

### Round 1 — Design package alignment

文档级静态检查，不运行代码测试。

| Command | Expected proof | Notes |
|---|---|---|
| `git switch v0.2-local` | 当前工作树位于 local-only staging branch。 | 如果分支不存在，停止报告。 |
| `git merge-base --is-ancestor v0.2 v0.2-local` | `v0.2-local` 正确堆叠在 `v0.2` 之上。 | exit code 必须为 0。 |
| `test -f` for 12.3 seven docs | 七件套全部存在。 | 文件存在性检查。 |
| `git diff --check` | 文档 diff 无 whitespace error。 | 静态检查。 |

### Round 2 — Code implementation

| Command | Expected proof | Notes |
|---|---|---|
| `pytest tests/test_recovery_proposal.py -v` | 35 passed | Proposal unit tests. |
| `pytest tests/test_recovery_classifier.py tests/test_user_abort_handler.py -v` | 38 passed | 12.1 / 12.2 regression. |
| `ruff check ...` | All checks passed | Lint clean. |

### Round 3 — Docs sync

| Command | Expected proof | Notes |
|---|---|---|
| `git diff --name-only` | Only `docs/iterations/m12/**` | Scope guard. |
| `git diff --check` | No whitespace errors | Static check. |

## 对齐清单（Alignment Checklist）

- [x] 12.3 仍然匹配 `contract.md`。
- [x] 12.3 是代码型迭代，已经包含 `technical-design.md`。
- [x] `test-plan.md` 已存在并与技术设计 Test Matrix 一致。
- [x] plan 验证表格引用 `technical-design.md` 和 `test-plan.md`。
- [x] 12.3 已实现 proposal schema / generator / tests（`b139aab`）。
- [x] 73 tests passed, ruff clean。
- [x] API / CLI / DB / frontend / E2E / live run 不在本轮范围。
- [x] 验证命令已执行并记录到 `review.md`，未运行项写明 not run / unverified。
