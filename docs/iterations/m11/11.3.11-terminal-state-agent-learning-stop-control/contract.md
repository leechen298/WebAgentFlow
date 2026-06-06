# 契约（Contract）

状态：proposed

## 概念 / 边界契约

本父包定义 M11.3 post-closeout 终态判断路线，不新增 product lifecycle stage，提出新增命名内部角色
`Terminal State Agent / 终态判断 Agent`。该角色在父包阶段仍是 proposed boundary；child 1
必须先更新 / 复核 `docs/product-model.md` 后才能实现运行时代码。本包不新增 legacy Agent 字母。

- `TerminalState`：一次操作或一组操作后，页面 / 浏览器 / artifact 状态已经稳定到可以评价该
  attempt 的状态。
- `TerminalStateEvidence`：证明或反证 terminal state 的可审计证据。证据可以来自浏览器事件、
  网络事件、DOM / region 变化、download metadata、dialog / popup、toast、URL / title 变化、
  loading 周期、console error、截图和 PageAnalysis / Page Understanding hints。
- `Terminal State Agent / 终态判断 Agent`：L1 内部 Agent。它消费精简版 AST、Page Understanding
  Agent 输出、PageAnalysis、attempt 事件、before / after snapshot、browser event timeline，
  判断当前 attempt 是否已到可评价终态，并输出 terminal verdict、terminal type、evidence
  summary 和 stop recommendation。
- `ExplorationStopController`：工程层控制器。它不是产品 Agent，而是消费 Terminal State Agent
  verdict 的 deterministic controller，根据 `stop`、`wait`、`continue` 或 `unverified_stop`
  控制探索循环，防止 Supervisor 只在探索结束后才发现 evidence 不足。
- `PageTerminalHint`：Page Understanding Agent 对页面用途、页面内容、主要功能、页面区域和候选
  终态的语义提示，例如列表页的 search refresh、导出按钮的 download、详情按钮的 modal /
  drawer。
- `AttemptTerminalSummary`：某个 attempt 的终态摘要，供 Attempt Evaluation Agent 读取。

Terminal State Agent 不取代 Attempt Evaluation Agent。它回答“是否到了可评价终态、证据是什么、
现在是否应该停止等待 / 继续探索”；Attempt Evaluation Agent 回答“这个 attempt 是否成功、
异常在哪里、是否值得沉淀”。

## Agent 输入 / 输出契约

Page Understanding Agent 必须被升级为终态判断的上游输入，至少输出：

- `page_purpose`: 页面做什么。
- `page_content_summary`: 页面包含哪些主要内容。
- `page_regions`: 筛选区、表格区、操作栏、详情区、弹窗容器、分页区等区域。
- `possible_functions`: 搜索、筛选、导出、创建、编辑、删除、查看详情、刷新等候选功能。
- `candidate_terminal_states`: 每类功能可能产生的终态，例如 list refresh、modal opened、
  download started、navigation、toast/status message、region changed。
- `confidence` 和 `reason_summary`。

Terminal State Agent 输入必须至少包括：

- 精简版 AST；
- Page Understanding Agent 输出；
- PageAnalysis 的结构化控件 / 区域信息；
- attempt action log；
- before / after DOM、region snapshot、screenshot 或 accessibility snapshot；
- browser event timeline；
- bounded wait result。

Terminal State Agent 输出必须至少包括：

- `terminal_outcome`；
- `terminal_type`；
- `evidence_strength`；
- `evidence_summary`；
- `stop_decision`；
- `warnings`；
- `needs_more_wait` / `max_wait_reached` 这类等待状态提示。

## 终态类型契约

第一版 terminal state taxonomy 至少覆盖：

- `navigation`: URL、route、title、main frame load 或 history state 变化稳定。
- `list_refresh`: 搜索 / 筛选 / 刷新导致列表、表格、卡片集合或分页区域完成刷新。
- `network_completion`: 请求 / 响应完成且与候选操作相关，但页面变化不明显。
- `modal_or_popup_opened`: dialog、drawer、popover、dropdown、confirm、message panel 等可见。
- `browser_dialog`: alert / confirm / prompt 事件出现并被记录。
- `download_started`: download event 出现，并记录 filename、suggested filename、MIME / size
  等可安全记录 metadata。
- `artifact_available`: 下载、导出或生成文件完成，artifact metadata 可验证。
- `toast_or_status_message`: message / notification / status text 出现，可能短暂存在。
- `region_changed`: 指定 page region 的 DOM / text / row count / fingerprint 发生可解释变化。
- `no_observable_change`: 已等待并采集证据，但没有足够变化；只能进入 failed / unverified，
  不得宣称成功。

## 状态 / 结果契约

`terminal_outcome`：

- `terminal_detected`: 有足够证据说明已到终态。
- `terminal_unverified`: 有迹象但证据不足，不能作为成功学习依据。
- `not_terminal_yet`: 仍处于 loading、请求未完成、弹层未稳定或 DOM 未稳定。
- `terminal_failed`: 出现错误终态，例如网络错误、下载失败、目标区域错误、阻断弹窗或页面崩溃。

`stop_decision`：

- `stop`: terminal evidence 足够，停止当前 attempt 并进入 Attempt Evaluation。
- `wait`: 仍可能产生终态，继续等待 bounded timeout。
- `continue`: 当前操作没有形成终态，探索可以尝试下一个动作。
- `unverified_stop`: 已达到等待上限或证据冲突，停止但标记 unverified。

`evidence_strength`：

- `strong`: 浏览器事件、网络、DOM / artifact、PageTerminalHint 中至少两个独立来源一致。
- `medium`: 一个强信号或多个弱信号，但缺少完整交叉验证。
- `weak`: 只有间接迹象。
- `none`: 没有有效证据。

只有 `terminal_outcome=terminal_detected` 且 evidence gate 通过的 attempt，才可进入成功
LearnedPath 候选。`terminal_unverified`、`terminal_failed`、`no_observable_change` 只能保留
run history、failure evidence 或 negative knowledge。

## Schema / API 契约

父包不定义最终 wire shape。子包必须在各自 `contract.md` / `technical-design.md` 中定义：

- browser event timeline 的 redacted schema；
- PageTerminalHint schema；
- Terminal State Agent input / output schema；
- terminal verdict / stop decision schema；
- AttemptTerminalSummary schema；
- exploration run history 和 conversation / console history 展示字段；
- 如需 database migration，必须单独设计兼容与回滚。

父包要求所有新增字段向后兼容；旧 run history、旧 LearnedPath、旧 conversation history 必须可读。

## Evidence / Observation 契约

允许的 terminal evidence 来源：

- Playwright page / browser context events：request、response、requestfailed、download、dialog、
  popup、framenavigated、load / domcontentloaded、console、pageerror。
- CDP / browser instrumentation when available：network lifecycle、performance timing、target
  events；第一版不得要求 Chromium fork。
- DOM / accessibility / screenshot snapshots：region fingerprint、row count、visible text diff、
  ARIA dialog / role changes、loading indicator lifecycle。
- PageAnalysis 和 Page Understanding Agent 输出的 page purpose、region、control relation、
  candidate terminal hints。
- 精简版 AST，供 Terminal State Agent 理解当前页面结构和 attempt 所在上下文。
- execution steps、attempt log、wait result、supervisor / pass_gate / scorecard（仅在允许入口真实执行时）。

不允许：

- 用 Codex 自然语言判断替代产品内 evidence。
- 用 target-specific `/users`、字段名、按钮文案、DOM id 写入 runtime 终态规则。
- 用失败或 unverified evidence 宣称学习成功。
- 直接调用 autonomous-run endpoint 或内部 service import 伪造 live run evidence。
- 在未授权 live run 时记录 `pass` / `works` 结论。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：属于 L1 autonomous learning，在 Page Understanding Agent 和 Attempt
  Evaluation Agent 之间提出 Terminal State Agent 边界；不改变 L1 / L2 / L3。child 1 必须先
  更新 / 复核 `docs/product-model.md` 后才能实现该 Agent。
- Scope boundary 对齐：代码和 Playwright 仍负责浏览器操作；Agent 只做语义理解 / 评价，不逐步
  控制浏览器。
- Roadmap / milestone 对齐：当前执行路由放在 M11.3 post-closeout，因为它修复 URL-only learning
  和筛选页学习停止判断；未来 M14 Learning Quality, Coverage & Negative Knowledge 应复用或扩展
  本包沉淀的 Agent / evidence 契约。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：Agent role proposed change:
  Yes；product lifecycle: No；milestone boundary: current execution belongs to M11.3 post-closeout。
- 如果是 Yes，必须先更新哪些权威文档：`docs/product-model.md`、`docs/roadmap.md`（如 roadmap
  的 M11.3 follow-up / M14 reuse relationship 需要同步）、child 1 `contract.md`。

## 兼容性契约

- 旧 `exploration_runs` 仍可读；新增 terminal evidence 字段必须可选。
- 旧 `learned_paths` 仍可 replay；新 gate 不自动删除旧 path。
- 旧 conversation / console history 不要求有 terminal summary。
- M10 replay status semantics 不改变。
- M11 chat feedback 不得因为本包未实现而失效；本包完成后可消费更丰富 learning outcome，未来
  M14 可继续扩展该 evidence contract。

## 不变契约

本轮不改变：

- Product lifecycle stages：L1 / L2 / L3 不变。
- Internal Agent roles：不新增 legacy Agent 字母；Page Understanding Agent、Attempt Evaluation
  Agent、Learning Report Agent 边界不被 Terminal State Agent 取代。
- Public API contracts：父包不改；子包如新增字段必须向后兼容。
- Database schema：父包不改；子包如需要 migration 单独评审。
- Replay status semantics：不改变 M10 replay / drift status。
- Reporter / recovery / abort boundaries：不进入 M12 recovery / retry / abort。

## 非目标

- 不实现任意网页“全自动学会所有操作”的最终形态。
- 不让 LLM 控制每一步浏览器动作。
- 不做指数级全操作组合探索。
- 不把测试页面或 fixture 细节写入 runtime。
- 不在父包阶段运行 live autonomous validation。

## 未决问题

- 第一版 terminal evidence 是否需要独立 DB table，或先存入 `exploration_runs.strategy_json` /
  `result_snapshot_json` / event payload；由 child 1 和 child 2 设计。
- Page Understanding Agent 的输出是独立 LLM 调用，还是先通过现有 page analysis + bounded prompt
  过渡；由 child 3 设计。
- Terminal State Agent 的第一版是否必须 LLM-backed，或采用 deterministic evidence classifier +
  Agent review 的两段式；由 child 1 和 child 4 设计。
- 如果 Playwright / CDP 事件不足以覆盖某些浏览器终态，是否开后续 Chromium instrumentation
  child package；本父包不授权。
