# Replay 测试域

本文件记录 M10.2 LearnedPath replay execution + drift detection 的测试矩阵。
它是 replay 这个产品能力域的长期测试说明，不是 WebAgentFlow 全项目测试计划。

## 覆盖范围

Replay 测试域覆盖：

- LearnedPath replay API。
- drift detection：`page_mismatch`、`signature_changed`、`target_missing`、
  `unsupported_action`、`none`。
- replay action execution result：`succeeded`、`observed`、`drifted`、
  `failed`、`unsupported`、`runtime_error` 等 replay 自有状态。
- LearnedPath catalog 里的 replay UI 展示。

Replay 测试域不覆盖：

- autonomous learning 全流程。
- Agent D/E/F/G/H。
- Runtime Conversation Surface。
- teaching mode。
- risk gate。
- artifact lifecycle。
- multi-page workflow。
- task postcondition verification。

这些能力属于后续里程碑或其他产品能力域，需要各自建立测试矩阵。

## 确定性 E2E 矩阵

当前确定性 E2E 位于 `apps/e2e/tests/replay/`，覆盖 M10.2 已交付行为。

| 用例 | 断言重点 |
| --- | --- |
| replay API happy path | HTTP 200，`code=0`，`status=succeeded`，`drift_status=none`，steps 非空 |
| observational path | `actions=[]` 返回 `status=observed`，steps 为空 |
| catalog UI happy path | catalog drawer 可以输入 URL 并展示 replay 成功结果 |
| page mismatch | `status=drifted`，`drift_status=page_mismatch` |
| target missing | `status=drifted`，`drift_status=target_missing` |
| unsupported action | `status=unsupported`，`drift_status=unsupported_action`，不是 500 |
| flaky warning | replay 允许执行，并展示 flaky/trust warning |
| deprecated 422 | deprecated path replay 返回 HTTP 422 |
| signature changed but executable | `drift_status=signature_changed`，有 warning，但仍可执行 |

## Codex 探索式补充

Replay 的探索式验证只补充 M10.2 replay E2E 的边界观察。它不能替代确定性
E2E，也不能扩大 replay 的产品范围。

探索式验证用例矩阵见：

- `docs/testing/exploratory/replay-e2e-cases.md`

可复用执行提示词见：

- `docs/testing/exploratory/replay-e2e-run-prompt.md`

探索式报告必须写入：

- `docs/testing/results/`

没有命令证据的 case 不能写 PASS；未执行的 case 写 `NOT_RUN`，环境阻塞写
`BLOCKED`。

## 后续可补用例

后续 replay 域可以按实现进展补充：

- 真实 DOM 遮挡导致的 `failed` action。
- 如果未来实现 replay audit persistence，则补 replay audit 查询和保留行为。
- 如果 M14 或后续里程碑增加更多 action type，则补对应 action replay E2E。
- 如果未来 artifact lifecycle 进入实现，再在 artifact 所属能力域补测试，不塞进
  M10.2 replay。
