# 技术设计（Technical Design）

状态：draft_for_review（planner-backed choice eval 设计稿，未实现代码）

## 当前状态（Current State）

11.3.5.9 已实现 TaskPathPlanner-backed chat choices。Runtime 在多候选 / vague goal path 中
生成 planner candidates，调用 TaskPathPlanner，生成 sanitized public choices，并在用户选择后
执行 private map 中对应 learned action。

11.3.6.1 提供 runner core。11.3.6.3 扩展 non-planner pending choice eval。11.3.6.4 不重新设计
runner 框架，而是在 runner core 上增加一个 case family：

```text
planner_backed_choice
```

并补一个回归 case：

```text
planner_single_path_bypass_regression
```

## Design Overview

```text
Config / CLI
  -> Case registry
  -> Planner candidate setup
  -> ConversationDriver
  -> EvidenceCollector
  -> GateEvaluator
  -> ArtifactWriter
  -> Exit reducer
```

### Case Registry

新增 case id：

```text
planner_backed_choice
```

可选 npm script：

```bash
pnpm run eval:wagent:planner-choice
```

该 script 应等价于调用 runner 的 planner-backed choice case，不得绕过 Conversation API。

## Planner Candidate Setup

Runner 需要构造一个稳定的 multi-candidate planner 场景。

### Preferred Setup

首选在当前 eval run 中通过 Conversation API 学习多个 distinct actions：

```text
学习操作 A
学习操作 B
学习操作 C
```

每个 setup action 必须记录：

```text
choice_id
alias
target_url
learned_path_id
source_turn
source_event_id
path_hash
```

如果实际 product-test-site 暂时无法稳定产生多个 distinct actions，runner 不得猜测；
应转入 blocked / not observable，或使用已评审的 eval-only planner candidate setup hook。

### Eval-only Planner Candidate Binding

如果需要 hook，hook 只负责准备 safe session learned action summaries。它不得：

- 直接写 `pending_choice_private_map`。
- 直接生成 `planner_choice_created` / `planner_choice_selected`。
- 直接调用 `TaskPathPlanner.plan()`。
- 伪造 Planner output。

后续 planner choice 必须由 Conversation API dispatch 自然触发。

推荐 setup manifest：

```json
{
  "case_id": "planner_backed_choice",
  "setup_type": "eval_only_planner_candidate_binding",
  "live_multi_action_capability": false,
  "planner_distinct_path_capability": false,
  "expected_selected_choice": "A",
  "candidates": [
    {"choice_id": "A", "alias": "新增项目", "learned_path_id": "...", "path_hash": "sha256:..."},
    {"choice_id": "B", "alias": "添加项目", "learned_path_id": "...", "path_hash": "sha256:..."},
    {"choice_id": "C", "alias": "录入项目", "learned_path_id": "...", "path_hash": "sha256:..."}
  ]
}
```

Artifact 必须 redaction。Markdown 只能输出 choice id、alias、hash、capability flags 和 match。

## Conversation Flow

推荐 flow：

```text
create_session(metadata.client=wagent_eval)
setup candidates
send vague turn: "帮我处理一下这个页面"
collect evidence after planner choice
send selection turn: "A"
collect evidence after execution
evaluate planner_backed_choice gates
run / reuse single-path bypass regression
write JSON + Markdown
```

如果 vague turn 只进入 11.3.6.3 non-planner path，应 fail `non_planner_choice_not_used`。

## Evidence Collection

EvidenceCollector 需要读取：

- session detail。
- messages。
- events。
- history。
- learned path details for setup paths。
- raw dispatch responses。
- runner setup manifest。

Planner-specific sources：

- `planner_candidates_generated`
- `planner_choice_created`
- `planner_choice_selected`
- `planner_unable_to_plan`
- `planner_fallback_used`
- `chat_execution_started`
- `chat_execution_completed`
- `task_result_reported`

Runner setup manifest 是 runner 内部 evidence，用于记录 expected selected choice mapping。它可以进入
redacted JSON artifact，但 learned path ids 必须按 11.3.6 redaction 规则处理。

## Gate Evaluation

新增 evaluator helpers：

- detect current eval planner setup candidates。
- record `setup_type`、`live_multi_action_capability` 和 `planner_distinct_path_capability`。
- detect `planner_candidates_generated` event。
- detect `planner_choice_created` event。
- fail if only non-planner pending choice path is observed。
- parse public A/B/C choices from message / public event / session payload。
- scan public payload for forbidden private tokens。
- scan planner events for full ids、selector、slot values、raw planner warning text。
- detect selection turn and `planner_choice_selected` event。
- compare selected choice expected path with `chat_execution_started.learned_path_id` internally。
- output only redacted hashes / aliases in gate evidence。
- verify pending choice cleanup after selection。
- verify reporter / DOM evidence success。
- verify single-path no-planner regression。

## Planner Top-choice Observability

Current public surfaces may not expose the exact planner top choice id or top path hash. If implementation cannot
observe it through sanitized events or public choice markers, gate evaluator must mark:

```text
planner_top_choice_observable = not_observable / warning
```

The runner must not infer Planner top choice from final WAgent text or Codex judgment.

If a minimal read-only exposure is added later, it must expose only:

```text
top_choice_id
top_path_hash
candidate_count
warning_count / risk_count / uncertainty_count
```

It must not expose full `learned_path_id`, selector, slot overrides, private map or raw planner warnings.

## Redaction

Redaction must cover:

- `learned_path_id`
- `pending_choice_private_map`
- `planner_summary` when it contains raw warnings / risk reasons
- `slot_overrides`
- `evidence_targets`
- selector / XPath
- `ReplayAction`
- `execution_payload`
- credentials / tokens / cookies / authorization headers
- raw `response_text` containing private payload

`item_name` can remain visible as deterministic `/items` test data only when it is not inside private
slot override payload.

## Compatibility

本迭代允许的代码改动范围：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时的最小 eval-only planner candidate setup hook 和 targeted tests

除 eval-only setup hook 外，不修改 planner-backed choice 产品语义。若实现发现需要改变 11.3.5.9
planner contract，必须先回到本迭代文档修订并重新 review。
