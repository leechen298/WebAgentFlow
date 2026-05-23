# 复盘 / 评审（Review）

状态：in_progress

## 2026-05-23 文档草案

- Author：Codex
- Decision：docs_created
- Notes：
  - 基于用户与 ChatGPT 的讨论，新增 11.3.7 用户视角 WAgent 行为 eval 文档包。
  - 本包定位为 11.3.6 之后的下一阶段验收定义，不实现 runtime 代码。
  - 明确 11.3.6 只证明 runtime 受控执行能力，不能代表页面级自动操作学习或完整产品预期通过。
  - 明确第一批 case：URL-only known、URL-only unknown、execute-known、execute-unknown、
    vague-input。
  - 明确后续扩展：explicit learn、pending continuation、choice selection、recovery menu、
    page capability discovery、multi-operation learning、natural-language reuse。
  - 新增 anti-hardcoding hard gate：测试页面链接及其相关内容不得出现在功能代码或产品 prompt 中。

## 用户反馈

- “M11.3.6 closeout 的测试通过，但结论口径需要修正。” -> accepted。
- “当前测试只证明 chat runtime 对已学习路径的参数化复用、evidence reporting、pending choice /
  planner choice / recovery menu。” -> accepted。
- “它没有证明 WAgent 能自动学习页面所有操作、从新页面生成完整操作库、任意页面任务自动命中并执行。”
  -> accepted。
- “新增下一阶段 proposal：11.3.7 Page Capability Learning Eval / User-facing WAgent Behavior Eval。”
  -> accepted，采用 `11.3.7-user-facing-wagent-behavior-eval`，并把 page capability learning 放入后续扩展。
- “必须严格禁止需要测试的页面链接及其相关内容，出现在功能的代码和提示词中。” -> accepted，
  写入 contract、technical design、test plan 和 review checklist。
- “因为出现的话，可能会出现针对性的实现功能，影响整体产品。” -> accepted，作为
  forbidden-token hard gate 的动机。

## 最终差异（Final Delta）

### 实际交付

- Created 11.3.7 iteration documentation package.
- Updated M11 index / plan and 11.3.6 closeout wording to separate runtime component acceptance
  from user-facing product behavior acceptance.
- No runtime code changed.

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- None for docs draft.

### WebAgentFlow Live Run 边界（Live Run Boundary）

本轮没有触发 `verify-scenario`、autonomous run、Console UI smoke 或 product-driven browser
execution。

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

本轮是 docs-only drafting。没有运行未来 11.3.7 eval runner，因此不得声称 11.3.7 已测试或通过。

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `find docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval -maxdepth 1 -type f | sort` | Seven docs exist | Seven files listed: README, intent, contract, technical-design, test-plan, plan, review | 0 | Pass | command output | Docs package is complete |
| `rg -n "11\\.3\\.7|User-facing WAgent Behavior Eval|测试页面链接|forbidden-token|runtime execution capabilities" docs/iterations/m11 docs/testing/wagent-runtime-eval.md docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md` | Scope correction discoverable | Matches found in M11 index / plan, 11.3.6 program docs, closeout docs, runtime eval docs and 11.3.7 package | 0 | Pass | command output | Scope correction is discoverable |
| placeholder scan for template tokens | No template placeholders | No matches | 1 | Pass | command output | exit `1` means `rg` found no matches |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| `pnpm run eval:wagent:user-behavior` | Runner not implemented in this docs draft | User-facing behavior remains unverified |
| Unit / API tests | No code changed | Runtime regressions are not assessed by this docs-only change |
| Console UI smoke | Not requested | UI-specific behavior remains unverified |
| `verify-scenario` / autonomous run | Out of scope and prohibited by default | No Supervisor pass_gate evidence claimed |

### 后续事项（Follow-ups）

- Review and approve 11.3.7 docs before implementation.
- Implement forbidden-token scanner before behavior cases.
- Keep target-specific test content out of feature code and product prompt assets.
