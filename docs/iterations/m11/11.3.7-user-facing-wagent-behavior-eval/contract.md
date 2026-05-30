# 契约（Contract）

状态：pass（first-wave user-facing behavior gates passed；full learn-then-execute remains follow-up）

## 概念 / 边界契约

### User-facing behavior eval

11.3.7 验证的是 WAgent 面向普通用户的入口行为，而不是底层 replay、slot binding、
Reporter adapter 或 pending choice 私有映射的孤立单元能力。

用户视角行为包括：

- 页面 URL 输入后的状态判断；
- 明确学习请求；
- 明确执行请求；
- 模糊请求；
- 用户补充信息；
- 多候选选择；
- 执行失败后的恢复菜单。

### Learned page state

页面状态必须从产品数据或当前 session 状态推导：

| State | Meaning | Required behavior |
|---|---|---|
| `known_page` | 当前 eval session 或 explicit eval scope 中存在可用 learned action | 列出可执行操作或匹配用户目标 |
| `unknown_page` | 当前 eval session / isolated scope / explicit filtered catalog 中没有可用 learned action | 说明还没学过，并引导学习或取消 |
| `ambiguous_page` | URL / target 不足或无法解析 | 追问目标页面，不执行 |

Known / unknown isolation is required:

- known cases may only use learned actions created or selected for the current eval session / eval scope;
- unknown cases must use a fresh session, isolated scope, explicit filtered catalog, or equivalent
  deterministic isolation;
- global historical LearnedPath rows must not make an unknown case look known;
- if old global LearnedPath data cannot be isolated, the unknown case is `blocked`, not pass.

### User intent handling

| Intent family | Example meaning | Required behavior |
|---|---|---|
| `url_only` | 用户只发页面链接 | 查 learned actions，再按 known / unknown 分支引导 |
| `execute_known` | 用户明确要求执行已学操作 | 匹配 learned action、补参数、执行、验证 evidence |
| `execute_unknown` | 用户要求执行未学操作 | 不直接 replay；询问是否学习并执行、只学习或取消 |
| `learn_explicit` | 用户明确要求学习操作 | 进入学习流程，保存 LearnedPath，标记可替换参数 |
| `vague_input` | 用户说法无法确定目标或操作 | 不执行；要求用户提供页面或操作目标 |
| `pending_continuation` | 用户回答上一轮追问 | 续接原任务，不丢 target，不重开任务 |
| `choice_selection` | 用户选择 A / 1 / 第一个 | 解析 public choice，内部映射到 private action |
| `recovery_selection` | 用户在失败菜单中选择重试 / 重新学习 / 取消 | 按 public wording 执行对应安全出口 |

### Anti-hardcoding / generalization gate

测试页面细节是 eval 数据，不是产品能力。以下内容不得出现在功能代码或产品提示词中：

- 测试页面 URL、host、port、route 或路径模板；
- 测试页面专有标题、说明文案、按钮名、字段 label、placeholder；
- fixture 专有业务实体名、fixture item names、测试 item 名称、operation aliases、测试别名；
- DOM test id、fixture selector、fixture CSS class；
- 针对该测试页面的 hard-coded operation list 或 branching rule；
- 只为了通过本轮测试而加入的 prompt 示例、few-shot 或自然语言模板。

允许出现这些内容的位置仅限：

- 测试 fixture 自身，例如 fixture-site 页面源码；
- eval spec / test data / test-only fixtures；
- eval runner 的测试配置层，前提是它不被产品 runtime import；
- unit / integration / E2E 测试文件；
- docs、review、testing result 和 redacted artifact。

These allowed locations are not runtime configuration. Product runtime must not import eval specs,
test-only fixtures, docs, review files, testing results, or artifacts to learn target details.

功能代码包括但不限于：

- `apps/api/app/services/**`
- `apps/api/app/routers/**`
- `apps/api/app/schemas/**`
- `apps/cli/wagent/**`
- `apps/console/src/**`
- product prompt assets、prompt registry、system prompt、developer prompt、few-shot examples。

如果 implementation 需要识别页面能力，只能使用通用 page analysis、DOM / accessibility 信号、
LearnedPath metadata、用户消息和明确的 eval spec 输入，不能靠测试页面常量。

Existing target-specific runtime special cases are blockers. Examples include route checks such as
the test page path, selector checks such as the test list selector, hard-coded fixture field names,
or operation aliases that only exist to pass the fixture-site scenario. They must be removed,
made generic, or moved into eval spec / test-only code before 11.3.7 can pass.

No grandfather exception is allowed. If cleanup cannot happen in the 11.3.7 implementation run, the
review must open a cleanup issue / follow-up and mark 11.3.7 `blocked`; it must not mark the eval pass.
Opening a cleanup follow-up is only a way to record why the eval is blocked, not permission to ship
or pass with target-specific runtime behavior still present.

## 状态 / 结果契约

### Eval result status

| Status | Meaning |
|---|---|
| `pass` | 所有 required gates 通过，且 forbidden-token hard gate 通过 |
| `fail` | 任一 required behavior gate 失败，或发生误执行 / 泄露 / hardcoding |
| `blocked` | API、product test surface、database 或 required credentials 不可用 |
| `unverified` | 只做了文档或静态检查，没有执行对应 runtime / UI / CLI case |

### First-wave required scenarios

第一批 required scenarios：

1. `url_only_known_page`
2. `url_only_unknown_page`
3. `execute_known_action`
4. `execute_unknown_action`
5. `vague_input_no_execution`
6. `forbidden_test_target_not_in_runtime_code_or_prompts`
7. `url_only_unknown_choose_learn_starts_learning`
8. `execute_unknown_choose_learn_then_execute_or_learning_flow`

`url_only_unknown_choose_learn_starts_learning` is required. After WAgent says the page is not learned,
the user's public learn choice must enter a real learning flow or produce a product-level blocked
state with evidence. A no-op reply, fake learning-complete text, or hidden execution is fail.

`execute_unknown_choose_learn_then_execute_or_learning_flow` has a staged contract:

- if full `learn_then_execute` is supported, the case must prove learning succeeded, execution ran
  after learning, and evidence verified the final result;
- if full `learn_then_execute` is not supported, the case may only pass the narrower learning-flow
  gate: choosing the learn option starts the controlled learning flow and does not claim execution;
- in the latter case, full learn-then-execute must be recorded as a follow-up, not a pass.

### Follow-up scenarios

后续可扩展 scenarios：

- `learn_explicit_action`
- `pending_slot_continuation`
- `choice_selection_public_to_private`
- `failure_recovery_public_menu`
- `page_capability_discovery_controlled`
- `multi_operation_learning_controlled`
- `natural_language_reuse_multiple_actions`

## Schema / API 契约

本轮文档不直接修改 schema、API、database 或 CLI contract。

后续实现如果新增 eval runner，应遵守：

- 通过 Conversation API 或既有 project eval runner surface 驱动 WAgent。
- eval spec 可以包含目标页面 URL、用户话术、expected public text fragments、
  expected behavior gates、forbidden runtime tokens。
- eval spec 不得被产品 runtime import。
- public response / events 不得暴露 `learned_path_id`、selector、private map、
  slot overrides、ReplayAction 或 raw planner payload。
- target-specific details 只能作为 eval input 和 assertion data，不得进入 product prompt。

## Evidence / Observation 契约

允许的 evidence 来源：

- Conversation API response、messages、events 和 session metadata；
- project eval runner 写出的 JSON / Markdown artifact；
- LearnedPath catalog 的只读查询结果；
- replay / reporter 产生的 DOM evidence summary；
- 明确批准的 Console UI 或 CLI 操作记录。

不允许的 evidence 来源：

- Codex 直接调用 autonomous-run endpoints；
- hidden service import 或 hidden HTTP client；
- 直接调用 replay API 后冒充 WAgent conversation；
- 未执行的推理结论；
- 未脱敏 raw artifact。

任何 “执行完成” 或 “失败恢复菜单正确” 结论都必须绑定可复查 product evidence。

## 产品模型 / 范围 / 路线图对齐（Product Model / Scope / Roadmap Alignment）

- Product model 对齐：仍属于 M11 L3 runtime conversation / actual work MVP 的入口行为验收。
- Scope boundary 对齐：不提前实现 L1 Page Understanding Agent，不做 M12 complex recovery。
- Roadmap / milestone 对齐：作为 11.3 working runtime 在 11.3.6 之后的用户视角验收包。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A，因为本包不改变 lifecycle、Agent role 或 milestone。

## 兼容性契约

- 11.3.6 runtime eval artifacts 和 pass_with_caveats 结论继续有效。
- 11.3.7 不重写 11.3.6 的 raw results，只补充更准确的 scope boundary。
- 既有 Conversation API、LearnedPath catalog、Task Path Planner 和 Task Result Reporter
  contract 不因本轮文档变化而改变。
- 后续实现如发现功能代码已有测试页面常量，必须作为 11.3.7 阻断项或单独 cleanup task 处理，
  不能让新的 eval 靠这些常量通过。
- Cleanup follow-up is not a grandfather exception. Until the target-specific runtime / prompt content
  is removed or isolated into test-only layers, 11.3.7 remains `blocked`.
- Known current runtime special cases must be cleaned up during implementation, not accepted as
  historical behavior.

## 不变契约

本轮不改变：

- Product lifecycle stages：仍为 L1 / L2 / L3。
- Internal Agent roles：不新增 Agent，不新增 legacy letter。
- Public API contracts：文档阶段不改。
- Database schema：文档阶段不改。
- Replay status semantics：不改。
- Reporter / recovery / abort boundaries：不改，只定义用户视角验收。

## 非目标

- 不证明任意页面全自动 capability discovery 已完成。
- 不证明 WAgent 能自动学习页面所有操作。
- 不证明已生成完整页面操作库。
- 不在未知操作上静默 learn-then-execute。
- 不把测试页面常量写入产品 prompt 来提升通过率。
- 不让 global catalog 中的旧 LearnedPath 决定 unknown case。

## 未决问题

- 11.3.7 第一版 runner 是否复用 11.3.6 `scripts/evals/wagent_runtime_eval.py`，还是新建
  user-behavior runner：implementation design review 决定。
- known / unknown 页面状态必须隔离；implementation design review 只决定具体机制：
  fresh session、isolated eval scope、explicit filtered catalog，或等价方案。
