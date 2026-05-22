# 契约（Contract）

状态：implementation complete（code review passed，targeted tests passed）

## 概念 / 边界契约

### Planner Chat Integration

Planner Chat Integration 是 `wagent chat` 中的多候选 planning path。它只在 Runtime 已经
判断不能安全直接执行时触发。

允许触发：

| 场景 | 说明 |
|---|---|
| 多个 learned actions 匹配 | 同一用户目标命中多个候选 |
| 用户目标模糊 | “帮我处理一下这个页面”、“搞一下” |
| 用户给了 URL 但 action 仍模糊 | `http://localhost:<port>/items 帮我处理一下` |
| planning preview / confirmed execution path | 需要先展示候选再等用户选择 |
| candidate trust / drift warning 需要展示 | Planner 生成 warning / risk hint |

禁止触发：

| 场景 | 处理 |
|---|---|
| 单个 learned action 且目标明确 | 直接 replay |
| `/items` 新增项目 happy path | 直接 replay |
| 无 learned action | 走 no-path / learning guidance，不让 Planner 编造 |
| Failure Recovery A/B/C | 归 11.3.5.8，不走 Planner |
| learn_then_execute | 继续保守阻断 |

触发规则：

```text
if len(candidates) > 1 and cannot_confidently_select_single_action:
    enter planner choice path
```

`user_url` 只能作为 `target_page_hint`，不得作为跳过 Planner / choice 的条件。用户给了
URL 但 action 仍然模糊时，仍应进入 Planner + pending_choice。

### Runtime Priority Before Planner

Planner path 只能在现有 live context 都不能处理当前输入之后触发。优先级：

```text
pending_choice / recovery choice
active_task
pending_intake
pending_target
deterministic single-action match
planner multi-candidate / vague-goal path
```

“继续”不是默认 Planner 模糊目标。只有在没有 `pending_choice`、recovery choice、
`active_task`、`pending_intake`、`pending_target` 等 live context 可继续时，才可以作为
普通模糊输入进入 Planner clarification / choice。

### Candidate Source

11.3.5.9 的 chat integration 默认只使用当前 conversation session 的 `learned_actions`
作为候选来源。Planner 不得引入用户当前 session 不可见的 learned path。

Runtime 可以读取 LearnedPath repo 补充候选 metadata，例如：

```text
scenario
page_template
trust
hit_count
trust_reason / drift evidence summary
```

但最终候选集合必须满足：

```text
candidate.learned_path_id ∈ current_session.learned_actions[*].learned_path_id
```

### TaskIntent Construction

Runtime 构造 `TaskIntent` 时，只使用当前用户输入、Intake 结果和 runtime context：

```text
raw_text = user raw input
normalized_goal = intake.action.canonical_goal or intake.action.goal
target_page_hint = intake.target.url path or current/pending target page_template
scenario_hint = intake.action.canonical_goal or matched action alias when safe
uncertainty = intake uncertainty / vague-goal marker
```

不得调用 LLM 重新规划，不得读取 raw HTML，不得启动 autonomous exploration。

### Visible Pending Choice

用户可见 `pending_choice` 只暴露：

```ts
type PlannerVisibleChoice = {
  choice_id: "A" | "B" | "C" | "D";
  label: string;
  description?: string;
  intent: "execute_operation" | "learn_operation" | "understand_page" | "cancel" | "other";
};
```

visible payload 和 WAgent 回复不得包含：

```text
learned_path_id
selected_path_id
selector
browser_action
ReplayAction
slot_overrides
route_plan.raw steps
private mapping payload
```

### Planner Private Map

真实执行信息只能写入 `pending_choice_private_map`，并且只允许 Runtime / Orchestrator 使用。

推荐结构：

```ts
type PlannerPrivateChoice = {
  kind: "planner_route_choice";
  learned_path_id: string;
  target_url: string;
  action_alias?: string;
  page_template?: string;
  slot_overrides?: Record<string, string>;
  planner_summary?: {
    candidate_index: number;
    purpose?: string;
    confirmation_required?: boolean;
    warnings?: string[];
    risk_hints?: Array<{ type?: string; reason?: string; severity?: string }>;
    uncertainty?: string[];
  };
};
```

如果实现复用 11.3.5.7 的 `kind: "learned_action"` 也可以，但必须保存足够信息用于：

- 用户选择后执行正确 path；
- 保留 `slot_overrides.item_name` 等 runtime slot；
- 记录 sanitized planning event；
- 不向 LLM / user / public session payload 泄露 private map。

### Planner Output Mapping

当前 `TaskPathPlanner.plan(task_intent, candidates)` 不返回多个候选列表。它消费 Runtime
传入的 ranked candidates，选择 top valid candidate 生成单一 `route_plan`，并通过
`confirmation_requirements`、`risk_hints`、`uncertainty`、`warnings` 表达风险或模糊性。

因此：

```text
TaskPathPlanner 不负责生成 A/B/C 候选列表。
Runtime 基于 ranked session candidates 生成 A/B/C。
Planner output 只给 top candidate 提供 route_plan / warning / risk / uncertainty 信号。
```

TaskPathPlanner output 到 Runtime choice 的映射规则：

| Planner output | Runtime 行为 |
|---|---|
| `route_plan is None` | 不执行；给 no-plan / learning guidance |
| `route_plan.steps` 为空 | 不执行；给 no-plan / learning guidance |
| 单个候选但 trust / risk 需要确认 | 展示 confirmation choice，不直接执行 |
| 多个候选 | Runtime 按 ranked session candidates 展示 choice |
| Planner top candidate matches choice A | choice A 可带 sanitized planner description / warning / confirmation hint |
| warnings / risk_hints / uncertainty | 只以 sanitized description / hint 展示 |

注意：现有 `PlanningPreviewService.preview()` 的 user_response 会包含 `Selected path:
<learned_path_id>`。11.3.5.9 不得把该 raw response 直接作为 `wagent chat` 用户回复。

### Event Contract

允许记录：

```text
planner_candidates_generated
planner_choice_created
planner_choice_selected
planner_unable_to_plan
planner_fallback_used
```

event payload 可以包含：

```text
candidate_count
choice_group_id
selected_choice_id
planner_warning_count
planner_risk_count
confirmation_required
public action alias
page_template
```

event payload 不得包含：

```text
pending_choice_private_map
learned_path_id
selected_path_id
slot_overrides
ReplayAction
selector
route_plan raw private steps
runtime slot values
item_name raw value
credential / token / secret
```

### Compatibility Contract

- 11.3.5.6 `/items` verified happy path 不能变慢或进入 Planner。
- 11.3.5.7 choice parser / private map / cancel cleanup 继续复用。
- 11.3.5.8 recovery choice 不受 Planner 影响。
- 进入实现前必须 preflight 确认 11.3.5.7 / 11.3.5.8 targeted tests 通过。
- Router 仍然只能推荐，不执行 skill，不输出 path id。
- TaskPathPlanner 仍然是 deterministic service，不调用 LLM / browser / autonomous run。

## 非目标

- 不新增 DB migration。
- 不新增 public API endpoint。
- 不修改 TaskPathPlanner domain schema，除非实现发现不可避免的 contract 缺口并先更新文档。
- 不把 global LearnedPath catalog 全量暴露进当前 chat session。
- 不实现多步 route execution。
- 不实现 formal plan confirmation slash commands；本包使用 `pending_choice` 作为用户确认入口。
