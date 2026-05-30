# 实施计划（Implementation Plan）

状态：pass（first-wave user-facing behavior gates passed；full learn-then-execute remains follow-up）

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- 11.3.6 closeout result:
  `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md`

## 文件 / 模块

- `scripts/evals/wagent_user_behavior_eval.py` - user-facing behavior eval runner。
- `scripts/evals/specs/` 或等价 test-only path - 目标页面、用户话术、expected gates
  和 forbidden-token 列表仅能存在于 eval / test layer。
- `docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md` - stable latest
  Markdown result。
- `artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json` - stable latest JSON
  artifact。
- `apps/api/tests/` - target-agnostic unit / integration tests。
- Product prompt assets - 只允许通用策略，不允许测试目标内容。
- `docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval/review.md` - 记录实际实现和证据。

## 步骤

1. 确认 design review 通过并锁定实现范围。
   - 产出：以已通过评审的 first-wave case、known / unknown isolation strategy、
     forbidden-token hard gate 和 allowed / forbidden path list 作为实现输入。
   - 要求：不得在实现中放宽 anti-hardcoding、isolation 或 unknown choose-learn gates。
2. 新增 test-only eval spec。
   - 产出：目标 URL、测试话术、expected behavior gates、forbidden runtime tokens 都在 spec 中。
   - 要求：spec 不被产品 runtime import。
3. 实现 forbidden-token scanner。
   - 产出：能扫描功能代码和产品 prompt asset，允许 docs / tests / fixture / artifact。
   - 要求：任何匹配使 eval fail；现有测试站点特判不得 grandfather。
4. 清理现有 fixture-site runtime 特判。
   - 产出：`/records` route checks、test selector construction、fixture field names、fixture item
     names 和 operation aliases 不再存在于 product runtime / product prompts。
   - 要求：改成 generic runtime，或移动到 eval spec / test-only layer；未清理则 11.3.7
     标为 blocked，不能 pass。
5. 实现 known / unknown 隔离 preflight。
   - 产出：known 只读取当前 eval session / eval scope learned actions；unknown 使用 fresh
     session、isolated scope 或 explicit filtered catalog。
   - 要求：如果 global old LearnedPath 会污染 unknown，11.3.7 标为 blocked。
6. 实现 first-wave runner cases。
   - 产出：`url_only_known_page`、`url_only_unknown_page`、
     `url_only_unknown_choose_learn_starts_learning`、`execute_known_action`、
     `execute_unknown_action`、`execute_unknown_choose_learn_then_execute_or_learning_flow`、
     `vague_input_no_execution`、`forbidden_test_target_not_in_runtime_code_or_prompts`。
   - 要求：所有 case 通过 Conversation API 或 approved eval surface；`url_only_unknown_choose_learn_starts_learning`
     必须进入真实 learning flow 或产生 evidence-backed blocked state。
   - 备注：如果 full `learn_then_execute` 当前不支持，只能记录 learning flow started，并把
     full learn-then-execute 作为 follow-up；不得伪造 full pass。
7. 增加 redaction and boundary checks。
   - 产出：artifact / public response 中没有 private ids、selector、private map、slot overrides。
   - 要求：operation log 明确没有 autonomous-run endpoint 或 direct replay substitution。
8. 写 docs/testing 使用说明。
   - 产出：命令、环境变量、artifact 路径、status semantics、not-run live surfaces。
9. 执行验证并回填 review。
   - 产出：命令输出、exit code、artifact 路径、case gate 表、未运行项。
   - 要求：没有证据的项写 `not_run` / `unverified`。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。
本包已实现 runner，并完成 first-wave closeout。后续修改 runtime、eval runner、target spec 或
fixture-site 后需要重新运行本表中的 eval / integrity checks。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval -maxdepth 1 -type f | sort` | 七件套存在 | Yes | Docs-only creation check |
| `rg -n "11\\.3\\.7|User-facing WAgent Behavior Eval|测试页面" docs/iterations/m11 docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md` | 索引和 scope correction 已写入 | Yes | Docs grep only |
| `pnpm run eval:wagent:user-behavior -- --timeout 300` | First-wave behavior eval pass / fail / blocked artifact | Yes by default | Latest closeout artifact status is `pass` |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_result_gate_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json` | Latest artifact gate decision | Yes | Latest closeout result is `decision=PASS` |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md` | Public artifact redaction | Yes | Latest closeout result is `status=pass`, `match_count=0` |

## 复核清单（Review Checklist）

- [x] 11.3.6 结论没有被写成完整产品能力通过。
- [x] 11.3.7 明确验证用户视角行为，而不是重复底层零件测试。
- [x] forbidden-token hard gate 覆盖功能代码和产品 prompt。
- [x] 现有测试站点特判已改成 generic runtime、移入 eval spec / test-only layer，或将
  11.3.7 标为 blocked 并开 cleanup follow-up。
- [x] 如果当前 runtime 中发现 fixture-site 特判，已实际清理；cleanup issue 不能让
  11.3.7 pass。
- [x] known / unknown 页面状态使用 current eval session / eval scope 或 explicit filtered
  catalog 隔离，不受 global old LearnedPath 污染。
- [x] `url_only_unknown_choose_learn_starts_learning` 进入真实 learning flow，或以具体服务 /
  browser blocker 标为 blocked；没有证据不得 pass。
- [x] 测试目标细节只允许出现在 eval spec、fixture、tests、docs 和 artifact。
- [x] eval spec、docs、review、testing results、artifacts 不被 product runtime import。
- [x] 第一批 case 不依赖登录页。
- [x] 没有触发 `verify-scenario`、autonomous run 或 Console UI smoke。
