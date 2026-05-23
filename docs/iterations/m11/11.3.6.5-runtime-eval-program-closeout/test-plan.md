# 测试计划（Test Plan）

状态：ready_for_implementation

## 测试目标

验证 M11.3.6 closeout sweep 能把实现事实、runner output、artifact 和迭代文档状态对齐，
并且不会把 non-live / blocked / fixture-only 证据误写成 live pass。

## 静态检查

| ID | 检查 | 预期 |
|---|---|---|
| ST-1 | `git status --short --branch` | 记录分支和脏区；不得覆盖用户改动。 |
| ST-2 | `rg -n "eval:wagent" package.json` | 存在 items / failure-recovery / pending-choice / planner-choice scripts。 |
| ST-3 | `rg -n "SCHEMA_VERSION|ALL_CASES|planner_backed_choice|pending_choice_multi_candidate" scripts/evals/wagent_runtime_eval.py` | runner 覆盖 11.3.6.3 / 11.3.6.4 case。 |
| ST-4 | `find docs/testing/results -name 'm11-11.3.6*'` | closeout 前后 result 数量明确。 |

## Runner Commands

| ID | Command | Required? | 通过标准 |
|---|---|---|---|
| RC-1 | `pnpm run eval:wagent:pending-choice` | Required unless services unavailable | exit `0` 才能 closeout pass；exit `2` 只能记录 blocked artifact。 |
| RC-2 | `pnpm run eval:wagent:planner-choice` | Required unless services unavailable | exit `0` 才能 closeout pass；exit `2` 只能记录 blocked artifact。 |
| RC-3 | `pnpm run eval:wagent:items` | Optional regression | 若运行，必须记录 exit code / artifact。 |
| RC-4 | `pnpm run eval:wagent:failure-recovery` | Optional regression | 若运行，必须记录 exit code / artifact。 |

Exit code 解释沿用 11.3.6 runner contract：

| Exit Code | 含义 |
|---:|---|
| 0 | all required gates pass |
| 1 | required gate fail |
| 2 | environment blocked |
| 3 | timeout |
| 4 | artifact write failure |
| 5 | runner error |

## Artifact / Redaction Checks

| ID | 检查 | 预期 |
|---|---|---|
| AR-1 | 新增 JSON artifact 存在 | path 记录在 closeout result。 |
| AR-2 | 新增 Markdown result 存在 | path 记录在 closeout result。 |
| AR-3 | sensitive grep | 不泄露 full `learned_path_id`、private map、selector、slot overrides、credentials。 |
| AR-4 | result status | 与 runner exit code 一致。 |
| AR-5 | live run wording | 未跑 live 时写 `not_run`，blocked 时写 `blocked`，不得写 pass。 |
| AR-6 | blocked completion wording | blocked artifact 不得让子包进入 `implementation_complete_non_live` / `implemented_and_live_eval_passed`。 |

## Review / Index Checks

| ID | 文件 | 预期 |
|---|---|---|
| RI-1 | 11.3.6.3 `review.md` | 不再停留在 `Code: not_started`，除非 closeout 明确未执行。 |
| RI-2 | 11.3.6.4 `review.md` | 不再停留在 `Code：not_started`，除非 closeout 明确未执行。 |
| RI-3 | 11.3.6 program README / review | 子包状态与 11.3.6.3 / 11.3.6.4 review 一致。 |
| RI-4 | M11 README / `m11-plan.md` | 索引状态与 program README 一致。 |

## 不运行项

默认不运行：

- autonomous-run endpoints；
- `verify-scenario`；
- Console UI smoke；
- product-driven browser execution outside the eval runner。

如果用户后续明确要求 live UI smoke，必须另按 AGENTS.md 记录 invocation surface、
run_id / product output 和 pass gate，不得混入本 closeout 默认流程。

## 失败处理

- `RC-1` 或 `RC-2` gate fail：closeout result 写 `blocked` 或 `partially_closed`，并建议新开 fix。
- artifact redaction fail：不得提交 artifact；先开 fix 或重生成。
- 服务不可用：允许记录 blocked artifact，但对应子包只能写 `implementation_complete_blocked`
  或 `blocked`；M11.3.6 program 只能写 `partially_closed` 或 `blocked`，不能写
  `closed_live` / `closed_non_live` / complete。
