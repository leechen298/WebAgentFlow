# 契约（Contract）

状态：proposed

## 概念 / 边界契约

`Terminal State Agent / 终态判断 Agent` 在本包中定义为 M11.3.11 scoped L1 evaluator
worker / terminal evidence contract，不是新的 lifecycle stage，也不是 legacy Agent I。
它位于 code-driven Playwright attempt 之后、Attempt Evaluation Agent 之前，回答：

```text
这个 attempt 是否已经到达可评价终态？证据是什么？现在应该 stop、wait、continue 还是 unverified_stop？
```

它不点击、不填写、不选择元素、不发起 browser operation。浏览器操作仍由 deterministic code、
Playwright execution 和 autonomous explorer attempt loop 执行。

Terminal State Agent 不取代：

- Page Understanding Agent：仍负责页面用途、区域、功能和候选终态语义。
- Attempt Evaluation Agent：仍负责 attempt 是否成功、异常在哪里、是否可沉淀。
- Learning Report Agent：仍是低优先级 presentation layer。
- Supervisor / pass_gate：仍是 approved verification surface 产生的运行结果判定。

本包不新增 legacy Agent 字母；如在产品模型中列名，写作 `Terminal State Agent`，
legacy alias 必须为 `no legacy alias`，并声明它支持 Attempt Evaluation Agent / code-derived
durable verdict，不替代任何既有 L1 Agent。

## 状态 / 结果契约

### Terminal types

第一版 taxonomy 固定为：

- `navigation`
- `list_refresh`
- `network_completion`
- `modal_or_popup_opened`
- `browser_dialog`
- `download_started`
- `artifact_available`
- `toast_or_status_message`
- `region_changed`
- `no_observable_change`
- `terminal_failed`

### Terminal outcomes

- `terminal_detected`：证据足够，attempt 已到可评价终态。
- `terminal_unverified`：有迹象但证据不足，不能作为成功学习依据。
- `not_terminal_yet`：仍在 loading、request、DOM stabilization、download 或 popup settling。
- `terminal_failed`：出现错误终态，例如 network failure、pageerror、download failure、blocked dialog。

### Evidence strength

- `strong`：至少两个独立证据来源一致，或一个 browser/artifact 强事件加一个 supporting signal。
- `medium`：一个强信号或多个弱信号，但缺少完整交叉验证。
- `weak`：只有间接迹象。
- `none`：没有有效证据。

### Stop decisions

- `stop`：终态证据足够，停止当前 attempt 并交给 Attempt Evaluation。
- `wait`：仍可能产生终态，继续 bounded wait。
- `continue`：当前 action 没形成终态，探索可进入下一个动作。
- `unverified_stop`：等待上限或证据冲突，停止但标记 unverified。

成功 LearnedPath 候选必须同时满足：`terminal_outcome=terminal_detected`、evidence gate 通过、
Attempt Evaluation 成功。`terminal_unverified`、`terminal_failed`、`no_observable_change`
不得进入 successful LearnedPath 或 current-session learned action catalog。

## Schema / API 契约

本包不落最终 runtime schema，但后续 child 必须按以下 logical shape 设计：

- `BrowserEventTimeline`：redacted browser events，包含 event kind、timestamp、safe URL metadata、
  method/status/resource type、download/dialog/popup/navigation/load/console/pageerror metadata。
- `PageTerminalHint`：Page Understanding Agent 输出的 candidate terminal states、target regions、
  function hints 和 confidence。
- `TerminalStateAgentInput`：compact AST、PageTerminalHint、PageAnalysis summary、attempt action log、
  before/after snapshots、BrowserEventTimeline、bounded wait result。
- `TerminalStateVerdict`：terminal outcome、type、evidence strength、evidence summary、stop decision、
  warnings、wait status。
- `AttemptTerminalSummary`：给 Attempt Evaluation / LearnedPath ingest gate 的 bounded summary。

所有新增字段必须向后兼容。旧 `exploration_runs`、旧 `learned_paths`、旧 conversation history
和旧 Console history 必须可读；缺少 terminal evidence 时显示 `not available`，不能报错。

## Evidence / Observation 契约

允许证据来源：

- Playwright page/context events：request、response、requestfailed、download、dialog、popup、
  framenavigated、load、domcontentloaded、console、pageerror。
- DOM / accessibility / screenshot snapshots：region fingerprint、row count、text diff、ARIA role、
  visible status message、loading lifecycle。
- PageAnalysis / Page Understanding：page purpose、regions、control relation、candidate terminal hints。
- Attempt log / action executor output / bounded wait result。

禁止证据来源：

- Codex 或其他 coding agent 的自然语言判断。
- target-specific `/users`、字段名、按钮文案、DOM id runtime rule。
- unredacted cookie、authorization header、token、raw request body、personal data。
- 未授权 live run 的 `pass`、`works` 或 invented Agent verdict。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：本包把 terminal-state classification 加入 L1 autonomous learning 的 attempt trial 和 Attempt Evaluation handoff；Terminal State Agent 命名仅限 scoped evaluator worker / evidence contract。
- Scope boundary 对齐：Agent 只做语义/证据评价；code 仍控制 browser operation。
- Roadmap / milestone 对齐：当前执行属于 M11.3 post-closeout stop-control follow-up；M14 可复用该 evidence / negative knowledge 契约。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：Yes，新增 scoped evaluator worker / evidence contract wording；No，不改变 lifecycle stage、legacy Agent aliases 或 milestone owner。
- 必须更新的权威文档：`docs/product-model.md`、`docs/roadmap.md`、`docs/iterations/m11/README.md`。

## 兼容性契约

- 旧 LearnedPath 不自动删除、不自动降级。
- 旧 run history 不要求 terminal summary。
- 新 terminal evidence 是 additive metadata，不改变 M10 replay status semantics。
- pass_gate / Supervisor result 仍是 approved validation surface 的运行证据，不被 Terminal State Agent 覆盖。
- Child 2-6 必须各自定义 migration/storage 细节；本包只允许 storage direction，不允许 runtime schema 变更。

## 不变契约

本轮不改变：

- Product lifecycle stages：L1 / L2 / L3 不变。
- Legacy Agent aliases：A-H 不新增、不重排。
- Public API contracts：不变。
- Database schema：不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：不进入 M12。

## 非目标

- 不实现完整 M14 learning quality system。
- 不实现 unbounded exploration 或全页面自动学会所有操作。
- 不让 LLM 逐步操作浏览器。
- 不运行 live autonomous validation。

## 未决问题

- Child 2 决定 event timeline 的具体 storage 位置和 redaction implementation。
- Child 3 决定 Page Understanding terminal hints 是 LLM-backed、deterministic bridge，还是两段式。
- Child 4 决定第一版终态判断是否采用 deterministic classifier、LLM-backed scoped evaluator worker，或两段式 classifier + Agent review。
- Child 5 决定 failure evidence / negative knowledge 的 MVP persistence 形态。
