# 实施计划（Implementation Plan）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## 文件 / 模块

预计触及：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时：Conversation runtime 中的最小 eval-only hook 及 targeted tests

本迭代文档：

- `docs/iterations/m11/11.3.6.2-failure-recovery-eval/`

## Step 1 · 复核现状

实现前先检查：

- 11.3.6.1 runner core 当前实现状态。
- 11.3.5.8 recovery menu / private payload tests。
- Conversation dispatch metadata 是否能承载 eval-only fault injection。
- events / history / public payload 当前是否足够验证 redaction gates。

## Step 2 · 扩展 runner case registry

新增：

```text
failure_recovery_menu_safety
```

要求：

- 可通过 runner `--case` 选择。
- 不影响现有 `items_closed_loop` 和 `single_path_direct_replay_regression`。
- case result 写入统一 JSON / Markdown artifact。

## Step 3 · 实现 failure trigger

优先使用最小 eval-only hook：

```text
metadata.client = wagent_eval
metadata.eval_fault_injection.case_id = failure_recovery_menu_safety
metadata.eval_fault_injection.reporter_outcome = needs_review
```

如果现有 runtime 已有稳定 failure path，可不加 hook，但必须把触发方式写入 review。

## Step 4 · 实现 recovery gate evaluator

新增 hard gates：

- `failure_triggered`
- `recovery_menu_shown`
- `retry_wording_safe`
- `retry_side_effect_warning`
- `relearn_option_shown`
- `cancel_option_shown`
- `private_payload_not_visible`
- `recovery_events_sanitized`
- `verified_happy_path_no_recovery`
- `no_autonomous_or_direct_replay`

## Step 5 · 更新 artifact / Markdown result

Markdown result 增加：

- failure trigger type。
- recovery failure class。
- menu evidence。
- private payload scan evidence。
- retry execution not-run statement。
- live eval not-run statement when applicable。

## Step 6 · 更新 scripts / docs

如果实现 package script，新增：

```json
{
  "scripts": {
    "eval:wagent:failure-recovery": ".venv/bin/python scripts/evals/wagent_runtime_eval.py --case failure_recovery_menu_safety"
  }
}
```

同步更新：

- `docs/testing/wagent-runtime-eval.md`

## Step 7 · 测试与安全检查

运行 test-plan 中的 non-live commands，并记录结果。

不得在没有服务、artifact 和 session evidence 的情况下声称 live eval pass。

## Step 8 · Review

更新本目录 `review.md`：

- implementation summary。
- changed files。
- commands and outputs。
- artifacts。
- not-run items。
- final decision。

## 非目标

- 不执行 retry 作为 required gate。
- 不运行登录页。
- 不新增 pending choice / planner choice eval。
- 不调用 autonomous-run endpoints。
- 不把 Codex 自然语言判断作为 gate。
