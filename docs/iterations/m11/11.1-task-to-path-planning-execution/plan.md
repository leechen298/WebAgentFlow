# 实施计划

## M11.1 总体设计

M11.1 在 M11.0 runtime conversation loop 之上建立第一个 L3 Actual Work
MVP。用户提交任务后，系统不再要求用户显式提供 LearnedPath id，而是通过
task-to-path planning 找到候选路径、绑定参数、请求确认、执行 replay，并
基于可验证信号汇报结果。

核心路径：

1. 用户通过 conversation surface 提交 task input。
2. 系统生成 task intent record。
3. LearnedPath retrieval / ranking 返回候选路径。
4. Slot binding 将任务参数绑定到可替换 action values。
5. Task Path Planner / 任务路径规划器（legacy: Agent D） 在候选、绑定、证据边界内生成 route plan。
6. Confirmation / consent gate 在执行前要求用户确认不确定或有风险的计划。
7. Execution 通过 M10 replay / M11.0 replay hook 执行。
8. Result verification 读取 replay result、postconditions、artifact status
   和 final-state signals。
9. Task Result Reporter / 任务结果汇报器（legacy: Agent E） 基于证据汇报结果，不脑补成功。

## 执行包拆分

- 11.1.1 Task planning domain contract。
- 11.1.2 LearnedPath retrieval and ranking。
- 11.1.3 Task Path Planner MVP。
- 11.1.4 Task Planning Dispatch Preview。
- Future Slot binding contract and deterministic binding MVP。
- Future Plan confirmation and consent gate。
- Future Execution via replay。
- Future Result verification and Task Result Reporter / 任务结果汇报器 reporting。
- Future Task-to-path tests and evidence。

## Task Path Planner / 任务路径规划器（legacy: Agent D） 输入 / 输出边界

Task Path Planner / 任务路径规划器（legacy: Agent D） 只在规划边界工作。

输入：

- user task / TaskIntent。
- LearnedPathCandidate 列表。
- SlotBindingProposal 列表。
- negative / drift / replay evidence summary。
- risk / confirmation policy hints。

输出：

- RoutePlan。
- RouteStep 列表。
- ConfirmationRequirement。
- RiskHint / ConsentRequirement。
- uncertainty。

Task Path Planner / 任务路径规划器（legacy: Agent D） 不读 raw HTML，不逐步控制浏览器，不执行 replay，不调用
autonomous run。

## Task Result Reporter / 任务结果汇报器（legacy: Agent E） 输入 / 输出边界

Task Result Reporter / 任务结果汇报器（legacy: Agent E） 只在结果汇报边界工作。

输入：

- TaskExecutionResult。
- replay result summary。
- postcondition results。
- artifact status。
- final URL / title / DOM signals。
- uncertainty flags。

输出：

- 用户可读结果 summary。
- structured status：`succeeded` / `failed` / `uncertain` / `needs_review`。
- evidence references。
- warnings / next action suggestions。

Task Result Reporter / 任务结果汇报器（legacy: Agent E） 不得脑补成功；证据不足时必须返回 `uncertain` 或 `needs_review`。

## LearnedPath retrieval 输入 / 输出

输入：

- TaskIntent。
- target_page_hint / scenario_hint。
- available LearnedPath catalog metadata。
- trust / hit_count / drift evidence / negative evidence。

输出：

- LearnedPathCandidate 列表。
- match_reasons。
- warnings。
- evidence summary。

Retrieval / ranking 不调用 Task Path Planner / 任务路径规划器（legacy: Agent D），不执行 replay。

## Task Planning Dispatch Preview 位置

Task Planning Dispatch Preview 位于 conversation runtime 和 task planning
services 之间。它把 ordinary user task 转成 preview：

- 构造最小 `TaskIntent`。
- 调用 LearnedPath retrieval / ranking。
- 调用 Task Path Planner。
- 将 planning preview 写回 conversation message / event。
- 停在 confirmation-pending / unable-to-plan 语义，不执行 replay。

该阶段不做 Slot Binding、不做 confirmation gate、不做 execution，也不改变显式
`/replay <learned_path_id> <url>` command 的行为。

## Slot binding 输入 / 输出

输入：

- TaskIntent。
- LearnedPathCandidate actions / replaceable values。
- user-provided task terms。

输出：

- SlotBindingProposal。
- confidence。
- requires_confirmation。
- binding warnings。

Slot Binding remains future scope and is not assigned a package number in the
current M11.1 plan.

## Confirmation / consent gate 位置

Confirmation / consent gate 位于 route plan 生成之后、execution 之前。

初期使用 deterministic policy + user confirmation，不新增 Risk Agent。
需要确认的类型包括 ambiguous、risky、destructive、external-send、
bulk-modification、permission-modification 和用户自定义敏感操作。

## Execution through replay 位置

Execution 只能执行已确认的 route plan，并通过已有 deterministic replay /
later explicit execution service 调用。

不通过 autonomous exploration 执行，不做 hidden relearning，不让 LLM 逐步
控制浏览器。

## Result verification 位置

Result verification 位于 replay execution 之后、Task Result Reporter / 任务结果汇报器（legacy: Agent E） reporting 之前。

验证输入包括 replay result、postcondition signals、artifact status、final
URL / title / DOM signals。无法验证时返回 `uncertain` / `needs_review`。

## Testing strategy

- 11.1.1 优先覆盖 schema / enum / contract。
- 后续包优先 deterministic tests。
- LLM provider 不作为默认测试依赖。
- 不调用 autonomous run。
- E2E 放到 11.1.8。

## 验证

当前文档阶段只运行：

```bash
git diff --check
```
