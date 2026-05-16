# 12.5 Design Package Plan

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
- 12.1 / 12.2 / 12.3 / 12.4 recovery code and tests
- M11.0 conversation schema / state / orchestrator code

## 文件 / 模块

**本次设计包生成：**

- `docs/iterations/m12/12.5-recovery-conversation-flow/README.md` - 新建代码型迭代包索引和当前状态。
- `docs/iterations/m12/12.5-recovery-conversation-flow/intent.md` - 新建目标、动机、边界和成功标准。
- `docs/iterations/m12/12.5-recovery-conversation-flow/contract.md` - 新建 conversation response / choice / event / state / evidence 契约。
- `docs/iterations/m12/12.5-recovery-conversation-flow/technical-design.md` - 新建 future schema / pure service / data flow 设计。
- `docs/iterations/m12/12.5-recovery-conversation-flow/test-plan.md` - 新建 future unit / limited integration matrix 和未运行项。
- `docs/iterations/m12/12.5-recovery-conversation-flow/review.md` - 新建本次设计包生成记录。
- `docs/iterations/m12/README.md` - 同步 12.5 状态。
- `docs/iterations/m12/m12-plan.md` - 同步 12.5 状态。

**后续实现提交可触及，但本次不创建或修改：**

- `apps/api/app/schemas/recovery.py`
- `apps/api/app/services/recovery/conversation_flow.py`
- `apps/api/app/services/conversation/orchestrator.py`
- `apps/api/app/services/conversation/state.py`
- `apps/api/tests/test_recovery_conversation_flow.py`
- `apps/api/tests/test_conversation_recovery_flow.py`

## 步骤

1. 执行 precheck：同步 `v0.2`，确认工作区 clean，确认 HEAD 包含 `f1c2606` 或后续提交。
2. 确认 `12.5-recovery-conversation-flow/` 和 `12.6-*` 不存在。
3. 阅读 iteration templates、M12 README / plan、12.3 / 12.4 design packages、
   recovery services、conversation schema / state / orchestrator。
4. 创建 12.5 七件套：
   `README.md`、`intent.md`、`contract.md`、`technical-design.md`、
   `test-plan.md`、`plan.md`、`review.md`。
5. 最小同步 M12 README / m12-plan 的 12.5 状态。
6. 运行七件套存在性检查、文档级静态检查和 scope checks。
7. 将实际验证结果回填到 `review.md`。
8. 只 stage `docs/iterations/m12`，确认 staged diff 只包含 M12 文档。
9. 本地提交，不 push。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细
测试矩阵。本次作为 docs-only design package generation，只执行文档级静态检查。

| Command | Expected proof | Notes |
|---|---|---|
| `git fetch --all --prune` | Remote refs refreshed. | Git metadata sync. |
| `git switch v0.2` | Current branch is `v0.2`. | If switch fails, stop. |
| `git pull --ff-only origin v0.2` | Branch is fast-forward synced. | If not fast-forward, stop. |
| `test -f` for 12.5 seven docs | 七件套全部存在。 | 文件存在性检查。 |
| `git diff --check` | 文档 diff 无 whitespace error。 | 静态检查。 |
| code/package status check | No code/package changes. | `*.py`, frontend files, package/lockfile status must be empty. |
| `find docs/iterations/m12 ... 12.6` | No 12.6 dirs. | Scope guard. |
| `git status --short docs/iterations/m11` | No M11 history docs changed. | Scope guard. |
| `git diff --name-only` | Only `docs/iterations/m12/**`. | Scope guard. |
| `git diff --cached --name-only` | Only `docs/iterations/m12/**`. | Staged scope guard. |
| `git diff --cached --check` | No staged whitespace errors. | Commit gate. |

## 对齐清单（Alignment Checklist）

- [x] 12.5 是代码型迭代。
- [x] 12.5 包含 `technical-design.md`。
- [x] `test-plan.md` 已存在，因为 12.5 涉及 recovery / conversation flow。
- [x] `contract.md` 明确 conversation flow is not execution。
- [x] `technical-design.md` 只设计 future implementation，不创建代码。
- [x] `test-plan.md` 明确 API / UI / E2E / live run 不在本次执行。
- [x] plan 验证表格引用 `technical-design.md` 和 `test-plan.md`。
- [x] 验证命令执行结果记录到 `review.md`，未运行项写明 not run / unverified。
