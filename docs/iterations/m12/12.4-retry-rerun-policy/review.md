# 12.4 Review and Reflection

状态：proposed

## 2026-05-15 设计包生成（Design Package Generation）

- Reviewer：documentation package self-check
- Decision：design package generated
- Notes：本次按最新 iteration templates 创建 12.4 代码型迭代完整设计包。

## 用户反馈

- 要求 12.4 生成代码型迭代完整设计包 -> accepted。
- 要求表达为“本次提交交付设计包，后续实现以设计包为输入”，避免写成禁止开发 ->
  accepted。
- 要求本次只修改 `docs/iterations/m12/**`，不写代码、不跑 API / CLI / E2E /
  `verify-scenario` -> accepted。
- 要求 12.4 核心原则固定为 retry policy 不等于 retry execution -> accepted。
- Review P3：future confirmation marker 不应命名得像执行触发器 -> accepted；
  design now recommends `has_user_confirmation_marker` and states it affects
  policy outcome only.
- Review P3：`abandon_task` policy outcome 不应保留二选一 -> accepted；
  design now defaults `abandon_task` to `no_retry_needed`.

## 最终差异（Final Delta）

### 实际交付

- 新建 12.4 `README.md`：代码型迭代包索引、当前状态和门禁 checklist。
- 新建 12.4 `intent.md`：goal、motivation、boundary / non-goals、success criteria。
- 新建 12.4 `contract.md`：retry policy concepts、outcomes、reasons、schema/API、
  evidence、compatibility、不变契约和非目标。
- 新建 12.4 `technical-design.md`：future retry policy schema / evaluator /
  data flow / compatibility / edge cases / validation commands。
- 新建 12.4 `test-plan.md`：future retry policy unit matrix 和 not-run boundaries。
- 新建 12.4 `plan.md`：实施步骤、验证表格和对齐清单。
- 新建 12.4 `review.md`：本次设计包生成记录。
- 更新 M12 README / m12-plan：12.4 标记为 proposed / current design package，
  12.5 / 12.6 保持 future。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- None so far. 本次只做 design package generation，不实现 code。

### Review-fix notes

- `technical-design.md` 的 future evaluator signature 将 `user_confirmed`
  收紧为 `has_user_confirmation_marker`，并明确该 marker 不触发 retry execution。
- `contract.md` 的 evidence / unresolved question 已同步为
  `has_user_confirmation_marker`。
- `test-plan.md` 和 `technical-design.md` 已将 `abandon_task` 的默认 retry policy
  outcome 固定为 `no_retry_needed`。

### WebAgentFlow Live Run 边界（Live Run Boundary）

12.4 design package generation 未触发 `verify-scenario`、autonomous run 或
product-driven browser execution。不产生 `run_id`。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 没有打开浏览器或产品 UI。
- 没有运行 CLI / API / E2E。
- 所有 live / E2E 项标记为 `not run` / `unverified`。

## 验证证据（Validation Evidence）

没运行的项不得写成 tested。以下只记录本次实际执行过的文档级静态检查。

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| 12.4 seven-doc existence check | All seven files exist | No output | 0 | PASS | command output | `README.md`, `intent.md`, `contract.md`, `technical-design.md`, `test-plan.md`, `plan.md`, `review.md`. |
| `git diff --check` | No whitespace errors | No output | 0 | PASS | command output | Docs-only static check. |
| code/package status check | No code/package changes | No output | 0 | PASS | command output | Scope guard for `*.py`, frontend files, package files, lockfiles. |
| `find docs/iterations/m12 ... 12.5/12.6` | No output | No output | 0 | PASS | command output | Scope guard. |
| `git status --short docs/iterations/m11` | No output | No output | 0 | PASS | command output | M11 history guard. |
| `git diff --name-only` | Only `docs/iterations/m12/**` tracked changes | `docs/iterations/m12/README.md`; `docs/iterations/m12/m12-plan.md` | 0 | PASS | command output | New 12.4 directory is untracked until staging; staged scope check covers it. |
| `git status --short` | Only `docs/iterations/m12/**` changes | M12 README / m12-plan modified; 12.4 directory untracked | 0 | PASS | command output | Workspace scope guard. |
| `git diff --cached --name-only` | Only `docs/iterations/m12/**` | 9 M12 doc paths listed | 0 | PASS | command output | Staged scope guard. |
| `git diff --cached --check` | No whitespace errors | No output | 0 | PASS | command output | Commit gate. |

## 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API tests | 12.4 design package 不新增 route 或 response contract。 | None for docs-only package. |
| CLI tests | 12.4 design package 不改 CLI。 | None for docs-only package. |
| Unit tests | 12.4 design package 不创建 retry policy code。 | Future implementation must run retry policy unit tests and recovery regressions. |
| E2E / UI smoke | 12.4 design package 不接 UI / browser flow。 | UI behavior unverified by design. |
| `verify-scenario` / autonomous run | 12.4 design package 不触发 live autonomous run。 | Product runtime not exercised by design. |

## 2026-05-15 Review-fix Validation

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Notes |
|---|---|---|---|---|---|
| `git diff --check` | No whitespace errors | No output | 0 | PASS | Docs-only static check. |
| code/package status check | No code/package changes | No output | 0 | PASS | Scope guard. |
| `git status --short docs/iterations/m11` | No output | No output | 0 | PASS | M11 history guard. |
| `find docs/iterations/m12 ... 12.5/12.6` | No output | No output | 0 | PASS | Scope guard. |
| `git diff --name-only` | Only 12.4 docs changed | 4 paths under `12.4-retry-rerun-policy/` | 0 | PASS | Review-fix scope guard. |
| `rg user_confirmed / no_retry_needed or retry_denied` | No stale active design wording | Only historical review-fix note mentions `user_confirmed`; no `no_retry_needed or retry_denied` remains. | 0 | PASS | Confirms design wording tightened. |

## 后续事项（Follow-ups）

- 进入 12.4 implementation 前，需要人工审核 `contract.md`、
  `technical-design.md`、`test-plan.md` 和 `plan.md`。
- 12.4 implementation 应创建 retry policy schema、deterministic evaluator 和
  focused unit tests；不要接 API / CLI / conversation dispatcher / browser action。
- 12.1 / 12.2 历史包仍是旧四件套，缺少新模板的 `contract.md` /
  `technical-design.md` / `test-plan.md`。本次不回填；如需治理应另开文档任务。
- `recommended_option_kinds` 当前仍是 12.3 proposal 的 display emphasis only；
  进入 12.5 conversation flow 前可继续评估是否重命名为更明确的 display-order 字段。
