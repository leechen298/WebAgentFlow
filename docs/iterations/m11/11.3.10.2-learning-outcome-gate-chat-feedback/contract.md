# Contract

## Scope

本包定义 `wagent chat` 学习完成后的 outcome gate 和用户反馈规则。
它依赖 child 1 的 capability discovery aggregate result。

## Learning Outcome Status

Allowed values:

- `success`
- `partial_success`
- `failed`
- `unverified`

### success

至少一个核心能力通过证据门禁，且没有系统性阻塞。

Required behavior:

- 列出学到的能力。
- 只把通过门禁的 LearnedPath 加入 current session learned action catalog。
- 引导用户用自然语言说工作需求。

### partial_success

部分筛选能力通过，部分失败、未确认或暂不支持。

Required behavior:

- 列出已学能力。
- 列出未学会、未确认或暂不支持的能力。
- 不夸大全部成功。
- 只把通过门禁的 LearnedPath 加入 current session learned action catalog。

### failed

没有任何能力通过证据门禁。

Required behavior:

- 明确告诉用户学习失败。
- 不生成 learned action。
- 不加入 current session learned action catalog。
- 提供后台详情入口。

### unverified

执行了探索，但证据不足，不能确认学习成功。

Required behavior:

- 明确告诉用户“我还不能确认已经学会”。
- 不生成 learned action。
- 不加入 current session learned action catalog。
- 提供后台详情入口。

## Feedback Rules

### success

Must include:

- 已学能力摘要。
- 自然语言下一步引导。

Must not include:

- 固定口令要求。
- “帮我开始”。
- 内部产品名称。

### partial_success

Must include:

- 已学能力。
- 未学/失败/未确认能力。
- 后台详情入口。
- 自然语言下一步引导。

### failed / unverified

Must include:

- 失败或未确认原因摘要。
- 后台详情入口。
- 不宣称学习完成。

## Control Term Filtering

以下控制词永远不能进入 learned action identity：

- `开始学习`
- `取消`
- `是`
- `好的`
- `好`
- `确认`
- `现在开始`
- `开始`
- `继续`
- `返回`
- `重试`

Forbidden identity fields:

- `alias`
- `suggested_utterance`
- `business_goal`
- `canonical_goal`
- `match_terms`
- current session learned action display name

如果 raw user text 是控制词，runtime 必须回溯使用：

- pending page learning intent
- capability summaries
- user-provided business goal when available
- safe generated capability labels from passed LearnedPath metadata

如果无法生成业务身份，则该 run 不得生成 learned action。

## Learned Action Catalog Gate

Only passed capabilities may enter the current session learned action catalog.

Do not add:

- failed scenario
- unverified scenario
- unsupported capability
- control-term-only alias
- observe-only path
- click-only generic submit path

## Debug / History Contract

Conversation history detail must expose:

- learning batch outcome
- discovery batch id
- passed capabilities
- failed capabilities
- unsupported capabilities
- unverified capabilities
- run ids
- learned path ids
- evidence status
- warnings

This is a product/debug surface, not a request to dump raw LLM payloads or private runtime payloads into backend terminal logs.

## CLI Contract

At session start, CLI should show a concrete history path:

`/conversation/history/<session_id>`

The message should remain user-friendly and not require users to understand internal logs.

## Non-goals

- No new discovery mechanics in child 2.
- No live autonomous validation by default.
- No backend terminal raw payload dump as the observability solution.
- No changes to product lifecycle or internal Agent role names.
