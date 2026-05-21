# 意图（Intent）

状态：ready_for_implementation（design review passed，未开始实现）

## 背景

11.3.5 working runtime 的 P0 闭环不是“replay 调用成功就算成功”。对于用户来说，
“帮我新增项目，名称叫测试项目B”是否完成，必须看页面结果：列表里是否真的出现
`测试项目B`。

当前 `TaskResultReporter` 已存在，并且 outcome 使用：

```text
verified
failed
uncertain
needs_review
blocked
```

但当前 Reporter 是保守的：没有明确 postcondition evidence 时不会轻易输出
`verified`。本包要补的正是这段中间层：

```text
replay succeeded
+ runtime stop 前采集页面 DOM evidence
+ Reporter 能读到 structured postcondition evidence
=> verified
```

如果只把 evidence 记录到事件 payload，却没有让
`TaskResultReporter._check_postconditions()` 能读取，P0 happy path 仍会停在
`uncertain`，不能算闭环打通。

## 用户价值

用户需要的是“WebAgentFlow 在网页上干了活，并且能说明为什么判断成功”。本包让
系统从：

```text
我执行了 replay。
```

升级到：

```text
执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。
```

同时保留保守性：

```text
操作已经执行，但我还没有拿到足够页面证据确认结果。
```

## 本轮目标

本轮目标是打通 `/items` 新增项目的最小结果证据链：

```text
1. Runtime 构造 evidence target：
   kind=dom_text_present
   text=slot_overrides.item_name
   source_slot=item_name
   selector=[data-testid='item-list']

2. Replay 执行所有 actions。

3. 在 runtime.stop() 前检查 selector 区域内是否出现 target text。

4. ReplayResult 带出 execution_evidence。

5. ConversationReplaySummary 带出 execution_evidence。

6. Reporter Adapter 把 execution_evidence 放到 reporter 可读的 structured
   postcondition evidence 位置。

7. TaskResultReporter 输出：
   - verified：replay succeeded + drift none + no error + dom_text_present verified
   - uncertain：replay succeeded 但无 useful evidence
   - needs_review：replay succeeded 但 target missing
   - failed：replay failed / runtime error
   - blocked：candidate missing / drift blocking / unsupported
```

## 成功标准

### P0 成功路径

输入：

```text
帮我新增项目，名称叫测试项目B-${timestamp}
```

执行已参数化 LearnedPath 后：

```text
ReplayResult.execution_evidence 包含：
kind = dom_text_present
target = 测试项目B-${timestamp}
status = verified
confidence >= 0.9

TaskResultReporter outcome = verified
user response 说明列表中看到了该项目名
```

### 保守路径

如果 replay succeeded 但没有 evidence：

```text
outcome = uncertain
不得说新增成功
```

如果 target text 未出现：

```text
outcome = needs_review
不得说新增成功
```

如果 replay failed / drifted：

```text
outcome = failed 或 blocked
不得编造页面证据
```

## 范围

本包允许修改：

- `apps/api/app/schemas/learned_path_replay.py`
- `apps/api/app/schemas/conversation.py`
- `apps/api/app/services/learning/learned_path_replay.py`
- `apps/api/app/services/conversation/replay_hook.py`
- `apps/api/app/services/conversation/chat_runtime.py`
- `apps/api/app/services/task_planning/result_reporter.py`
- 对应 targeted tests

如果实现需要新增小型 helper module，必须保持内部 adapter 定位，不得变成 Router
可推荐 Application Skill。

## 非目标

- 不实现复杂 evidence 类型；P0 只做 `dom_text_present` 和 `unknown`。
- 不把 Reporter outcome 改成 `success / partial_success`。
- 不做 Failure Recovery 菜单。
- 不做 TaskPathPlanner。
- 不做 `pending_choice`。
- 不做 `active_task`。
- 不扩大到搜索 / 编辑 / 删除项目。
- 不调用 LLM 判断页面是否成功。
- 不读取 raw HTML 交给 LLM。
- 不运行 autonomous exploration。

## 与前后迭代关系

- 依赖 11.3.5.3：`/items` 页面必须存在，并提供 `[data-testid='item-list']`。
- 依赖 11.3.5.4：replay 必须实际填入执行阶段的 B，而不是学习阶段的 A。
- 输出给 11.3.5.6：提供闭环测试所需的 evidence、Reporter outcome 和用户可见回复。
