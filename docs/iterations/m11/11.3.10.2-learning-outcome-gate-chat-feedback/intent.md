# Intent

## 用户问题

当前 `wagent chat` 在 URL-only learning 后可能输出：

- “学习完成：我学会了开始操作。”
- “之后你可以说‘帮我开始’。”

这有两个问题：

1. “开始学习”是 CLI 控制选项，不是用户要完成的业务工作。
2. 即使底层学习证据失败或不足，chat runtime 仍可能基于单个 alias 宣称学习完成。

对普通用户来说，这既不友好，也会误导用户相信系统已经学会了页面能力。

## 产品目标

当 child 1 已经产出多场景 capability learning result 后，本包负责：

- 判断整体学习结果。
- 列出学到的能力。
- 列出失败、未确认或暂不支持的能力。
- 避免控制词污染 learned action identity。
- 引导用户直接说自然工作需求。
- 在后台 history / debug timeline 中展示可复查详情。

## Learning Outcome

本包新增或标准化：

`learning_outcome = success | partial_success | failed | unverified`

用户反馈必须基于 aggregate outcome，而不是单个 `alias` 模板。

## 成功定义

本包成功后：

- `wagent chat` 不再出现“我学会了开始操作 / 帮我开始”。
- `开始学习`、`取消`、`是`、`好的`、`现在开始` 等控制词不会进入 alias、
  suggested utterance、business_goal 或 match_terms。
- success / partial_success / failed / unverified 都有明确反馈路径。
- failed / unverified 不会污染 current session learned action catalog。
- history detail 能看到 learning batch outcome、passed capabilities、failed capabilities、
  run id、learned path id 和 evidence status。

## 用户体验目标

用户不需要记忆系统生成的固定口令。学习成功后，系统应鼓励用户直接说要做的工作：

`你可以直接告诉我想做什么，比如“搜索启用用户”或“按邮箱查用户”。`

对外表达使用“我”，不要暴露 `WebAgentFlow` 作为用户需要理解的产品内部名称。
