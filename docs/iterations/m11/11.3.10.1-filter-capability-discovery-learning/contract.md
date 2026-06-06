# Contract

## Scope

本包定义并实现 L1 autonomous learning 的筛选页 capability discovery contract。
适用入口是 product-level URL-only learning：用户只给页面 URL，未提供 authored spec、
scenario id 或字段值映射。

本包不改变 spec-backed autonomous run。已有 authored spec / scenario 的验证路径仍按原契约运行。

## New Concepts

### PageCapabilityDiscovery

一次页面能力发现批次。它从 PageAnalysis、页面结构、控件语义、可见表单区域和 action planner
可支持的 adapter 中生成 capability inventory 和 scenario matrix。

Required fields:

- `discovery_batch_id`
- `page_url`
- `page_signature`
- `source_analysis_id` or equivalent source snapshot reference
- `candidate_capabilities`
- `generated_scenarios`
- `created_run_ids`
- `passed_learned_path_ids`
- `failed_or_unverified_scenarios`

### FilterCapability

页面上的一个可学习筛选能力。它不是 DOM 节点本身，而是一个有业务语义、可绑定输入、可提交、
可观察结果的 filter/search unit。

Required fields:

- `capability_id`
- `kind`
- `human_label`
- `control_ref`
- `control_type`
- `adapter_type`
- `supported`
- `support_reason`
- `default_test_value_source`
- `submit_ref`
- `observation_target`

### CapabilityScenario

围绕一个或多个 `FilterCapability` 生成的可执行学习场景。

Required fields:

- `scenario_id`
- `capability_id`
- `scenario_kind`
- `human_label`
- `input_bindings`
- `expected_observation_target`
- `discovery_batch_id`
- `source_capability_ids`
- `pass_gate_required`

## Scenario Kinds

Allowed `scenario_kind` values:

- `single_filter`
- `pairwise_filter`
- `all_supported_filters_smoke`

## All Filter Items Contract

“所有筛选项”在本包内的含义：

所有被 PageAnalysis / DOM analysis 识别为筛选或搜索控件，且存在通用 adapter 支持的控件，
都必须进入 candidate scenario set。

不能因为控件来自 Ant Design、Element Plus 或其他组件库而静默跳过。尤其不得静默跳过：

- text input
- search input
- radio
- segmented status
- select
- combobox
- cascader
- date picker
- range date picker
- month picker

如果控件被识别但暂不支持，必须保留 unsupported capability evidence：

- `supported: false`
- `support_reason`
- raw control evidence
- skipped scenario reason

## Combination Search Contract

“各种组合搜索”的默认契约不是全排列。默认生成：

1. 每个 supported filter 一个 `single_filter` scenario。
2. supported filters 的 pairwise combination matrix。
3. 一个 `all_supported_filters_smoke` scenario。

不得在 product runtime 中做指数级全排列，避免对真实页面产生过多动作和不必要成本。

## LearnedPath Ingest Contract

LearnedPath 只能从通过证据门禁的 scenario 沉淀：

- `pass_gate.status == "pass"` or equivalent clean evidence outcome。
- scenario actions 具有具体筛选语义。
- scenario run history 已持久化。
- scenario metadata 可追溯到 discovery batch。

失败、阻塞、未验证或证据不足的 scenario：

- 必须保留 autonomous run history。
- 必须保留 failure / unverified evidence。
- 不得进入 LearnedPath。
- 不得进入当前 session learned action catalog。

## Runtime Hardcoding Prohibition

产品 runtime 不得硬编码：

- `/users`
- 字段名
- 按钮文案
- fixture 数据
- DOM test id
- route-specific prompt

这些内容只能出现在：

- 测试
- fixture
- 文档
- eval artifact

## Metadata Contract

每个 scenario run 的 `strategy_json` or equivalent metadata 必须包含：

- `kind`
- `discovery_batch_id`
- `capability_id`
- `scenario_id`
- `scenario_kind`
- `capability_label`
- `bound_controls`
- `source_capability_ids`
- `product_level: true`

原先笼统的 `scenario: null` 或 `scenario: product_level` 不足以表达本包新增能力。

## Backward Compatibility

- Existing LearnedPath rows remain readable.
- Existing ExplorationRun rows remain readable.
- Spec-backed autonomous run behavior must not regress.
- Explicit user-taught learning flow must not lose user-provided goal / aliases.

## Non-goals

- 不做 L2 guided teaching。
- 不做 M12 recovery / retry / abort。
- 不做 active browser tab support。
- 不让 LLM 逐步控制浏览器。
- 不把 AI coding agent 当作产品内部 Supervisor Agent。
