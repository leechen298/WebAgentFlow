# 实施计划（Implementation Plan）

状态：PACKAGE_COMPLETE

## 输入

- `AGENTS.md`
- `docs/product-model.md`
- `docs/roadmap.md`
- `docs/iterations/README.md`
- `docs/iterations/AGENTS.md`
- `docs/iterations/templates/`
- 当前用户关于筛选页、下载、弹窗、静默刷新和终态判断的产品反馈

## 文档生成决策

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control/` |
| Package type | umbrella / campaign |
| Parent / child route | parent package with six planned child packages |
| Required docs | parent: README / intent / contract / test-plan / plan / review / GOAL_RUNNER / CURRENT_STATE |
| Child docs | not generated in this pass; each child must create full seven-document set before implementation |
| Source inputs read | repository product model, roadmap, iteration standards, templates, current M11.3 context and future M14 alignment |
| Contract / status / evidence changes | parent defines Terminal State Agent, terminal state, evidence strength, stop decision, Agent boundary, live-run boundary |
| Design-review gate | required for every child package before implementation |
| Test-plan trigger | required for every code / mixed child because evidence, browser runtime, Agent boundary, API/history, UI and validation are involved |
| Implementation authorization boundary | parent does not authorize implementation; child `review.md` must record `implementation_authorized: yes` |
| Stop conditions | missing child docs, product-model conflict, runtime implementation attempted from parent, live-run request missing explicit approval, target-specific hardcoding |
| Handoff / checkpoint | active child starts at `11.3.11.1-terminal-state-agent-contract-taxonomy` |

## Planned Package 1

| Field | Value |
|---|---|
| Package name | `11.3.11.1-terminal-state-agent-contract-taxonomy` |
| Status | planned |
| Type | mixed |
| Goal | Create the concrete Terminal State Agent contract, event taxonomy, schema plan, product-model update plan, and first child seven-document implementation package. |
| Why this exists | The parent package defines the route, but runtime work needs a precise contract for the new named Agent boundary, terminal states, evidence strength, stop decisions, and Attempt Evaluation handoff. |
| Inputs / required reading | parent docs; `docs/product-model.md`; `docs/roadmap.md`; current `autonomous_explorer.py`, `supervisor_observations.py`, `page_analyzer.py`, `wait_for_change.py`, `learning_run_service.py`; M10 LearnedPath docs; M11 observation docs. |
| Allowed changes | child iteration docs; product-model / roadmap update proposal or scoped doc update; terminal-state schema proposal; event taxonomy design; compatibility review; test-plan definition. |
| Forbidden changes | runtime code, API, schema migration, live run, implementing the Agent before product-model alignment, adding legacy Agent letters without explicit product-model update. |
| Expected deliverables | full seven-document child package; reviewed contract for Terminal State Agent input/output, terminal outcome, evidence strength, stop decision, redaction, and storage options. |
| Expected tests / verification | docs integrity checks only; no runtime tests; no live autonomous run. |
| Compatibility constraints | preserve old run history, LearnedPath, replay and conversation history semantics. |
| Scope guardrails | contract and design only; does not implement browser event recording or stop controller. |
| Exit criteria | child `review.md` records design review result and `implementation_authorized` decision; parent `CURRENT_STATE.md` may move to child 2 only after approval. |
| Handoff to next package | child 2 consumes event taxonomy and storage/redaction decision. |

## Planned Package 2

| Field | Value |
|---|---|
| Package name | `11.3.11.2-browser-event-recorder` |
| Status | planned |
| Type | code / mixed |
| Goal | Add target-agnostic browser event recording for terminal-state evidence during autonomous attempts. |
| Why this exists | Search refreshes, downloads, dialogs and silent network completion are often visible in browser events before they are visible in DOM snapshots. |
| Inputs / required reading | child 1 docs; execution runtime; Playwright browser lifecycle; autonomous explorer attempt loop; wait result / observation docs; redaction policy. |
| Allowed changes | browser event recorder service, event timeline schema, redaction, attempt/run metadata integration, unit/integration tests. |
| Forbidden changes | Chromium fork, target-specific URL/selector rules, direct live autonomous validation, changing action planner semantics, storing raw secrets or unredacted request bodies. |
| Expected deliverables | request/response/requestfailed/download/dialog/popup/navigation/load/console/pageerror event capture; bounded timeline; redacted metadata; correlation to attempt id/run id. |
| Expected tests / verification | unit tests with synthetic events; integration tests without live browser where possible; Playwright controlled fixture tests only if child test-plan authorizes; live run default not run. |
| Compatibility constraints | old runs without event timeline remain readable; event capture failure must not crash existing exploration unless child contract says so. |
| Scope guardrails | instrumentation only; does not decide terminal state or LearnedPath ingest. |
| Exit criteria | tests pass, review finds no P0/P1 redaction or compatibility issue, event timeline can be consumed by child 4. |
| Handoff to next package | child 4 consumes recorder output; child 6 later exposes it in history / console. |

## Planned Package 3

| Field | Value |
|---|---|
| Package name | `11.3.11.3-page-understanding-terminal-hints` |
| Status | planned |
| Type | code / mixed |
| Goal | Upgrade Page Understanding Agent / PageAnalysis handoff to produce page purpose, content summary, possible functions, page regions, control relations, and candidate terminal hints. |
| Why this exists | The detector needs semantic hints: a list page search button likely refreshes a table; an export control likely produces a download; a detail action may open a modal. |
| Inputs / required reading | child 1 docs; product model Page Understanding Agent boundary; page analyzer; HTML AST / simplified AST docs; screenshot/page context handling; conversation page understanding references. |
| Allowed changes | PageTerminalHint schema, page context bundle, compact AST input, bounded Page Understanding prompt/output or deterministic bridge, tests and fixtures. |
| Forbidden changes | selectors or raw DOM paths in Agent output if product model forbids them; LLM-controlled browser actions; hardcoded `/users` field labels; forcing every page into a list-page category. |
| Expected deliverables | page purpose, page content summary, possible functions, region inventory, control-to-region hints, candidate terminal types, confidence/reason summary, fallback behavior when Agent unavailable. |
| Expected tests / verification | unit tests for deterministic hint extraction; prompt/schema tests if LLM path is introduced; no live run unless explicitly approved. |
| Compatibility constraints | existing PageAnalysis consumers continue working; Page Understanding can be optional / unavailable without breaking exploration. |
| Scope guardrails | semantic hints only; does not evaluate attempts or persist LearnedPaths. |
| Exit criteria | terminal hints are stable enough for child 4 and do not violate Agent boundary rules. |
| Handoff to next package | child 4 combines hints with browser event timeline and DOM evidence. |

## Planned Package 4

| Field | Value |
|---|---|
| Package name | `11.3.11.4-terminal-state-agent-stop-control` |
| Status | planned |
| Type | code / mixed |
| Goal | Implement Terminal State Agent input/output and post-action advisory terminal-state judgment; document that true in-loop stop control remains future work. |
| Why this exists | Supervisor currently evaluates after exploration; the system first needs auditable terminal evidence before Attempt Evaluation and LearnedPath ingest can make safe decisions. |
| Inputs / required reading | child 1 Terminal State Agent contract; child 2 event timeline; child 3 terminal hints; autonomous explorer loop; wait_for_change; action executor; supervisor observation boundaries. |
| Allowed changes | Terminal State Agent schema/service, deterministic advisory stop policy metadata, bounded wait metadata, terminal verdict schema, attempt summary metadata, tests. |
| Forbidden changes | direct LearnedPath success claims, unbounded waits, target-specific rules, replacing Attempt Evaluation Agent, LLM step-by-step operation. |
| Expected deliverables | Terminal State Agent judgments for navigation, list refresh, network completion, modal/popup, dialog, download/artifact, toast/status, region change, no observable change; post-action stop/wait/continue/unverified decisions. |
| Expected tests / verification | unit tests per terminal type; integration tests with synthetic timelines and DOM snapshots; regression for search/list refresh not ending as a meaningless button click; live autonomous run default not run. |
| Compatibility constraints | Terminal State Agent output may be advisory for old paths; failure to detect must produce unverified/continue, not false success. |
| Scope guardrails | terminal judgment metadata only; no real in-loop timing mutation; final learning success remains child 5 / Attempt Evaluation gate. |
| Exit criteria | Terminal State Agent output is auditable, bounded, redacted, and consumed by Attempt Evaluation handoff. |
| Handoff to next package | child 5 consumes AttemptTerminalSummary for ingest and negative knowledge. |

## Planned Package 5

| Field | Value |
|---|---|
| Package name | `11.3.11.5-attempt-evaluation-ingest-gate` |
| Status | planned |
| Type | code / mixed |
| Goal | Feed terminal-state evidence into Attempt Evaluation and LearnedPath / negative-knowledge gates. |
| Why this exists | A terminal state alone is not proof of a useful learned path; the product needs a separate success / failure / unverified judgment before persistence. |
| Inputs / required reading | child 4 Terminal State Agent output; Attempt Evaluation Agent product boundary; supervisor observations; pass_gate semantics; learning_run_service; LearnedPath ingest; negative knowledge roadmap. |
| Allowed changes | AttemptTerminalSummary aggregate, Attempt Evaluation prompt/input or rule bridge, ingest gate, failure evidence persistence, learning outcome summaries, tests. |
| Forbidden changes | persisting failed/unverified attempts as successful LearnedPaths; removing operator trust lifecycle; bypassing pass_gate; changing L3 Task Path Planner to read raw HTML. |
| Expected deliverables | success/partial/failed/unverified attempt evaluation, evidence warnings, LearnedPath ingest eligibility, negative evidence retention, run history summaries. |
| Expected tests / verification | unit/API/service tests for all outcomes; regression for terminal_unverified not entering session learned catalog; live run default not run. |
| Compatibility constraints | old pass_gate and LearnedPath rows remain valid; new gate is additive and backwards compatible. |
| Scope guardrails | evaluation and persistence only; does not add Console report UX beyond data fields. |
| Exit criteria | child review confirms failed/unverified evidence cannot be user-facing success or successful LearnedPath. |
| Handoff to next package | child 6 renders and validates evidence through operator-facing surfaces and regression suite. |

## Planned Package 6

| Field | Value |
|---|---|
| Package name | `11.3.11.6-evidence-console-and-regression-suite` |
| Status | planned |
| Type | code / mixed / validation |
| Goal | Expose terminal-state evidence in history/debug surfaces and add regression coverage for representative terminal states. |
| Why this exists | Operators need to see why learning stopped, what evidence was used, which attempts failed, and why a path was or was not learned. |
| Inputs / required reading | child 2-5 outputs; exploration run history router; Conversation History / debug timeline docs; Console history pages; eval integrity rules; fixture-site boundaries. |
| Allowed changes | API read models, Console history/detail display, CLI/history summaries, regression artifacts, docs review updates. |
| Forbidden changes | raw payload dumping in terminal logs, unredacted request/response bodies, direct autonomous-run endpoint calls by Codex, live validation without approval. |
| Expected deliverables | terminal evidence summary UI/API/CLI, independent or deep-linkable LearnedPath detail entry, run_id/attempt_id/learned_path_id linkage, regression suite for list refresh/modal/download/navigation/no-change, latest redacted evidence docs when validation is authorized. |
| Expected tests / verification | unit/component/API tests; non-live eval where appropriate; live autonomous validation only after explicit user authorization with target, scenario and result-doc scope. |
| Compatibility constraints | old history pages continue rendering; missing terminal evidence shows as not available, not error. |
| Scope guardrails | display and regression only; does not add new Terminal State Agent semantics beyond child 4/5. |
| Exit criteria | operator can audit terminal evidence and regression results; final review records commands run, not run, and any live run_id/pass_gate if authorized. |
| Handoff to next package | M11.3 can proceed to child implementation and validation; future M14 may later reuse the terminal evidence contract for broader learning quality work. |

## 父包步骤

1. Create M11.3.11 parent umbrella docs and update M11 milestone README.
2. Record parent contract, child sequence, stop conditions and live-run boundary.
3. Set `CURRENT_STATE.md` active child to `11.3.11.1-terminal-state-agent-contract-taxonomy`.
4. End this pass after documentation integrity checks.
5. Do not create runtime code or run live autonomous validation in this pass.

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `find docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control -maxdepth 1 -type f -print` | parent docs exist | Yes | docs-only evidence |
| `rg -n "11.3.11|terminal|Terminal State Agent|active_child" docs/iterations/m11/README.md docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control` | index, contract and route are discoverable | Yes | no runtime execution |
| `git diff --check` | no whitespace errors | Yes | repository-level diff hygiene |

## 复核清单

- [x] 父包列出所有 planned child packages。
- [x] 每个 planned package 包含 required quasi-package fields。
- [x] 父包不授权 runtime implementation。
- [x] `CURRENT_STATE.md` 指向 child 1 docs generation。
- [x] 明确提出 Terminal State Agent，但不新增 legacy Agent 字母，且实现前需要 product-model 对齐。
- [x] 明确 Playwright / CDP first，不直接 fork Chromium。
- [x] 明确 failed / unverified evidence 不沉淀为成功 LearnedPath。
- [x] 父包包含 test-plan.md，child packages 仍需各自 test-plan。
- [x] 明确 live autonomous validation 默认不运行。
