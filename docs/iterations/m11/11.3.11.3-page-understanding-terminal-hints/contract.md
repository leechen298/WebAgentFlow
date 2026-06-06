# 契约（Contract）

状态：proposed

## 概念 / 边界契约

`PageTerminalHintSet` 是 Page Understanding / PageAnalysis 给终态判断的语义提示集合。
它不是执行计划，不是 selector catalog，不是 LearnedPath 候选。

Required concepts:

- `page_purpose`：页面做什么的简短描述。
- `page_content_summary`：页面主要内容和控件概况。
- `page_regions`：筛选区、表单区、结果区、操作栏、导航区、弹窗候选区等区域提示。
- `possible_functions`：搜索、筛选、导出、创建、编辑、删除、查看详情、刷新、导航、提交等候选功能。
- `candidate_terminal_states`：每类功能可能产生的 terminal type。
- `confidence` / `reason_summary`：deterministic bridge 的置信度和原因。

## 状态 / 结果契约

Terminal hint source:

- `deterministic`：由 PageAnalysis 结构化控件推导。
- `provider`：未来 Page Understanding Agent provider 输出；本包默认不启用。
- `fallback`：PageAnalysis 信号不足，只输出 generic operate-page hints。

Candidate terminal types must use child 1 taxonomy:

- `navigation`
- `list_refresh`
- `network_completion`
- `modal_or_popup_opened`
- `download_started`
- `toast_or_status_message`
- `region_changed`
- `no_observable_change`

## Schema / API 契约

Logical shape:

```text
PageTerminalHintSet {
  page_purpose
  page_content_summary
  page_regions[]
  possible_functions[]
  candidate_terminal_states[]
  confidence
  reason_summary
  source
}
```

No public API wire change is required in child 3. If implementation stores hints on exploration result,
field must be optional and backward compatible.

## Evidence / Observation 契约

Allowed inputs:

- PageAnalysis counts and categorized elements.
- DiscoveredElement category, tag, role, text, aria_label, placeholder, label_text, semantic_role and content_hint.
- Page title and URL metadata.

Disallowed outputs:

- executable selectors or raw `target_selector`;
- raw DOM path or full HTML;
- raw fixture-specific field labels as runtime rules;
- claim that a terminal state happened.

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：supports Page Understanding Agent / terminal-state evidence handoff in L1.
- Scope boundary 对齐：semantic hints only; browser operation stays code-owned.
- Roadmap / milestone 对齐：M11.3 post-closeout; M14 may replace/extend deterministic bridge later.
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- Existing PageAnalysis consumers keep working.
- Terminal hints are optional.
- Provider unavailable must fall back to deterministic/fallback hints.
- No changes to LearnedPath, pass_gate, Supervisor or replay semantics.

## 不变契约

本轮不改变：

- Product lifecycle stages。
- Internal Agent roles。
- Public API contracts by default。
- Database schema。
- Replay status semantics。
- Reporter / recovery / abort boundaries。

## 非目标

- 不做 full M14 Page Understanding Agent。
- 不让 LLM output selectors or browser steps。
- 不实现 stop controller。
- 不运行 live validation。

## 未决问题

- Later child may decide whether to persist terminal hints in run history.
- Later M14 may replace deterministic bridge with provider-backed Page Understanding Agent prompt assets.
