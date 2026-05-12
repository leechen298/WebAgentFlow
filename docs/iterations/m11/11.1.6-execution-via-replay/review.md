# 审核与反思

本 review 文档用于后续 11.1.6 implementation review。当前仍是文档阶段，不写
PASS，不写测试数量。

## Scope Review Checklist

- [ ] 实现只执行 already confirmed plans。
- [ ] 实现不从 raw user text 重建 plan。
- [ ] 实现不调用 Task Path Planner 做 re-planning。
- [ ] 实现不调用 autonomous run。
- [ ] 实现不读取 raw HTML。
- [ ] 实现不做 hidden relearning。
- [ ] 实现不接入 LLM provider。
- [ ] 实现不做 slot binding、result verification、Task Result Reporter、
  recovery dialogue 或 teaching mode。
- [ ] 实现不新增 user / account / tenant fields。

## Execution Precondition Checklist

- [ ] Conversation 处于 confirmed-but-not-executed 语义。
- [ ] User consent 已通过 11.1.5 记录。
- [ ] Plan 尚未执行。
- [ ] Plan 未被 cancelled、rejected 或 superseded。
- [ ] Selected LearnedPath id 可用。
- [ ] Target URL 或 replay entry context 可用。
- [ ] Missing context 会 blocked，而不是 guessing。

## Confirmed Plan Lookup Checklist

- [ ] Confirmed plan 从可审计 conversation events 恢复。
- [ ] `plan_preview_proposed` evidence 用于 selected path / route summary。
- [ ] `plan_confirmed` evidence 用于 consent。
- [ ] 不使用 raw user text 重建 plan。
- [ ] 不再次调用 Task Path Planner。

## Replay Invocation Checklist

- [ ] 复用 existing deterministic replay service / explicit replay hook。
- [ ] 如果已有 service-level replay function，不引入 HTTP self-call。
- [ ] 只有显式 `learned_path_id + url` 或等价 confirmed entry context 存在时
  才调用 replay。
- [ ] 不引入 autonomous execution、hidden relearning、raw HTML planning、
  LLM、slot binding 或 invented actions。

## Missing Context Checklist

- [ ] Missing LearnedPath id 记录 execution-blocked 语义。
- [ ] Missing target URL / entry context 记录 execution-blocked 语义。
- [ ] Assistant message 说明 execution context 缺失。
- [ ] Context 不完整时不调用 replay handler。

## Conversation Event Checklist

- [ ] 记录 execution started event。
- [ ] replay invocation 完成时记录 execution completed event。
- [ ] replay invocation 失败时记录 execution failed event。
- [ ] preconditions 缺失时记录 execution blocked event。
- [ ] Payload 在可用时包含 learned_path_id 和 target URL / entry context。
- [ ] Payload 包含 no-autonomous marker。
- [ ] Payload 包含 no result verification marker。
- [ ] Payload 不包含 raw HTML、screenshots 或 user/account/tenant fields。

## State Transition Checklist

- [ ] Confirmed plan 只有在 preconditions 通过后才进入 executing 语义。
- [ ] Completion state 不暗示 result verification。
- [ ] Failure state 不尝试 recovery。
- [ ] 如果实现扩展 conversation state machine，state changes 记录一致。

## Assistant Message Checklist

- [ ] Execution-started response 表达 replay execution started。
- [ ] Execution-completed response 表达 result verification 尚未实现。
- [ ] Execution-failed response 表达未尝试 recovery。
- [ ] Execution-blocked response 表达 required context missing。
- [ ] 没有 response 声明 task success 或 business-result verification。

## Explicit Replay Compatibility Checklist

- [ ] 现有 `/replay <learned_path_id> <url>` command 仍可工作。
- [ ] `/replay` while `awaiting_confirmation` 仍由 11.1.5 blocked。
- [ ] Confirmed-plan execution 和 explicit replay 保持 separate entry paths。

## Result Verification Boundary Checklist

- [ ] Replay completed 不被报告为 task succeeded。
- [ ] 11.1.6 不发出 business result verified。
- [ ] 11.1.6 不发出 artifact produced。
- [ ] 不调用 Task Result Reporter。

## Regression Checklist

- [ ] Conversation orchestrator tests pass。
- [ ] 如触及 Conversation API，则 Conversation API tests pass。
- [ ] Explicit replay hook tests pass。
- [ ] 11.1.5 confirmation gate tests pass。
- [ ] 如触及 replay integration，则 replay service tests pass。
- [ ] `git diff --check` clean。

## Evidence Checklist

- [ ] Changed files 已列出。
- [ ] Execution precondition examples 已记录。
- [ ] Confirmed plan lookup evidence 已记录。
- [ ] Replay invocation evidence 已记录。
- [ ] Missing-context behavior 已记录。
- [ ] Event payload examples 已记录。
- [ ] Result verification non-goal evidence 已记录。
- [ ] Verification commands and results 已记录。

## Implementation Decision Closure

以下决策已为 11.1.6 第一版 future implementation 收口。它们仍是文档阶段决策，
直到代码和测试实现完成。

- [ ] Execution trigger decision：
  - 11.1.6 不得在 11.1.5 confirmation 后自动执行 replay。
  - Confirmation 只记录 consent / ready-for-execution 语义。
  - 第一版 execution trigger 是 `conversation status == plan_confirmed` 加
    用户通过现有 dispatch surface 输入明确 execution intent。
  - 允许的 execution tokens 仅限 exact match：
    `execute`、`run`、`start`、`执行`、`开始`。
  - 此 trigger 不引入 LLM classifier、fuzzy matching、新 API endpoint 或新
    CLI command。
- [ ] Target URL / replay context decision：
  - Replay context 必须来自可审计 confirmed plan / preview evidence。
  - 允许来源是 latest `plan_preview_proposed` event payload、`plan_confirmed`
    event payload，或已经存在的 future persisted execution context。
  - 必需 context 是 selected `learned_path_id` 加 `target_url` 或 replay entry
    context。
  - 实现不得从 raw user text 推断 target URL，不得 re-run retrieval，不得
    re-run Task Path Planner，不得从 raw HTML / browser page 猜 entry point。
- [ ] Missing context decision：
  - 缺 confirmed plan、selected LearnedPath 或 target URL / replay entry context
    时，execution blocked。
  - Blocked execution 记录 `execution_blocked` 或等价语义。
  - 不调用 replay，不调用 autonomous run，不尝试 re-planning。
- [ ] Execution state decision：
  - 第一版可以新增 `executing`、`execution_finished`、`execution_failed`
    statuses。
  - `execution_finished` 不表示 task succeeded 或 business result verified。
  - Blocked execution 可以只记录 event，并让 session 保持 `plan_confirmed`。
- [ ] Event semantics decision：
  - 第一版应使用或新增 `plan_execution_started`、
    `plan_execution_completed`、`plan_execution_failed`、
    `plan_execution_blocked`。
  - `plan_execution_completed` 只表示 replay invocation completed。
  - Event payload 包含 learned_path_id、target URL / replay context（如可用）、
    route summary（如可用）、replay run id / execution id（如可用）、failed 时的
    error summary、`no_result_verification: true`、`no_autonomous: true`。
  - Event payload 不包含 raw HTML、screenshot payload、identity / tenant
    fields 或 business success assertions。
- [ ] Replay result boundary decision：
  - 11.1.6 只记录 replay-level results：started、completed、failed、blocked。
  - 11.1.6 不得记录 task succeeded、business result verified、form submission
    confirmed 或 artifact produced。
- [ ] Single selected LearnedPath decision：
  - 第一版只支持 single selected LearnedPath。
  - Multi-step 或 multi-selected-path RoutePlans 返回 `execution_blocked` /
    `unsupported_multi_step_route`。
  - 不允许 partial multi-step execution。
- [ ] Explicit replay compatibility decision：
  - Confirmed-plan execution 和 explicit `/replay <learned_path_id> <url>` 是
    separate entry paths。
  - explicit `/replay` outside `awaiting_confirmation` 继续走 explicit replay
    path。
  - `/replay` while `awaiting_confirmation` 继续由 11.1.5 blocked。
  - `plan_confirmed` execution intent 不得通过伪装成 slash `/replay` command
    实现。
- [ ] Result verification boundary decision：
  - 11.1.6 不实现 result verification、Task Result Reporter、failure recovery、
    teaching mode、slot binding、form filling、autonomous run、hidden
    relearning、raw HTML planning、LLM planning、browser exploration 或
    multi-step route execution。

## Decisions to Confirm Before Implementation

- 最终 status enum 名称可以在实现时按现有 conversation schema 风格微调。
- 精确 replay service integration point 必须在 inspect 现有 replay code 后决定。
- 精确 replay run id / execution id 字段取决于现有 replay return shape。
