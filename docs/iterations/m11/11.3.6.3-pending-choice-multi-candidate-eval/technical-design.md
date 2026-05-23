# 技术设计（Technical Design）

状态：draft_for_review（pending choice eval 设计稿，未实现代码）

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

### Eval-only Setup Hook

如果需要 hook，hook 只负责把当前 eval run 已知的 learned path ids 绑定成多个 safe
learned action summaries。它不得创建 fake path，也不得直接写 private map。pending choice
仍必须由后续 Conversation API dispatch 触发。

推荐 metadata shape：

```json
{
  "client": "wagent_eval",
  "eval_candidate_setup": {
    "case_id": "pending_choice_multi_candidate",
    "actions": [
      {"choice_id": "A", "alias": "新增项目", "learned_path_id": "..."},
      {"choice_id": "B", "alias": "添加项目", "learned_path_id": "..."},
      {"choice_id": "C", "alias": "录入项目", "learned_path_id": "..."}
    ]
  }
}
```

Hook event 如需记录，只能记录 case id、candidate count 和 aliases；不得记录 learned path ids
或 private map。

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
redacted JSON artifact，但 learned path ids 必须按 11.3.6 redaction 规则处理；gate evidence 可
使用短 hash / alias / event id 等审计线索，不把完整 private id 写进 Markdown。

## Gate Evaluation

新增 evaluator helpers：

- detect current eval setup candidates。
- detect non-planner `pending_choice_created` event。
- parse public A/B/C choices from message / public event / session payload。
- scan public payload for forbidden private tokens。
- detect planner events and fail this case when present。
- resolve expected choice A learned path from setup manifest。
- verify A-turn `chat_execution_started.learned_path_id` matches expected A path。
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
