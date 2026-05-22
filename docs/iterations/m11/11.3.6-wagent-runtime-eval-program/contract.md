# 契约（Contract）

状态：accepted_program_plan（program review passed，docs-only）

## Eval Program Contract

WAgent Runtime Eval Program 是 M11 working runtime 的本地验收体系。它通过 11.3.6.x
子包逐步覆盖核心 runtime case family。

它不是：

- 产品内部 Agent；
- TaskResultReporter；
- Supervisor Agent；
- M15 automated evaluation / audit / hygiene 平台；
- `verify-scenario` skill replacement。

## 通用原则

所有 11.3.6.x runner / eval case 必须遵守：

- pass / fail 由 hard gates 决定。
- Codex 是 artifact 审计员，不是 pass / fail 裁判。
- live eval 没有真实运行就不能声称 pass。
- direct replay API 不能冒充 WAgent runtime conversation 闭环。
- autonomous-run endpoints 不得由 runner 直接调用。
- `verify-scenario` 不属于 11.3.6.x 默认验证路径。
- public artifact 必须 redaction。
- current session evidence 优先于全局 catalog 推断。
- 不可观察字段必须标记 `not_observable` / `warning`，不能猜。

## 子包契约

| Package | Type | Responsibility |
|---|---|---|
| 11.3.6.1 | code | runner core, `/items` closed loop, single-path direct replay regression |
| [11.3.6.2](../11.3.6.2-failure-recovery-eval/) | code | failure recovery eval, private retry payload safety |
| 11.3.6.3 | code | pending choice multi-candidate eval |
| 11.3.6.4 | code | planner-backed choice eval |

每个 code 子包必须拥有自己的完整七件套，并在 `review.md` 记录实际测试证据。

## Artifact Contract

11.3.6.x 子包默认共用 artifact 约定：

```text
artifacts/wagent-eval/${runner_or_case}-${timestamp}.json
docs/testing/results/m11-${package}-${case_or_runner}-${date}.md
```

Markdown result 至少包含：

- status。
- commit。
- API base / product URL。
- session id。
- cases。
- required gates。
- warnings / not observable。
- raw JSON artifact path。
- not-run / boundary statement。

## Exit Code Contract

11.3.6.x runner 默认使用：

| Exit code | Meaning |
|---:|---|
| 0 | all required gates pass |
| 1 | required gate fail |
| 2 | environment blocked |
| 3 | timeout |
| 4 | artifact write failed |
| 5 | runner internal error |

如果子包需要新增 exit code，必须先更新该子包 `contract.md`，并说明兼容影响。

## Evidence Contract

不同 case family 可以有不同 gates，但所有 gates 都必须声明：

- name。
- required / conditional / optional。
- source。
- status semantics。
- evidence string。

不允许把 final WAgent message 当作唯一成功证据。Final response 只能作为 final response
gate，不能替代 DOM evidence、reporter outcome、choice event、planner event 或 recovery event。

## Boundary Contract

11.3.6 不改变：

- product lifecycle stages L1 / L2 / L3；
- internal Agent role table；
- Router / Orchestrator / Skill Runtime 边界；
- TaskResultReporter 语义；
- Failure Recovery 语义；
- LearnedPath storage contract；
- Conversation API response envelope。
