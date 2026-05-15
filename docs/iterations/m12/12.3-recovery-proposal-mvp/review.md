# 12.3 Review and Reflection

状态：implemented

## 2026-05-15 设计包对齐（Design Package Alignment）

- Reviewer：documentation alignment self-check
- Decision：design package aligned
- Notes：本轮按最新 iteration templates 将 12.3 从旧四件套对齐为代码型迭代完整设计包。

## 用户反馈

- 要求 12.3 按代码型迭代文档规范补齐 `README.md`、`intent.md`、`contract.md`、
  `technical-design.md`、`test-plan.md`、`plan.md`、`review.md` -> accepted。
- 要求本轮只改 `docs/iterations/m12/**`，不写代码、不跑 API / CLI / E2E /
  `verify-scenario` -> accepted。
- 要求审计 `v0.2-local` 相对 `v0.2` 的本地堆叠差异 -> accepted。
- 要求检查 12.3 七件套存在性 -> accepted。
- 要求实现 12.3 proposal schema / generator / tests -> accepted。

## 最终差异（Final Delta）

### 实际交付

**Round 1 — Design package alignment:**

- 12.3 `README.md` 更新为代码型迭代包索引和准备状态。
- 12.3 `intent.md` 更新为 design package alignment 语义。
- 新增 12.3 `contract.md`。
- 新增 12.3 `technical-design.md`。
- 新增 12.3 `test-plan.md`。
- 12.3 `plan.md` 更新为新模板结构。
- 12.3 `review.md` 更新为新模板结构。
- M12 README / m12-plan 同步 12.3 为 proposed / current design package。

**Round 2 — Code implementation（commit `b139aab`）:**

- 新增 `apps/api/app/services/recovery/proposal.py` — deterministic
  `RecoveryProposalGenerator`。
- 新增 `apps/api/tests/test_recovery_proposal.py` — 36 unit tests after
  schema-polish review fix。
- `apps/api/app/schemas/recovery.py` — 新增 `RecoveryProposal`、
  `RecoveryProposalOption`、`RecoveryProposalKind`、`ProposalSource`、
  `ProposalRiskHint`、`ProposalConfirmationRequirement`、`ProposalOwner`。
- `apps/api/app/services/recovery/__init__.py` — 新增
  `RecoveryProposalGenerator`、`generate_recovery_proposal` 导出。
- Reviewer P2 修复：`needs_manual_review` + `inflight_caveat=True` 时保留
  `inflight_action_risk` / `side_effects_unknown` risk hints。
- Reviewer P3 修复：abort flow 填充 proposal-level `evidence_refs`。

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- Round 1：None。与 design package alignment 计划一致。
- Round 2：
  - P1 branch 偏差：初始实现误提交到 `v0.2` 而非 `v0.2-local`；已 reset 并迁到
    `v0.2-local`。
  - P2 inflight risk：`needs_manual_review` + `inflight_caveat=True` 时遗漏
    `inflight_action_risk` / `side_effects_unknown` risk hints；已修复。
  - P3 top-level evidence：abort flow 的 `RecoveryProposal.evidence_refs` 为空；已修复。

### WebAgentFlow Live Run 边界（Live Run Boundary）

12.3 未触发 `verify-scenario`、autonomous run 或 product-driven browser
execution。不产生 `run_id`。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- 没有打开浏览器或产品 UI。
- 没有运行 CLI / API / E2E。
- 所有 live / E2E 项标记为 `not run` / `unverified`。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `pytest tests/test_recovery_proposal.py -v` | 36 passed | 36 passed | 0 | PASS | command output | Proposal unit tests. |
| `pytest tests/test_recovery_classifier.py tests/test_user_abort_handler.py -v` | 38 passed | 38 passed | 0 | PASS | command output | Regression: 12.1 + 12.2 tests. |
| `pytest ... (all 3 combined)` | 74 passed | 74 passed | 0 | PASS | command output | Full recovery suite. |
| `ruff check ...` | All checks passed | All checks passed | 0 | PASS | command output | Lint clean. |
| `git branch --show-current` | `v0.2-local` | `v0.2-local` | 0 | PASS | command output | Branch gate. |
| `test -d docs/iterations/m12/12.3-recovery-proposal-mvp` | EXISTS | EXISTS | 0 | PASS | command output | Design docs on branch. |
| `git diff --cached --name-only` | 4 expected files | 4 files listed | 0 | PASS | command output | Staged scope correct. |
| `git diff --cached --check` | No whitespace errors | No output | 0 | PASS | command output | Staged whitespace clean. |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API tests | 12.3 不新增 route 或 response contract。 | None. |
| CLI tests | 12.3 不改 CLI。 | None. |
| E2E / UI smoke | 12.3 不接 UI / browser flow。 | UI behavior unverified by design. |
| `verify-scenario` / autonomous run | 12.3 不触发 live autonomous run。 | Product runtime not exercised by design. |

### 后续事项（Follow-ups）

- 12.4 retry policy 和 12.5 conversation flow 可基于 12.3 proposal schema 继续。
- `recommended_option_kinds` 当前更像 display order；12.5 接入时可考虑改名为
  `display_order_kinds` 或在 docs/tests 中明确它只是排序/强调。
- `non_executable` 已升级为 schema-level `Literal[True]`，并用单元测试锁住
  `non_executable=false` 会被拒绝。
- 12.0 / 12.1 / 12.2 历史包仍是旧四件套；是否按新模板回填由后续文档治理任务决定。
