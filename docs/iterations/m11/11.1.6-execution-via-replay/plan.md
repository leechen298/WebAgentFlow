# 实施计划

## 输入与依赖

未来实现前必须先 inspect 当前 conversation orchestrator、confirmation gate、
replay hook 和 replay service，再决定最终 module boundary。

预期输入：

- conversation session 已处于 `plan_confirmed` 或等价
  confirmed-but-not-executed 语义；
- conversation events 中存在最近一次 confirmed plan evidence；
- selected LearnedPath id；
- target URL 或 replay entry context；
- route summary / route step metadata（如存在）；
- 现有 deterministic replay service / explicit replay hook。

可能实现位置：

- 实现前先 inspect 现有 replay service / replay handler，再决定最终路径；
- conversation 侧集成大概率位于 `apps/api/app/services/conversation/`；
- replay logic 应复用现有 replay service 或 command hook；
- tests 大概率位于 `apps/api/tests/`。

本轮文档阶段不创建代码文件。

## Execution Preconditions

只有同时满足以下条件，才允许进入 replay execution：

- conversation 已有 confirmed plan；
- 用户 consent 已通过 11.1.5 记录；
- plan 尚未执行；
- plan 未被 cancelled、rejected 或 superseded；
- selected LearnedPath id 可用；
- target URL 或 replay entry context 可用；
- route plan / selected path 仍可从 conversation events 审计。

如果缺少任何必需输入，11.1.6 不得猜测。它应返回 unable-to-execute 或
needs-more-context 语义，并记录 blocked event。

## Confirmed Plan Lookup

第一版实现应从 conversation events 中恢复 confirmed plan evidence：

- 最近的 `plan_preview_proposed` event：用于 selected path、warnings、risk
  hints 和 route summary；
- `plan_confirmed` event：用于 user consent 和 decision timestamp；
- 如有必要，可用 assistant message metadata 作为辅助证据。

11.1.6 不得从 raw user text 重建 plan。

11.1.6 不得再次调用 Task Path Planner，除非后续包明确设计 re-planning。

后续包可以引入 persisted execution context；第一版 execution-via-replay 设计不要求
先做这件事。

## Replay Invocation Boundary

第一版实现应复用现有 deterministic replay 能力。如果已有 service-level replay
function，不应通过 HTTP self-call 绕一圈。

如果现有 replay hook 只接受：

```text
learned_path_id + url
```

那么 11.1.6 第一版只有在两个字段都显式存在时才能执行。

Replay invocation 不得：

- 调用 autonomous run；
- 触发 browser exploration；
- 读取 raw HTML 做 planning；
- 调用 LLM provider；
- 做 slot binding；
- 发明 browser actions。

## Missing Execution Context Behavior

当 selected path 或 target URL / entry context 缺失时：

- 不执行 replay；
- 不调用 Task Path Planner；
- 不调用 autonomous learning；
- 追加 execution-blocked event；
- 返回用户可读消息，说明缺少执行上下文。

建议 assistant message 语义：

```text
The confirmed plan is not executable because required replay context is missing.
```

## Conversation Event Recording

计划中的 event 语义：

- `plan_execution_started`
- `plan_execution_completed`
- `plan_execution_failed`
- `plan_execution_blocked`

`completed` 只表示 replay invocation completed，不表示 business result
verification succeeded。

Event payload 应包含：

- `learned_path_id`；
- target URL / entry context（如存在）；
- route step id 或 route summary（如存在）；
- replay run id / execution id（如存在）；
- replay result summary（如存在）；
- no result verification marker；
- failed 时的 error summary；
- no autonomous marker；
- `task_verified: false`。

11.1.6 events 不存 raw HTML、screenshots、user/account/tenant fields，也不存
result verification verdicts。

## Conversation State Transition Options

未来实现可能需要新增 conversation statuses。候选语义：

```text
plan_confirmed -> executing
executing -> execution_finished
executing -> execution_failed
execution_finished -> task_intake or awaiting_result_review
execution_failed -> task_intake or needs_review
```

本轮文档阶段不修改 schema。

`execution_finished` 不表示 result verified。

## Assistant Message Behavior

Execution started:

```text
Replay execution started for the confirmed plan.
```

Execution completed:

```text
Replay execution completed. Result verification is not implemented in this package.
```

Execution failed:

```text
Replay execution failed before result verification. No recovery was attempted.
```

Execution blocked:

```text
The confirmed plan is not executable because required replay context is missing.
```

具体文案可以在实现时调整，但不得声明 task success。

## Explicit Replay Compatibility

`/replay <learned_path_id> <url>` 仍然是 explicit replay command。

Confirmed-plan execution 和 explicit replay command 是相关但独立的入口：

- explicit replay 使用用户提供的 path id 和 URL；
- confirmed-plan execution 使用此前已确认的 plan 和它的 replay context；
- 11.1.6 不得破坏 direct explicit replay；
- 11.1.6 不得破坏 11.1.5 中 `/replay` 在 `awaiting_confirmation` 下会被
  blocked 的行为。

## Result Verification Boundary

11.1.6 不得声明业务成功。它最多记录：

```text
replay execution completed
```

它不得记录：

```text
task succeeded
business result verified
artifact produced
form submission confirmed
```

这些属于 future Result Verification and Task Result Reporter。

## Testing Plan

未来实现测试至少应覆盖：

- session 不是 `plan_confirmed` 时 execution blocked；
- selected LearnedPath id 缺失时 execution blocked；
- target URL / entry context 缺失时 execution blocked；
- confirmed plan lookup 使用 existing events，不从 raw text 重建；
- 只有 learned_path_id + URL 都存在时才调用 replay service；
- started / completed / failed / blocked events 带有 audit fields；
- replay completed response 不声明 task verified；
- explicit `/replay <learned_path_id> <url>` 保持兼容；
- `/replay` while `awaiting_confirmation` 仍被 blocked；
- 不引入 autonomous、raw HTML、LLM、Task Path Planner re-planning 或 recovery
  imports。

## Evidence Plan

未来 implementation review 应记录：

- changed files；
- execution precondition examples；
- confirmed plan lookup evidence；
- replay invocation evidence；
- missing-context behavior；
- event payload examples；
- assistant message examples；
- explicit replay compatibility behavior；
- result verification non-goal evidence；
- test command output；
- `git diff --check` result。

11.1.6 文档初始化阶段只运行：

```bash
git diff --check
```

## Implementation Decision Closure

以下决策收口 11.1.6 第一版实现中会影响代码结构的 open questions。它们是
future implementation decisions；本文档不修改代码、schema、API endpoint 或 CLI
command。

### Execution trigger decision

11.1.6 第一版不得在 11.1.5 confirm 后自动执行 replay。

11.1.5 confirmation 只表示：

```text
consent recorded
ready for future execution
replay not executed
```

第一版 execution trigger 是：

```text
conversation status == plan_confirmed
+
user submits explicit execution intent through the existing dispatch surface
```

允许的 deterministic execution tokens：

```text
execute
run
start
执行
开始
```

Token 处理规则：

- exact match only；
- trim surrounding whitespace；
- 英文 token 做 ASCII lowercase；
- 不接 LLM classifier；
- 不做 fuzzy inference；
- 不新增 API endpoint；
- 不新增 CLI command。

`plan_confirmed` 下的其他 free text 不得触发 replay，除非后续包明确扩展 command
surface。

### Target URL / replay context decision

第一版只能从可审计的 confirmed plan / preview evidence 读取 replay context。

允许来源：

```text
latest plan_preview_proposed event payload
plan_confirmed event payload
future persisted execution context if already available
```

必需 execution context：

```text
selected learned_path_id
target_url or replay entry context
```

禁止来源：

```text
raw user text target_url inference
Task Path Planner re-run
LearnedPath retrieval re-run
raw HTML / browser page entry-point guessing
```

如果 confirmed evidence 中不存在 target URL 或 replay entry context，11.1.6 必须
blocked，而不是猜测。

### Missing context decision

如果缺少以下任一信息：

```text
confirmed plan
selected learned_path_id
target_url / replay entry context
```

第一版必须返回：

```text
execution_blocked
```

或等价 blocked semantics。

必需行为：

- 不猜测；
- 不执行 replay；
- 不调用 autonomous run；
- 不重新规划；
- 记录 blocked event；
- 追加 assistant message，说明缺少 execution context。

建议 assistant message 语义：

```text
The confirmed plan is not executable because required replay context is missing.
```

### State strategy decision

第一版可以新增 execution lifecycle statuses：

```text
executing
execution_finished
execution_failed
```

状态含义：

```text
execution_finished != task succeeded
execution_finished != business result verified
```

推荐 transitions：

```text
plan_confirmed -> executing
executing -> execution_finished
executing -> execution_failed
plan_confirmed -> plan_confirmed when execution is blocked
```

Blocked execution 第一版可以只记录 event。如果不引入 `execution_blocked` status，
session 应保持 `plan_confirmed`，并记录 `plan_execution_blocked`。

### Event semantics decision

第一版应使用或新增以下 event semantics：

```text
plan_execution_started
plan_execution_completed
plan_execution_failed
plan_execution_blocked
```

含义：

```text
plan_execution_completed only means replay invocation completed
plan_execution_completed does not mean task succeeded
plan_execution_completed does not mean result verified
plan_execution_completed does not mean artifact produced
```

Event payload 应包含：

```text
learned_path_id
target_url / replay entry context if available
route step id or route summary if available
replay run id / execution id if available
error summary if failed
no_result_verification: true
no_autonomous: true
```

Event payload 不得包含：

```text
raw HTML
screenshot payload
user/account/tenant fields
business success assertion
```

### Replay result boundary decision

11.1.6 只能记录 replay-level results：

```text
replay started
replay completed
replay failed
replay blocked
```

11.1.6 不得记录：

```text
task succeeded
business result verified
form submission confirmed
artifact produced
```

这些属于 future Result Verification and Task Result Reporter。

### Single-path execution decision

第一版只支持一个 selected LearnedPath。

如果 confirmed RoutePlan 包含多个 route steps 或多个 selected paths：

```text
execution_blocked / unsupported_multi_step_route
```

实现不得部分执行 multi-step route。Multi-step route execution 保持 future scope。

### Explicit replay compatibility decision

Confirmed-plan execution 和 explicit `/replay <learned_path_id> <url>` 是相关但
独立的入口。

要求：

- explicit `/replay` outside `awaiting_confirmation` 继续使用现有 explicit
  replay path；
- `/replay` while `awaiting_confirmation` 继续由 11.1.5 blocked；
- `plan_confirmed` 下的 execution intent 不得通过伪装成 slash `/replay`
  command 实现；
- confirmed-plan execution 可以复用 replay 的底层 deterministic capability，
  但 learned_path_id 和 target_url 必须来自 confirmed plan context。

### Out-of-scope decision

11.1.6 仍不做：

```text
result verification
Task Result Reporter
failure recovery
teaching mode
slot binding
form filling
autonomous run
hidden relearning
raw HTML planning
LLM planning
browser exploration
multi-step route execution
```

## Out of Scope

- 本轮文档阶段不写实现代码。
- 不修改 11.1.1 schemas。
- 不修改 11.1.2 retrieval implementation。
- 不修改 11.1.3 planner implementation。
- 不修改 11.1.4 preview implementation。
- 不修改 11.1.5 confirmation implementation。
- 不新增 API endpoint。
- 不新增 CLI command。
- 不调用 autonomous run。
- 不做 hidden relearning。
- 不读取 raw HTML。
- 不接入 LLM provider。
- 不做 real slot binding。
- 不做 form filling。
- 不做 result verification。
- 不实现 Task Result Reporter。
- 不做 recovery dialogue。
- 不做 teaching mode。
- 不做 browser exploration。
- 不创建 11.1.7 详情目录。

## Open Questions

- 最终 status enum 名称可以在实现时按现有 conversation schema 风格微调。
- 精确 replay service integration point 必须在 inspect 现有 replay code 后决定。
- 精确 replay run id / execution id 字段取决于现有 replay return shape。
