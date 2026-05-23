# 技术设计（Technical Design）

状态：ready_for_implementation（design review passed，未实现代码）

## 当前状态（Current State）

11.3.5.7 已实现 pending choice、private map、choice selection、expiry、revision、
cancel cleanup 和 active task targeted tests。11.3.6.1 提供 runner core。11.3.6.2 扩展
failure recovery case。

11.3.6.3 不重新设计 runner 框架，而是在 runner core 上增加一个 case family：

```text
pending_choice_multi_candidate
```

## Design Overview

```text
Config / CLI
  -> Case registry
  -> Multi-candidate setup
  -> ConversationDriver
  -> EvidenceCollector
  -> GateEvaluator
  -> ArtifactWriter
  -> Exit reducer
```

### Case Registry

新增 case id：

```text
pending_choice_multi_candidate
```

可选 npm script：

```bash
pnpm run eval:wagent:pending-choice
```

该 script 应等价于调用 runner 的 pending choice case，不得绕过 Conversation API。

## Multi-candidate Setup

Runner 需要构造一个稳定的 A/B/C non-planner 多候选场景。

### Preferred Setup

首选在同一 eval session 里通过 Conversation API 学习三个候选 actions：

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
```

如果实际 runtime 会因为 alias / target scope 合并而无法得到三个 distinct candidates，runner
不得猜测；应转入 blocked / not observable，或使用已评审的 eval-only setup hook。

### Candidate Setup Practicality

Runner setup manifest 必须记录 setup source：

```text
setup_type =
  live_same_session_distinct_paths |
  live_setup_session_distinct_paths |
  eval_only_candidate_binding |
  fixture_only
```

`live_same_session_distinct_paths` / `live_setup_session_distinct_paths` 是最高保真路径。
如果 `/items` 当前 live UI 只能稳定提供一个真实 action，第一版可使用
`eval_only_candidate_binding` 稳定触发 pending choice evaluator：

- 至少一个真实 LearnedPath 来自当前 eval run。
- 其他 A/B/C candidates 可作为 aliases 绑定到当前 eval run 的真实 path；受控 fixture 仅用于
  `fixture_only` / non-live evaluator tests。
- manifest 必须写入 `live_multi_action_capability=false`。
- Markdown result 必须说明该结果只验证 pending choice evaluator 和 public / private payload
  safety，不声称产品已有完整 live distinct-action capability。

### Eval-only Setup Hook

如果需要 hook，hook 只负责把当前 eval run 已知的真实 path 绑定成多个 safe learned action
summaries。它不得直接写 private map。pending choice 仍必须由后续 Conversation API dispatch
触发。受控 fixture 只能在 non-live evaluator tests 中使用，不能冒充 live runtime pass。

推荐 metadata shape：

```json
{
  "client": "wagent_eval",
  "eval_candidate_setup": {
    "case_id": "pending_choice_multi_candidate",
    "setup_type": "eval_only_candidate_binding",
    "live_multi_action_capability": false,
    "actions": [
      {"choice_id": "A", "alias": "新增项目", "learned_path_id": "..."},
      {"choice_id": "B", "alias": "添加项目", "learned_path_id": "..."},
      {"choice_id": "C", "alias": "录入项目", "learned_path_id": "..."}
    ]
  }
}
```

Hook event 如需记录，只能记录 case id、setup type、candidate count、aliases 和 redacted
path hashes；不得记录完整 learned path ids 或 private map。

## Conversation Flow

推荐 live flow：

```text
create_session(metadata.client=wagent_eval)
setup candidates
send ambiguous turn: "帮我处理一下这个页面"
collect evidence after pending choice
send choice turn: "A"
collect evidence after execution
evaluate gates
write JSON + Markdown
```

如果 ambiguous turn 进入 planner-backed choice，应 fail `planner_not_invoked`，因为 planner
choice 属于 11.3.6.4。

## Evidence Collection

EvidenceCollector 需要读取：

- session detail。
- messages。
- events。
- history。
- learned path details for setup paths。
- raw dispatch responses。
- runner setup manifest。

Runner setup manifest 是 runner 内部 evidence，用于记录 A/B/C expected mapping。它可以进入
redacted JSON artifact，但 learned path ids 必须按 11.3.6 redaction 规则处理；gate evidence
必须使用短 hash / alias / event id 等审计线索，不把完整 private id 写进 Markdown。

For `execution_uses_choice_A_path`, GateEvaluator may compare raw ids before redaction:

```text
expected_raw_path_id = setup_manifest.choice["A"].learned_path_id
actual_raw_path_id = chat_execution_started.payload.learned_path_id
match = expected_raw_path_id == actual_raw_path_id
```

Public evidence must then emit only:

```text
expected_choice=A
expected_alias=<alias>
expected_path_hash=<sha256-prefix>
actual_path_hash=<sha256-prefix>
match=true|false
setup_type=<setup_type>
```

## Gate Evaluation

新增 evaluator helpers：

- detect current eval setup candidates。
- record setup type and live multi-action capability。
- detect non-planner `pending_choice_created` event。
- parse public A/B/C choices from message / public event / session payload。
- scan public payload for forbidden private tokens。
- detect planner events and fail this case when present。
- resolve expected choice A learned path from setup manifest。
- verify A-turn `chat_execution_started.learned_path_id` matches expected A path internally。
- output only redacted path hashes / aliases in gate evidence。
- verify pending choice cleanup after A selection。
- verify reporter / DOM evidence success for A execution。

## Redaction

Redaction must cover:

- `learned_path_id`
- `pending_choice_private_map`
- `slot_overrides`
- `evidence_targets`
- selector / XPath
- `ReplayAction`
- `execution_payload`
- credentials / tokens / cookies / authorization headers

`item_name` can remain visible as deterministic `/items` test data.

## Compatibility

本迭代允许的代码改动范围：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时的最小 eval-only candidate setup hook 和对应 targeted tests

除 eval-only hook 外，不修改 pending choice 产品语义。若实现发现需要改变 11.3.5.7
pending choice contract，必须先回到本迭代文档修订并重新 review。
