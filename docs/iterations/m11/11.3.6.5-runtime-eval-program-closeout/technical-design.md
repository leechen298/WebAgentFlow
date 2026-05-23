# 技术设计（Technical Design）

状态：ready_for_implementation

## 设计摘要

本包采用 docs / verification closeout，不改 runtime。执行 Agent 读取当前 `origin/v0.1`
工作区，按现有 runner 命令运行或记录 skip，然后同步文档状态。

Closeout 分为四层：

```text
Repository state audit
-> Runner command execution / skip recording
-> Artifact and result validation
-> Iteration status synchronization
```

## 文件范围

允许修改：

- `docs/iterations/m11/11.3.6.3-pending-choice-multi-candidate-eval/review.md`
- `docs/iterations/m11/11.3.6.4-planner-backed-choice-eval/review.md`
- `docs/iterations/m11/11.3.6-wagent-runtime-eval-program/README.md`
- `docs/iterations/m11/11.3.6-wagent-runtime-eval-program/review.md`
- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-${timestamp}.md`

按实际命令输出允许新增：

- `artifacts/wagent-eval/wagent-runtime-eval-${timestamp}.json`
- `docs/testing/results/m11-11.3.6.3-pending-choice-eval-${timestamp}.md`
- `docs/testing/results/m11-11.3.6.4-planner-backed-choice-eval-${timestamp}.md`

默认不修改：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/app/**`
- `apps/api/tests/**`
- `package.json`

若必须改上述代码或脚本，本 closeout 终止，另开代码型 fix 迭代。

## Repository State Audit

执行前记录：

- current branch；
- `git rev-parse HEAD`；
- `git status --short --branch`；
- `git log --oneline --max-count=10`；
- `package.json` 中 11.3.6 eval scripts；
- runner `SCHEMA_VERSION` 和 `ALL_CASES`；
- `docs/testing/results/` 中已有 11.3.6 result 文件。

如果工作区不干净，必须区分：

- 本 closeout 已产生的文档 / artifact；
- 既有未提交改动；
- 与 closeout 无关的用户改动。

不得清理或覆盖用户改动。

## Runner Execution Design

推荐执行顺序：

```bash
pnpm run eval:wagent:pending-choice
pnpm run eval:wagent:planner-choice
```

可选执行：

```bash
pnpm run eval:wagent:items
pnpm run eval:wagent:failure-recovery
```

如果 API / product site 未启动，runner 应返回 exit code `2`，并生成 blocked artifact。Closeout
文档必须记录 blocked，不得把 blocked 写成 pass。

Blocked artifact 不得推动子包进入 `implementation_complete_non_live`。如果 pending-choice 或
planner-choice 只拿到 exit code `2`，closeout 只能记录该子包 blocked，并把 program 状态写成
`partially_closed` 或 `blocked`。

如果用户明确要求 live pass 证据，则应先启动所需服务，再运行对应 eval；否则可以记录
`live Conversation eval: not_run`，但 M11.3.6 program 不能标 `closed_live`。

## Artifact Validation

对新增 JSON / Markdown result 做静态检查：

```bash
rg -n "learned_path_id|slot_overrides|pending_choice_private_map|private_retry_payload|ReplayAction|authorization|cookie|token|secret" <artifact paths>
```

允许命中 only if：

- 文档在描述 prohibited terms / redaction rules；
- 测试负例路径；
- redacted placeholder，不包含真实私有 payload。

否则 closeout 必须 fail。

## Status Synchronization

状态同步必须从最具体到最总纲：

1. 11.3.6.3 review。
2. 11.3.6.4 review。
3. 11.3.6 program README / review。
4. M11 README。
5. `m11-plan.md`。
6. Program-level closeout result。

如果 11.3.6.3 / 11.3.6.4 只完成 non-live checks，状态应写成
`implementation_complete_non_live`，而不是 `implemented_and_live_eval_passed`。

## Rollback / Failure Design

如果 closeout 过程中 gate fail：

- 保留 failure artifact；
- review 写 `implementation_review_failed` 或 `blocked`；
- program closeout 写 `blocked` / `partially_closed`；
- 不修改 runner 代码；
- 建议另开 fix 迭代，引用 failure artifact。

如果 artifact 写入失败：

- closeout result 写 `blocked`；
- 不伪造 artifact path；
- 记录失败命令和 exit code。

## Contract Alignment

本设计遵守 11.3.6 program contract：

- pass / fail 由 runner hard gates 决定；
- Codex 只做 artifact 审计；
- direct replay 不可冒充 conversation closed loop；
- autonomous-run endpoints 不可由 runner / closeout 直接调用；
- 不可观察字段不得猜测；
- live eval 未跑时不得声称 live pass。
