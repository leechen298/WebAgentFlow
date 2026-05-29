# 意图（Intent）

状态：PACKAGE_COMPLETE

## Problem / Purpose

`11.3.8.1` 已让 learned action metadata 保存业务目标，但当前 suggested utterances
仍可能来自旧的 action label wrapper，例如：

```text
帮我Learn how to create
Learn how to create 一下
```

这类 utterance 不包含业务对象。用户下一次自然输入 `Create an inventory item ...`
时，现有 matcher 即使继续读取 utterances，也缺少能和用户业务表达相交的词。

本包的目的，是让学习完成后保存的 suggested utterances 直接表达可复用业务动作。

## Why Now

父包 `11.3.8` 把 PV-CLI-003 失败拆成连续子包：

1. `11.3.8.1` 保存 business identity。
2. `11.3.8.2` 用 business identity 生成 reusable utterances。
3. `11.3.8.3` 改善 learned action matching。
4. `11.3.8.4` 固化 regression。
5. `11.3.8.5` 才做外部黑盒重验和 latest result 更新。

`11.3.8.1` 已 `PACKAGE_COMPLETE`，本包现在可以消费其 metadata contract。

## Relationship To Roadmap / Milestone

本包属于 M11.3 post-closeout recovery follow-up。它不重新打开 M11 closeout，不启动
M12 recovery / retry / abort，也不改变 L1 / L2 / L3 lifecycle 或 internal Agent roles。

它仍遵守 M11.3 runtime chat 的产品原则：

```text
The LLM understands what the user said.
The code decides whether and how WebAgentFlow acts.
```

Suggested utterance generation 必须是 deterministic code path，不新增 LLM dependency。

## Non-goals

- 不引入 LLM utterance generation。
- 不做完整多语言翻译系统。
- 不改变 `_matching_actions()` threshold、confidence policy、多候选处理或 replay execution。
- 不实现 external black-box revalidation。
- 不更新 `docs/testing/results/external-black-box-validation-latest.md`。
- 不把 `5177/inventory`、Validation-Site selector、field label、button text、
  `data-testid`、seed copy、operation alias 或 page source 写入 runtime / prompts。
- 不把 SKU、商品名、数量、用户名、密码、token 等 slot / sensitive values 写进 reusable utterances。

## Success Definition

本包完成后：

- Product-level learning result 的 suggested utterances 包含 business action 和 business object。
- 当 `action_goal` 含 slot value 而 `canonical_goal` 干净时，utterances 从 clean canonical /
  useful aliases 生成。
- Existing Chinese / login utterance behavior 保持兼容。
- Chat runtime 保存 session learned action 时，会避免把 stale learning-wrapper utterances
  作为唯一 reusable terms。
- Focused tests 证明 business-object utterances 存在、slot values 被排除、旧流程保持兼容。
- Review 记录未运行 live external validation，并且不声称 PV-CLI-003 已通过。

## Expected Handoff

若本包 `PACKAGE_COMPLETE`，`11.3.8.3-learned-action-matching-improvement` 可以消费
`alias`、`utterances`、`business_goal`、`canonical_goal`、`action_aliases`、
`business_object` 和 `match_terms`。若 utterances 仍缺少 business object，`11.3.8.3`
不得通过放宽 matcher threshold 来掩盖本包缺口。
