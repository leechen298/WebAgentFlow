# 实施计划（Implementation Plan）

状态：proposed

## 输入

- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- 11.3.6 closeout result:
  `docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md`

## 文件 / 模块

- `scripts/evals/wagent_user_behavior_eval.py` 或等价 runner - 后续新增用户行为 eval runner。
- `scripts/evals/specs/` 或等价 test-only path - 后续存放目标页面、用户话术、expected gates
  和 forbidden-token 列表。
- `docs/testing/wagent-user-facing-behavior-eval.md` - 后续新增运行说明和 artifact 解释。
- `apps/api/tests/` - 后续补 target-agnostic unit / integration tests。
- Product prompt assets - 后续只允许通用策略，不允许测试目标内容。
- `docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval/review.md` - 记录实际实现和证据。

## 步骤

1. 完成 design review。
   - 产出：确认 first-wave case、forbidden-token hard gate 和 allowed / forbidden path list。
   - 未通过 review 前不得进入实现。
2. 新增 test-only eval spec。
   - 产出：目标 URL、测试话术、expected behavior gates、forbidden runtime tokens 都在 spec 中。
   - 要求：spec 不被产品 runtime import。
3. 实现 forbidden-token scanner。
   - 产出：能扫描功能代码和产品 prompt asset，允许 docs / tests / fixture / artifact。
   - 要求：任何匹配使 eval fail。
4. 实现 first-wave runner cases。
   - 产出：URL-only known、URL-only unknown、execute-known、execute-unknown、vague-input。
   - 要求：所有 case 通过 Conversation API 或 approved eval surface。
5. 增加 redaction and boundary checks。
   - 产出：artifact / public response 中没有 private ids、selector、private map、slot overrides。
   - 要求：operation log 明确没有 autonomous-run endpoint 或 direct replay substitution。
6. 写 docs/testing 使用说明。
   - 产出：命令、环境变量、artifact 路径、status semantics、not-run live surfaces。
7. 执行验证并回填 review。
   - 产出：命令输出、exit code、artifact 路径、case gate 表、未运行项。
   - 要求：没有证据的项写 `not_run` / `unverified`。

## 验证

验证计划来自 `technical-design.md` 的高层 Test Matrix 和 `test-plan.md` 的详细测试矩阵。
当前文档阶段不运行未来 runner。

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval -maxdepth 1 -type f | sort` | 七件套存在 | Yes | Docs-only creation check |
| `rg -n "11\\.3\\.7|User-facing WAgent Behavior Eval|测试页面" docs/iterations/m11 docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md` | 索引和 scope correction 已写入 | Yes | Docs grep only |
| `pnpm run eval:wagent:user-behavior` | Future behavior eval pass / fail / blocked artifact | Yes by default | Command does not exist until implementation |

## 复核清单（Review Checklist）

- [ ] 11.3.6 结论没有被写成完整产品能力通过。
- [ ] 11.3.7 明确验证用户视角行为，而不是重复底层零件测试。
- [ ] forbidden-token hard gate 覆盖功能代码和产品 prompt。
- [ ] 测试目标细节只允许出现在 eval spec、fixture、tests、docs 和 artifact。
- [ ] 第一批 case 不依赖登录页。
- [ ] 没有触发 `verify-scenario`、autonomous run 或 Console UI smoke。
