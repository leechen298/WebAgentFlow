# 测试计划（Test Plan）

状态：proposed

## 范围

这是 `11.3.11-terminal-state-agent-learning-stop-control` 父包级测试计划。它定义 M11.3
post-closeout 终态判断路线需要如何验证，但不代表当前父包已经执行 runtime tests。

当前父包阶段只执行文档完整性检查。具体 unit / integration / API / Console / live validation
必须在对应 child package 创建七件套、完成设计复核并获得 implementation authorization 后执行。

## 测试目标

本迭代最终需要证明：

- Page Understanding Agent 能输出页面用途、页面内容、可能功能、页面区域和候选终态。
- Terminal State Agent 能基于精简版 AST、页面理解结果、PageAnalysis、attempt log、DOM /
  region snapshot 和 browser event timeline 判断 attempt 是否到达可评价终态。
- Exploration stop control 能在探索循环中做 bounded `stop` / `wait` / `continue` /
  `unverified_stop` 决策。
- Attempt Evaluation Agent 能消费 terminal summary，评价 attempt 成败和异常。
- LearnedPath gate 只允许 evidence clean / pass 的 attempt 沉淀；failed / unverified 只能进入
  run history、failure evidence 或 negative knowledge。
- Console / history / CLI 能让操作员看到为什么停止、证据是什么、是否沉淀、LearnedPath 在哪里。

## 测试层级

| Layer | Purpose | Default in parent | Live run? |
|---|---|---|---|
| Docs integrity | 检查父包和 child docs 是否完整、一致、无模板残留 | required | No |
| Unit | 验证 schema、event classifier、redaction、terminal decision helper | child required | No |
| Integration | 验证 browser event timeline、Terminal State Agent input bundle、stop control 与 run metadata | child required | No by default |
| API / service | 验证 exploration run history、LearnedPath gate、conversation / history read model | child required when touched | No by default |
| Console / CLI | 验证 evidence summary、LearnedPath detail entry、run/history links | child required when touched | No by default |
| LLM / Agent schema | 验证 Page Understanding Agent 和 Terminal State Agent 的 schema-constrained output | child required if Agent prompt is implemented | Provider live call not required by default |
| Live autonomous validation | 真实浏览器 + 真实 target 的端到端证据 | not run by default | Requires explicit user approval |

## Child Test Matrix

### 11.3.11.1 Terminal State Agent Contract & Taxonomy

Required checks:

- Product-model alignment review: Terminal State Agent is added or explicitly staged as proposed; no legacy Agent letter is invented accidentally.
- Contract completeness: terminal types, terminal outcomes, stop decisions, evidence strength, Agent input/output, redaction and compatibility are defined.
- Test-plan completeness: every later child has a concrete verification route.

Evidence:

- child `review.md` design review result;
- docs integrity command output;
- no runtime test claim.

### 11.3.11.2 Browser Event Recorder

Required non-live tests:

- Synthetic event unit tests for `request`, `response`, `requestfailed`, `download`, `dialog`, `popup`,
  `framenavigated`, `load`, `domcontentloaded`, `console`, `pageerror`.
- Redaction tests: tokens, cookies, auth headers, query secrets, request bodies and direct personal data are
  not stored.
- Correlation tests: event timeline links to run id, attempt id and action id.
- Failure tests: recorder failure does not crash exploration unless child contract explicitly says so.

Optional controlled-browser tests:

- Playwright fixture page emits download/dialog/popup/navigation events and timeline records them.
- Must be scoped to child test-plan; not a live autonomous validation claim.

### 11.3.11.3 Page Understanding Terminal Hints

Required tests:

- Page context bundle includes compact AST, screenshot or snapshot reference, PageAnalysis summary and
  redacted URL/title.
- Page Understanding Agent output schema includes:
  `page_purpose`, `page_content_summary`, `page_regions`, `possible_functions`,
  `candidate_terminal_states`, `confidence`, `reason_summary`.
- Representative page classes:
  list/search page, form/create page, detail page, report/export page, modal-heavy page.
- Boundary tests:
  Agent output must not contain executable selectors or invented fixture-specific values.

Provider policy:

- Use deterministic fixtures / mocked Agent output by default.
- Real LLM provider smoke is optional and must be recorded as `not_run` unless explicitly executed.

### 11.3.11.4 Terminal State Agent & Stop Control

Required terminal-state cases:

- `navigation`: URL/title/frame lifecycle changes and stabilizes.
- `list_refresh`: search/filter triggers network + table/region refresh.
- `network_completion`: relevant request completes but visible DOM change is weak.
- `modal_or_popup_opened`: modal/drawer/popover appears.
- `browser_dialog`: alert/confirm/prompt captured.
- `download_started`: download event captured.
- `artifact_available`: artifact metadata is available and safe to record.
- `toast_or_status_message`: transient status message captured.
- `region_changed`: specific region fingerprint/text/row count changes.
- `no_observable_change`: bounded wait ends without enough evidence.
- `terminal_failed`: network error, page error, download failure or blocking error surface.

Required stop-decision cases:

- `stop`: strong evidence, safe to evaluate attempt.
- `wait`: loading/request/DOM instability still within bounded timeout.
- `continue`: current action produced no terminal state and exploration can move on.
- `unverified_stop`: max wait reached or evidence conflicts; cannot claim success.

Required safety regressions:

- URL-only `/users`-type search page must not collapse into a successful LearnedPath that only clicks a
  generic search button without field binding / terminal evidence.
- Silent refresh must not be treated as success unless network and region or page-understanding evidence
  meet child gate.
- Terminal State Agent uncertainty must become `terminal_unverified`, not false success.

### 11.3.11.5 Attempt Evaluation & LearnedPath Gate

Required tests:

- `terminal_detected + clean evidence + Attempt Evaluation success` can enter LearnedPath candidate.
- `terminal_unverified` never enters successful LearnedPath or current-session learned action catalog.
- `terminal_failed` records failure evidence / negative knowledge.
- `no_observable_change` is not user-facing success.
- Attempt Evaluation Agent receives terminal summary but does not control browser or decide wait loops.
- Existing pass_gate and trust lifecycle remain compatible.

Regression tests:

- Existing confirmed / provisional LearnedPath replay continues to work.
- Failed/unverified runs remain visible in history.
- User-facing learning feedback does not overclaim.

### 11.3.11.6 Evidence Console & Regression Suite

Required API / UI / CLI tests:

- Run history detail shows terminal outcome, terminal type, evidence strength, stop decision and warnings.
- Conversation history learning summary links to run id and learned_path_id when present.
- LearnedPath catalog remains usable.
- LearnedPath detail becomes independent or deep-linkable enough that a user can navigate from run history /
  conversation history to a specific path without hunting through the catalog manually.
- LearnedPath detail shows source run, attempt evidence, terminal evidence summary, trust, actions and replay
  result.
- Missing terminal evidence in old runs renders as not available, not error.

Regression suite must include representative cases for:

- list refresh;
- modal / drawer / popup;
- download / export;
- navigation;
- toast / status message;
- no observable change;
- terminal failure.

## Live Validation Gate

Live autonomous validation is not part of the parent docs pass and is not run by default.

Before any live run, the active child `test-plan.md` must name:

- approved target URL;
- approved scenario or product surface;
- allowed validation entry: product UI or approved `verify-scenario` skill only;
- expected evidence updates;
- redaction path;
- operator action log requirement.

Every live result must record:

- invocation surface;
- command or UI operation;
- run_id;
- `pass_gate.status`;
- Supervisor verdict and scorecard when produced;
- Terminal State Agent outcome;
- learned_path_id if created;
- result artifact path.

Direct `curl`, hidden httpx/fetch, service import or direct autonomous-run endpoint invocation is prohibited.

## Current Parent Verification

For the current parent package only, run:

| Command | Expected |
|---|---|
| `find docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control -maxdepth 1 -type f -print | sort` | parent docs including `test-plan.md` exist |
| `rg -n "Terminal State Agent|Page Understanding Agent|LearnedPath detail|live autonomous validation" docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control` | Agent boundary, detail entry and live-run boundary are discoverable |
| `rg -n "T[B]D|T[O]DO" docs/iterations/m11/11.3.11-terminal-state-agent-learning-stop-control` | no template residue |
| `git diff --check` | no whitespace errors |

## Not Run In Parent

- Runtime unit tests: not run.
- API / service tests: not run.
- Console / CLI tests: not run.
- LLM provider smoke: not run.
- live autonomous validation: not run.

Reason: this parent package is docs-only / umbrella planning. Runtime validation belongs to child packages
after design review and explicit authorization.
