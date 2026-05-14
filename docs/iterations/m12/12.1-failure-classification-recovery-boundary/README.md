# 12.1 · Failure Classification and Recovery Boundary

Status: documentation initialized.

## 目标

12.1 是 M12 的 failure classification 与 recovery boundary 文档包。它定义
一个未来实现可使用的、受 evidence 约束的分类器：从 M11.1 replay
execution / Task Result Reporter 产生的结构化证据中，判断当前结果属于
`failure`、`blocked`、`uncertain`、`needs_review`，或明确无需进入 recovery。

12.1 只给出边界建议，不执行恢复。它回答的是：

```text
当前 evidence 说明系统应该 stop、ask user、needs_review、
suggest_reteach，还是未来可在确认链路后考虑 retry？
```

它不按任何按钮，不继续浏览器，不重新规划，不生成面向用户的恢复对话。

## 和 12.0 的关系

12.0 建立 M12 的总边界：failure recovery / abort / runtime robustness 不是
自动修复层，不能 hidden recovery、hidden relearning，也不能在未经用户同意
时继续操作浏览器。

12.1 是 12.0 之后的第一层细化：先把 failure 类结果分清楚，再把 recovery
边界写成可审计建议。没有这层分类，后续 retry、proposal、conversation flow
都会缺少稳定前提，容易把 recovery 做成隐式行为。

## 和 M11.1 的关系

12.1 消费 M11.1 已经形成的结构化证据，而不是重新执行或重判网页：

- 11.1.6 replay execution evidence：`plan_execution_started`、
  `plan_execution_completed`、`plan_execution_failed`、
  `plan_execution_blocked` 等事件。
- 11.1.7 Task Result Reporter evidence：`verification_outcome`、
  `needs_review`、`task_verified`、`evidence_summary`、
  `missing_evidence_summary`、`no_recovery`、`no_autonomous`、`no_llm`。
- 11.1.8 tests and evidence：确认 `replay completed != task succeeded`，
  successful replay + no postcondition evidence 会得到 `uncertain`，blocked
  path 不会产生 replay events，failed / uncertain 不触发 recovery。

12.1 不消费 runtime user-abort signal。user abort 属于 12.2。

## 和 12.2 / 12.3 / 12.4 的边界

- **12.2 User abort / stop handling**：处理用户主动 stop / abort。12.1 不处理
  abort signal，也不定义 pause / stop 的运行时实现。
- **12.3 Recovery proposal MVP**：把 12.1 的 boundary recommendation 转成
  可展示的 recovery proposal。12.1 不生成用户对话，不生成 proposal 文案。
- **12.4 Retry / re-run policy**：定义 retry 什么时候允许、什么时候必须禁止、
  如何要求用户确认。12.1 的 `retry_possible_requires_confirmation` 不是 retry，
  只是说明未来可以交给 12.3 / 12.4 / 用户确认链路继续判断。

## 概念模型

未来实现可以围绕这些概念建模：

| 概念 | 含义 |
|---|---|
| `FailureClassification` | 对当前 result / execution evidence 的分类结果。 |
| `RecoveryBoundary` | 当前 evidence 允许或禁止的 recovery 边界。 |
| `ClassificationReason` | 触发分类的结构化原因，不是自由推理。 |
| `EvidenceReference` | 指向 conversation event、report payload、execution status、replay status、drift status、error summary 等证据来源。 |
| `BoundaryRecommendation` | 给后续 12.3 / 12.4 / 用户确认链路使用的边界建议。 |

## 分类输入

12.1 的输入必须来自结构化 evidence，例如：

- execution status：started / completed / failed / blocked；
- replay status：succeeded / observed / failed / missing；
- drift status；
- error summary；
- result reporter `verification_outcome`；
- result reporter `needs_review`；
- evidence summary / missing evidence summary；
- `task_verified`；
- `no_recovery` / `no_autonomous` / `no_llm` markers；
- learned path id、target URL、final URL、final title 等结构化引用。

12.1 不读取 raw HTML 做自由规划，不从截图 payload 或页面文本里临时发明
postcondition，也不依赖默认 LLM provider。

## 分类输出

建议分类值：

| Classification | 含义 |
|---|---|
| `success_no_recovery_needed` | 已有明确结构化 evidence 证明任务成功，不需要进入 M12 recovery。当前 M11.1 默认不会触发这个路径，因为第一版 postcondition evidence 尚未接入。 |
| `failure` | 有明确负面 evidence，例如 replay failed、drift、error，或 result reporter 给出 failed。 |
| `blocked` | 缺少上下文、权限、目标页面状态、路径能力或验证能力，不能安全继续。 |
| `uncertain` | replay 可能完成，但没有足够 postcondition evidence 证明业务任务成功。 |
| `needs_review` | 必须由用户或后续审核步骤查看 evidence 后才能判断。 |

## Recovery Boundary Recommendation

建议边界值：

| Recommendation | 含义 |
|---|---|
| `stop` | 必须停止当前自动化链路。不能继续操作浏览器。 |
| `ask_user` | 缺少上下文、权限、目标状态或判断依据，需要向用户询问。 |
| `needs_review` | 不能自动判断，需要用户或后续审核步骤查看 evidence。 |
| `suggest_reteach` | 可以建议重新教学或更新 LearnedPath，但不能自动写回。 |
| `retry_possible_requires_confirmation` | 当前 evidence 没有立刻禁止未来 retry consideration，但必须交给 12.3 / 12.4 / 用户确认链路处理。它不是 retry execution，也不是完整的 safe-retry 判断。 |
| `no_recovery_needed` | 明确无需进入 recovery。 |

## Non-execution Contract

12.1 classifier 不能执行：

- retry；
- replan；
- browser continuation；
- autonomous exploration；
- hidden relearning；
- LearnedPath write-back；
- user-facing recovery dialogue；
- recovery proposal generation；
- LLM-based recovery planning；
- M11.2 Runtime Observation / Wait-for-change；
- user abort handling。

12.1 的输出只能是 classification、reason、evidence references 和 boundary
recommendation。
