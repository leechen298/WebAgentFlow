# 复盘 / 评审（Review）

状态：implementation complete（implementation review passed, UI smoke pending）

## 2026-05-17 设计初始化（Design Draft）

- Reviewer：N/A
- Decision：passed_with_minor_changes
- Notes：按用户要求新增 11.3.2 Chat History & Debug Console 迭代文档。当前仅生成文档，未实现代码。

## 2026-05-17 设计评审（Design Review）

- Reviewer：User
- Decision：passed_with_minor_changes
- Notes：文档可作为 M11.3.2 的需求 / 设计输入进入实现阶段。需要把 Console manual route smoke 调整为最终验收必需，补充 `learning_runs` / `replay_summaries` normalized shape，并在 contract 明确 session list 默认 `updated_at desc` 及时间过滤边界。

## 2026-05-17 实现评审（Implementation Review）

- Reviewer：Codex external reviewer
- Decision：passed_with_ui_smoke_pending
- Notes：API / CLI / Console implementation matched the scoped contract after review fixes. Final acceptance is still blocked on MANUAL-1 Console route smoke.

## 用户反馈

- “新增一个迭代来做。” -> accepted，创建独立 `11.3.2-chat-history-debug-console` 迭代。
- “现有迭代文档不要动。” -> accepted，未修改既有具体迭代目录。
- “11.3.2吧。总的规划文档可以相应修改。” -> accepted，允许同步 M11 总规划入口。
- “Console manual route smoke 不应该是 optional。” -> accepted，改为 final acceptance required。
- “`learning_runs` / `replay_summaries` 的 extraction 规则可以再具体一点。” -> accepted，补 normalized shape。
- “列表接口可以明确排序和时间边界。” -> accepted，contract / technical design 明确 `updated_at desc` 和 `updated_at` 过滤。

## 最终差异（Final Delta）

### 实际交付

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`
- Review follow-up fixes:
  - Console manual route smoke is required before final acceptance.
  - `learning_runs` / `replay_summaries` have normalized extraction shapes.
  - Session list sorting and time filter semantics are explicit.

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- Console manual route smoke 尚未执行，因此当前状态只能是 implementation complete / UI smoke pending，不能写 accepted。

### WebAgentFlow Live Run 边界（Live Run Boundary）

本轮未触发 `verify-scenario`、autonomous run 或 product-driven browser execution。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

- E2E：not run。
- UI smoke：not run。
- CLI runtime：CLI pytest passed; interactive product smoke not run。
- Codex 做了代码 review、scoped pytest 复核和静态检查；未触发 live autonomous run。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---:|---|---|---|
| `git diff --check` | no whitespace errors | no output | 0 | Pass | local command output | 文档生成后执行 |
| `../../.venv/bin/pytest tests/test_conversation.py tests/test_chat.py -q` from `apps/cli` | CLI scoped tests pass | `30 passed in 0.08s` | 0 | Pass | local command output | M11.3.2 CLI surface |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_repo.py -q` from `apps/api` | M11.3.2 API / repo tests pass, known baseline failures documented | `4 failed, 88 passed in 0.60s` | 1 | Partial | local command output | 4 failures are existing dispatch replay tests, not introduced by history/debug surface |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| API full green | scoped run still has 4 known dispatch replay baseline failures | Do not claim API pytest is fully green until baseline is fixed or excluded with rationale |
| Console tests | Implementer reported Vitest / type-check clean; not rerun during final commit prep | Preserve report as implementation evidence; rerun if final acceptance needs fresh proof |
| UI smoke | Console route smoke not run | Required before final acceptance |
| live autonomous run | 本轮不需要也不允许默认触发 | 无；本轮是 history read/debug surface |

### 后续事项（Follow-ups）

- 执行 MANUAL-1：启动产品服务并真实打开 `/conversation/history` 和详情页，记录 route smoke evidence 后才可进入 accepted。
