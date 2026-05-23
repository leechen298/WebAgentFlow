# 实施计划（Implementation Plan）

状态：draft_for_review（planner-backed choice eval 设计稿，未实现代码）

## 文件 / 模块

预计触及：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时：Conversation runtime 中的最小 eval-only planner candidate setup hook 及 targeted tests

本迭代文档：

- `docs/iterations/m11/11.3.6.4-planner-backed-choice-eval/`

## Step 1 · 复核现状

实现前先检查：

- 11.3.6.1 / 11.3.6.3 runner 当前实现状态。
- 11.3.5.9 planner-backed choice runtime 的现有 events / history / public payload。
- `planner_candidates_generated`、`planner_choice_created`、`planner_choice_selected` 当前 payload。
- 当前 public API 是否能从 live Conversation flow 稳定准备多个 candidate learned actions。
- `pending_choice_private_map` 和 raw planner warnings 是否只存在 private metadata。
- 如果 live setup 不稳定，确认是否采用 `eval_only_planner_candidate_binding`，并记录它不能声称
  full live distinct-action Planner capability。

## Step 2 · 扩展 runner case registry

新增：

```text
planner_backed_choice
```

可选新增：

```text
planner_single_path_bypass_regression
```

要求：

- 可通过 runner `--case` 选择。
- 不影响现有 `items_closed_loop`、`single_path_direct_replay_regression`、
  `failure_recovery_menu_safety` 和 `pending_choice_multi_candidate`。
- case result 写入统一 JSON / Markdown artifact。

## Step 3 · 实现 planner candidate setup

优先通过 Conversation API 学习多个当前 eval run candidates。

如果实现阶段确认自然 setup 不稳定，可以实现最小 eval-only planner setup hook，但 hook 必须只准备
session learned action summaries，且必须默认关闭。manifest 必须记录：

```text
setup_type
live_multi_action_capability
planner_distinct_path_capability
candidate aliases
redacted path hashes
expected selected choice
```

公开 artifact / Markdown 不得输出完整 `learned_path_id`。

## Step 4 · 实现 planner-backed gate evaluator

新增 hard gates：

- `setup_planner_candidates_current_eval`
- `planner_candidates_generated`
- `planner_choice_created`
- `non_planner_choice_not_used`
- `public_choices_abc_visible`
- `planner_public_payload_sanitized`
- `planner_event_sanitized`
- `select_planner_choice_dispatched`
- `planner_choice_selected`
- `planner_choice_execution_started`
- `execution_uses_selected_choice_path`
- `pending_choice_cleared`
- `execution_verified`
- `final_response_verified`
- `no_autonomous_or_direct_replay`

新增 conditional gates：

- `planner_warning_wording_safe`
- `planner_top_choice_observable`

`execution_uses_selected_choice_path` 允许 runner 内部用 raw path id 比较 expected / actual，但 gate
evidence 只能输出 alias、redacted hash 和 `match=true|false`。

## Step 5 · 实现 single-path bypass regression

复用当前 eval run learned path，执行明确单路径请求，校验：

- no `planner_candidates_generated`。
- no `planner_choice_created`。
- direct `chat_execution_started`。
- execution path 来自当前 eval session。
- execution verified。

## Step 6 · 更新 artifact / Markdown result

Markdown result 增加：

- candidate setup type。
- `live_multi_action_capability`。
- `planner_distinct_path_capability`。
- planner events summary。
- selected choice evidence。
- expected / actual path hash match evidence。
- public/private payload scan evidence。
- live eval not-run statement when applicable。

如果 setup 使用 alias binding，Markdown 必须说明它不证明 full live distinct-action Planner
capability。

## Step 7 · 更新 scripts / docs

如果实现 package script，新增：

```json
{
  "scripts": {
    "eval:wagent:planner-choice": ".venv/bin/python scripts/evals/wagent_runtime_eval.py --case planner_backed_choice"
  }
}
```

同步更新：

- `docs/testing/wagent-runtime-eval.md`

## Step 8 · 测试与安全检查

运行 test-plan 中的 non-live commands，并记录结果。

不得在没有服务、session id、setup manifest、planner events、artifact 和 gate evidence 的情况下声称
live eval pass。

## Step 9 · Review

更新本目录 `review.md`：

- implementation summary。
- changed files。
- commands and outputs。
- artifacts。
- not-run items。
- final decision。

## 非目标

- 不实现新的 Planner ranking 语义。
- 不执行 failure recovery。
- 不运行登录页。
- 不调用 autonomous-run endpoints。
- 不把 Codex 自然语言判断作为 gate。
