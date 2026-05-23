# 实施计划（Implementation Plan）

状态：ready_for_implementation（design review passed，未实现代码）

## 文件 / 模块

预计触及：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时：Conversation runtime 中的最小 eval-only candidate setup hook 及 targeted tests

本迭代文档：

- `docs/iterations/m11/11.3.6.3-pending-choice-multi-candidate-eval/`

## Step 1 · 复核现状

实现前先检查：

- 11.3.6.1 / 11.3.6.2 runner 当前实现状态。
- 11.3.5.7 pending choice runtime 的现有 events / history / public payload。
- 当前 public API 是否能从 live Conversation flow 稳定准备三个候选 learned actions。
- `pending_choice_private_map` 当前是否只存在 private metadata，public history / session 是否已脱敏。
- 如果 live setup 不稳定，确认是否采用 `eval_only_candidate_binding`，并记录它不能声称 full
  live distinct-action product capability。

## Step 2 · 扩展 runner case registry

新增：

```text
pending_choice_multi_candidate
```

要求：

- 可通过 runner `--case` 选择。
- 不影响现有 `items_closed_loop`、`single_path_direct_replay_regression` 和
  `failure_recovery_menu_safety`。
- case result 写入统一 JSON / Markdown artifact。

## Step 3 · 实现 candidate setup

优先通过 Conversation API 学习三个当前 eval run candidates。

如果实现阶段确认自然 setup 不稳定，可以实现最小 eval-only setup hook，但 hook 必须只绑定当前
eval run 已知真实 learned path 或受控 fixture，且必须默认关闭。manifest 必须记录：

```text
setup_type
live_multi_action_capability
candidate aliases
redacted path hashes
```

公开 artifact / Markdown 不得输出完整 `learned_path_id`。

## Step 4 · 实现 pending choice gate evaluator

新增 hard gates：

- `setup_multi_candidate_current_eval`
- `pending_choice_created`
- `public_choices_abc_visible`
- `public_choice_payload_sanitized`
- `planner_not_invoked`
- `select_A_dispatched`
- `choice_A_execution_started`
- `execution_uses_choice_A_path`
- `slot_override_after_choice`
- `pending_choice_cleared`
- `private_map_not_public_after_selection`
- `execution_verified`
- `final_response_verified`
- `no_autonomous_or_direct_replay`

`execution_uses_choice_A_path` 允许 runner 内部用 raw path id 比较 expected / actual，但 gate
evidence 只能输出 alias、redacted hash 和 `match=true|false`。

## Step 5 · 更新 artifact / Markdown result

Markdown result 增加：

- candidate setup type。
- `live_multi_action_capability`，尤其是 alias binding 场景必须为 `false`。
- setup manifest summary。
- public choices evidence。
- A selection evidence。
- expected / actual path hash match evidence。
- private payload scan evidence。
- live eval not-run statement when applicable。

## Step 6 · 更新 scripts / docs

如果实现 package script，新增：

```json
{
  "scripts": {
    "eval:wagent:pending-choice": ".venv/bin/python scripts/evals/wagent_runtime_eval.py --case pending_choice_multi_candidate"
  }
}
```

同步更新：

- `docs/testing/wagent-runtime-eval.md`

## Step 7 · 测试与安全检查

运行 test-plan 中的 non-live commands，并记录结果。

不得在没有服务、session id、setup manifest、artifact 和 gate evidence 的情况下声称 live eval pass。

## Step 8 · Review

更新本目录 `review.md`：

- implementation summary。
- changed files。
- commands and outputs。
- artifacts。
- not-run items。
- final decision。

## 非目标

- 不实现 planner-backed choice。
- 不执行 failure recovery。
- 不运行登录页。
- 不调用 autonomous-run endpoints。
- 不把 Codex 自然语言判断作为 gate。
