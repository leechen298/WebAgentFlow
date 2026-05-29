# Iteration Documentation Agent Rules

状态：process standard

英文版本：`AGENTS.md`。

本文件约束 `docs/iterations/` 下的文档工作。仓库根目录的 `AGENTS.md`、
`CLAUDE.md` 和 `CLAUDE.zh.md` 仍然约束全仓行为。本文件定义 milestone plan、
umbrella recovery plan、planned package、具体 iteration package、validation
plan、evidence 和 review 文档必须达到的详细程度。

本文件不实现、也不定义外部自动化控制器。

## Purpose

创建或修改 `docs/iterations/` 下文件时使用本文件。它把 iteration 文档应有的详细程度
写成明确规则，避免后续 agent 只能从示例中猜 scope、evidence 要求、compatibility
constraints 或 closeout 状态。

这些规则适用于：

- `m<N>-plan.md` 这类 milestone plan；
- 把工作拆成多个 child package 的父级 umbrella package `plan.md`；
- 这些计划里的 planned package 条目；
- 具体 iteration package；
- validation plan；
- post-closeout validation 文档；
- review 和 evidence 记录。

## Plan-Compatible Documentation Generation Standard

当 agent 被要求创建或修改 iteration 文档时，文档生成阶段应该先像一个精简版
`/plan` run 一样工作，然后才允许进入任何 runtime implementation。生成结果必须
decision-complete，让后续 implementation agent 可以直接按文档执行，不需要再猜
package type、scope、gates 或 stop conditions。

写入或修改 iteration 文档前，必须先识别并把这些决策写进生成后的 package docs；
通常写在 `plan.md` 和 `review.md`：

```text
target package path
package type: docs | code | mixed | validation | umbrella / campaign
parent / child relationship, if any
required document set
source-of-truth inputs already read
contract / concept / status / evidence changes
design-review gate
test-plan trigger decision
implementation authorization boundary
expected verification evidence
stop conditions
next handoff or campaign checkpoint
```

对 code 或 mixed package，生成文档不能默认授权 implementation。必须先审核
`technical-design.md`，并记录 `implementation_authorized: yes`，才能开始 code work。

对 umbrella 或 campaign package，documentation-generation plan 还必须判断是否需要
`GOAL_RUNNER.md` 和 `CURRENT_STATE.md`。如果需要，必须从模板创建；或明确记录现有
这两个文件为什么仍然是 authoritative。

如果 target package、package type、required file set、parent / child route 或
implementation boundary 无法从仓库状态安全判断，必须停为 `NEEDS_USER_INPUT`，不得生成
speculative docs。

## Planned Package Standard

任何包含多个 planned sub-iterations 的 milestone plan 或 umbrella package plan，都必须把每个 planned package
写成准迭代包规格（quasi-package specification）。

每个 planned package 必须包含这些字段：

```text
Package name
Status
Type
Goal
Why this exists
Inputs / required reading
Allowed changes
Forbidden changes
Expected deliverables
Expected tests / verification
Compatibility constraints
Scope guardrails
Exit criteria
Handoff to next package
```

硬规则：

- `README.md` 可以是 package index 或 summary。
- 详细的 milestone 或 umbrella `plan.md` 必须是执行规格。
- 只写一行 package summary 不够。
- 后续 agent 不应该再靠猜测补 scope、allowed files、forbidden files、verification、
  compatibility constraints 或 handoff state。
- 如果缺少任一 required planned-package 字段，review 至少必须记录 P2。
- 如果缺少 `Forbidden changes`、`Compatibility constraints` 或 `Scope guardrails`
  可能导致 runtime、API、schema、prompt、eval 或 evidence 越界，review 必须记录 P1。

## Milestone Index Synchronization

任何新增的 concrete package directory、umbrella package、validation package
或 planned child-package sequence，都必须同步到所属 milestone 的 `README.md`；
适用时也必须同步到 milestone plan。

milestone `README.md` 必须暴露足够信息，让后续 agent 能发现：

- package id / directory；
- package type；
- current status；
- umbrella package 的 parent / child relationship；
- 当父级 package 只定义计划时，下一个可执行 child package。

milestone plan 或 umbrella plan 仍然是执行级规格，但 milestone `README.md`
不能完全遗漏该 package。package directory 已存在但 milestone `README.md`
没有记录，是 review finding。如果该遗漏可能导致 implementation agent 从错误
package 开始，按 P1 处理；否则至少按 P2 处理。

当父级 umbrella package 的文档要求 child packages 先创建完整七件套时，该父级
umbrella package 不得被当作 code implementation package。umbrella plan 中规划的
child packages 必须列入 milestone index；或者 milestone index 必须指向父级 package，
并清楚说明下一个可执行 child package。

Review checklist：

- 检查 package directory 是否存在。
- 检查 milestone `README.md` entry 是否存在。
- 检查 milestone plan 或 parent umbrella plan 是否包含执行级 planned-package fields。
- 检查 package `README.md`、milestone `README.md` 和 plan 中的 status / type 是否一致。
- 检查 implementation 前的 child-package gate。

## Campaign Goal Runner Standard

Campaign 指任何计划让 Codex App `/goal` 跨多个 child package 连续执行的 umbrella
package 或 milestone sequence。

可能被 `/goal` 消费的 campaign 必须提供：

```text
GOAL_RUNNER.md
CURRENT_STATE.md
```

`GOAL_RUNNER.md` 是稳定的自动化契约，必须定义：

```text
authoritative inputs
default execution mode
full campaign mode
child package lifecycle
subagent delegation policy
subagent ownership and evidence requirements
runtime authorization rules
hard stops
final status vocabulary
live validation approval requirements
closeout consistency gate
required child closeout fields
```

`CURRENT_STATE.md` 是短小、可更新的路由快照，必须定义：

```text
current_mode
parent_package
parent_status
parent_authorizes_runtime_implementation
active_child_package
route_status
route_type
next_action
do_not_reimplement
handoff_source
package queue
active subagent work, when applicable
conflict rule
live validation rule, when applicable
```

默认 `/goal` campaign 行为是 `full_campaign_mode`：只有当前 child package 已达到
`PACKAGE_COMPLETE`，且 `CURRENT_STATE.md` 或 parent plan 明确列出下一包 eligible
时，Codex 才可以不等新的用户提示继续下一包。Campaign 可以选择更严格的默认策略，
例如 one child per goal，但必须在 `GOAL_RUNNER.md` 中明确写出。

因为 `/goal` campaign 属于长程开发模式，每个 checkpoint 默认必须使用
subagents。父 agent 保留 campaign 契约、路由决策、集成、验证、证据质量、
Git 安全和最终状态的责任。Subagents 只是有边界的执行或审查 worker。

开始 checkpoint work 前，父 agent 必须判断哪些任务可以并行。可以把 codebase
exploration、impact mapping、互不重叠且有明确 file ownership 的 implementation
slices、test / log / CI triage、documentation / contract / test-plan review，
以及 correctness、security、compatibility、regression、evidence-quality 等独立
review axes 交给 subagents。

只有当 checkpoint 确实是 single-scope、没有可独立并行的工作，或 delegation
会违反 iteration contract、sandbox、live-run boundary、evidence rules 或 Git
safety rules 时，才可以保持单线程。checkpoint record 必须写明未使用 subagents
的原因。

Subagent 输出在父 agent review、verify、integrate 之前只属于 advisory。Campaign
progress 不得仅因为 subagent 声称成功就前进。

每个 child package checkpoint 至少必须记录：

```text
child package id
route status
subagent tasks launched or single-thread reason
subagent outputs reviewed
changed files
commands run
commands not run
test results
review findings by priority
compatibility review
scope review
next action
```

Full campaign mode 不跳过门禁。出现以下任一情况时，必须立即把 campaign 停为
`BLOCKED`、`NEEDS_USER_INPUT` 或该 campaign 定义的等价 final status：

- 存在未解决的 P0 / P1 design、code、evidence 或 scope finding；
- 缺少必需的 child documents；
- code / mixed work 缺少已审核的 `technical-design.md`；
- implementation 前缺少 `implementation_authorized: yes`；
- 目标状态缺少足够证据；
- `CURRENT_STATE.md` 与 child docs、parent plan、review records 或实际 git state 冲突；
- subagent work 绕过 iteration documents、assigned file ownership、live-run
  boundaries、evidence rules 或 Git safety rules；
- campaign routing 依赖未经父 agent 验证和集成的 subagent report；
- diff 中出现越界的 runtime、test、eval、external result、fixture、schema、API、
  worker、frontend 或 documentation file；
- 需要 live validation，但当前 thread 没有明确提供 target、API、state、scenario
  和 result-doc update 授权。

不要把过期 child package id 写成 `GOAL_RUNNER.md` 里的权威 route。当前 route 必须来自
`CURRENT_STATE.md` 或 parent plan，避免已完成 child 继续吸引新的 `/goal` run。

## Iteration Package File Standard

Code 和 mixed package 必须包含：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

Documentation-only package 至少必须包含：

```text
README.md
intent.md
contract.md
plan.md
review.md
```

只有当 documentation-only package 不准备或改变 runtime、schema、API、UI、tests、
fixtures、prompts、process rules、evidence rules、validation behavior、release
status 或 automation-consumption behavior 时，才可以省略 `technical-design.md` 和
`test-plan.md`。

如果 documentation-only package 修改以下内容，则必须包含 `test-plan.md`，并建议包含
`technical-design.md`：

```text
process rules
milestone semantics
product boundaries
Agent boundaries
evidence rules
validation templates
release status
package sequencing
automation consumption contracts
```

父级 umbrella planning package 可以有意使用更小的文件集合，但前提是它自己的文档明确说明：
后续 child code / mixed package 进入实现前必须创建完整七件套。即便如此，umbrella plan
也必须用上面的 Planned Package Standard 写清每个 child package 条目。

## Required Content For Each Package File

每个 package 文件都必须具体到可以 review。只有占位标题不够。

### README.md

必须包含：

```text
Status
Type
Goal
Scope
Deliverables
Final assessment state, if applicable
```

### intent.md

必须包含：

```text
Problem / purpose
Why now
Relationship to roadmap or milestone
Non-goals
Expected handoff
```

### contract.md

必须包含：

```text
Public concepts
Allowed changes
Forbidden changes
Compatibility requirements
Out-of-scope follow-ups
```

### technical-design.md

必须包含：

```text
Documentation or implementation structure
Affected files
Data / control flow, if relevant
Compatibility strategy
Anti-drift rules
```

### test-plan.md

必须包含：

```text
Exact commands to run
Expected results
Commands not run and why
Blocker recording rule
No unverified claims rule
```

### plan.md

必须包含：

```text
Ordered execution steps
Phase boundaries
Stop conditions
Checkpoint update step
Review update step
```

### review.md

必须包含：

```text
FINAL_STATUS block for current routing state
Changed files
Commands run
Test results
Compatibility review
Scope review
Unresolved P1/P2/P3
Final assessment
```

## Anti-Drift Requirements

任何 future milestone 或 package planning 都必须说明：

```text
where the work lives
what files may change
what files must not change
which current behaviors are compatibility-sensitive
which adjacent tempting features are explicitly out of scope
which later milestone or package owns those tempting features
how the next package receives handoff
```

禁止：

- 用 external validation target 反向驱动 runtime abstractions；
- 把 target-specific selectors、seed data、routes、answer keys 或 component details
  复制进 product runtime 或 prompts；
- 在 current package 中实现 future-milestone work；
- 混合 documentation planning 和 implementation，除非当前 package contract 明确允许；
- 在没有 current-session evidence 的情况下声称 tests passed。

## Validation And Post-Closeout Documentation Standard

post-closeout validation 文档必须区分这些状态：

```text
feature closeout complete
independent validation not yet performed
validation planned
validation executed
validation passed / blocked / failed / unverified
```

不能把 validation plan 写成 validation result。

post-closeout validation 文档应该包含：

```text
intent
contract
test plan
API / CLI smoke plan
E2E / integration plan
external-operator review plan
execution plan
report template
review
```

硬规则：

- E2E 没跑就记录 `not executed` 或 `not configured`。
- AI-operated validation 没跑就不能写 passed。
- 如果 E2E framework 或 service 不可用，要记录 fallback 和剩余风险。
- Validation report 不能预填 `passed`。
- 只有当前 session 真实运行过的命令才能记录为 passed。
- 如果命令不可用，必须记录 blocker。
- live autonomous 或 WAgent evidence 必须遵守根目录 `AGENTS.md` / `CLAUDE.md` 里的执行边界。

## Evidence And Review Rules

Evidence 和 review 记录必须遵守：

```text
No unverified test claims.
No hidden blockers.
No vague "tests passed".
No claim that a live product path passed without the approved product surface.
No conversion of FAIL / BLOCKED / UNVERIFIED into PASS by wording changes.
```

Review 必须保留这些状态差异：

- planned but not implemented；
- implemented but not tested；
- non-live tests passed；
- live product validation passed；
- live product validation failed / blocked / unverified。
