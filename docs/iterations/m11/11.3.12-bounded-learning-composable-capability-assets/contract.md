# Contract

状态：proposed

## Scope

本包定义 L1 autonomous learning 的原子能力资产、有限学习策略和 L3 runtime composition
契约。它不改变 L1 / L2 / L3 lifecycle，不新增内部 Agent 角色。

## New Concepts

### LearnedCapability

`LearnedCapability` 是页面级可复用原子能力资产。它比 LearnedPath 更小，表达“系统已验证可以
对某个页面区域执行某类操作，并观察到某类终态”。

示例能力：

- `control_input`：给文本输入框、搜索框、日期输入、month picker 设置值。
- `control_select`：选择 native select、combobox、cascader 或组件库下拉项。
- `control_toggle`：切换 radio、segmented、checkbox、switch。
- `submit_search`：点击搜索 / 应用筛选按钮，并观察列表刷新、URL query、请求完成或空结果。
- `reset_filters`：点击重置，并观察控件状态和结果区恢复。
- `switch_tab`：切换 tab，并观察子区域变化。
- `open_detail`：打开详情页或详情弹窗。
- `export_download`：触发导出 / 下载，并观察 browser download event 或 export request。
- `show_modal_or_toast`：点击按钮后出现 modal、drawer、popover、toast 或 dialog。

### CapabilityEvidence

证明某个 LearnedCapability 可用的证据包。至少包含：

- source `exploration_run_id` 或 user demonstration reference；
- action-scoped browser event / DOM before-after / terminal-state verdict；
- action binding summary；
- terminal evidence type；
- evidence strength；
- failure warnings；
- provenance: `system` or `user`。

### CapabilityCompositionPlan

运行时由代码构建的能力组合计划。它不是 LearnedPath，只有在真实执行并通过 evidence gate 后，
才可以沉淀为 LearnedPath。

Required fields:

- `composition_id`
- `target_url` / page signature scope
- `user_goal`
- `source_capability_ids`
- ordered action plan
- expected terminal target
- risk / confidence
- missing capability list

### BoundedLearningPolicy

控制自主学习范围的策略，避免页面能力学习退化为全排列搜索。

Required policy dimensions:

- max wall-clock duration
- max scenario count
- max failed attempts per selector / adapter
- max consecutive no-new-capability attempts
- default single-capability learning set
- allowed dependency combinations
- stop / partial_success / timed_out rules

### LearningBatch

一次 `start_learning` 触发的可审计批次。它必须有生命周期状态，而不是只依赖 HTTP request 是否还活着。

Allowed states:

- `running`
- `completed`
- `partial_success`
- `timed_out`
- `cancelled`
- `failed`
- `unverified`

## Asset Relationship Contract

The asset layers are:

```text
ExplorationRun
  -> learned_capabilities
  -> runtime composition
  -> LearnedPath
```

Rules:

- ExplorationRun is raw attempt history and evidence.
- LearnedCapability is reusable atomic evidence.
- LearnedPath is a replayable complete path.
- A LearnedPath may cite zero or more source LearnedCapability ids.
- A LearnedCapability must not claim a complete user workflow by itself.
- A CapabilityCompositionPlan must not be persisted as a successful LearnedPath until execution evidence passes gate.

## Page Understanding Contract

Page Understanding Agent remains the existing L1 role. This package expands what its output may inform:

- page purpose;
- region inventory: filter area, result area, action bar, tab set, modal roots, export controls;
- likely functions;
- terminal-state candidates;
- sample value candidates and their source;
- dependency hints, for example date range pair, tab-scoped controls, cascader levels.

It must not output step-by-step browser execution, selector-only actions, or direct Playwright commands.

## Bounded Learning Contract

Default learning must not enumerate all combinations.

Required default coverage:

- learn each supported independent control operation at least once when budget allows;
- learn each primary submit/action button terminal behavior once when budget allows;
- learn tab switch behavior and then run scoped discovery inside the active tab only when tab content changes;
- learn dependency pairs only when Page Understanding or structural rules identify dependency;
- preserve failed / unsupported capability evidence without retry loops.

Default non-goals:

- no exponential all-field combination matrix;
- no repeated attempts against the same failing selector beyond budget;
- no waiting for full page completion if enough evidence supports `partial_success`;
- no product runtime hardcoding of page routes, fixture labels, or target values.

## Empty Result Contract

Search returning zero rows can be a valid terminal state if evidence shows request completion, list refresh,
result count update, query persistence, or empty-state UI.

It must be labeled as weaker evidence than a known-hit search:

- `terminal_outcome=terminal_detected` may still be valid.
- `business_match_observed=false` must be preserved when no row matches the requested business value.
- User-facing learning report must not imply a business hit when only empty-result completion was observed.

## Runtime Composition Contract

L3 may compose LearnedCapabilities only under code-owned rules:

- Agent may parse user intent and recommend capability categories.
- Code retrieves scoped LearnedCapabilities and checks compatibility.
- Code builds the ordered plan and validates risk.
- Browser execution remains in replay / execution services.
- Successful composition may be promoted to LearnedPath after pass gate.
- Failed composition becomes negative capability evidence and may route to L2 teaching.

The system must prefer an existing high-confidence LearnedPath over composition when both are available.

## Learning Batch Lifecycle Contract

`wagent chat` timeout or disconnect must not leave browser-driving learning work unbounded.

Allowed behaviors:

- cancel the backend batch and close browser resources; or
- explicitly detach it into an async job with `learning_batch_id`, progress, cancellation, and history status.

Forbidden behaviors:

- backend continues to open browser windows with no user-visible batch handle;
- session remains forever in `active_task.status=learning`;
- conversation emits success without closed batch evidence;
- batch writes LearnedPaths after being marked cancelled.

## Compatibility Contract

- Existing LearnedPath rows remain readable and replayable.
- Existing ExplorationRun rows remain readable.
- `learning_run_service` may continue to return aggregate capability summaries, but future summaries should be derived from persisted LearnedCapability evidence when available.
- `wagent verify` / spec-backed autonomous runs are not replaced by this package.
- L2 user-demonstration provenance must remain distinct from L1 system provenance.

## Runtime Hardcoding Prohibition

Product runtime must not hardcode:

- `/users`;
- target field labels;
- target button text;
- fixture data values;
- DOM test ids;
- route-specific prompt text;
- validation-site-only aliases.

Target details may appear only in tests, fixtures, docs, and redacted artifacts.

## Implementation Authorization

This contract does not authorize implementation by itself. Implementation requires reviewed
`technical-design.md`, reviewed `test-plan.md`, and `implementation_authorized: yes` in `review.md`.
