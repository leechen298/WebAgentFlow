# 意图（Intent）

状态：ready_for_implementation（design review passed，未开始执行）

## 目标

用 `wagent chat` 真实产品入口跑通并记录 `/items` P0 闭环：

```text
学习新增项目 A
-> 执行新增项目 B
-> replay 实际填入 B
-> item-list 出现 B
-> TaskResultReporter 输出 verified
```

## 动机

11.3.5.3 - 11.3.5.5 已分别完成页面基座、参数化 replay 和 evidence / reporter
adapter。它们的 targeted tests 可以证明单个模块行为，但还不能证明用户通过
`wagent chat` 真的完成了第一条 working runtime 闭环。

本包的作用是把模块级通过收口成产品级证据：用户语言、会话状态、学习、replay、DOM
evidence、Reporter outcome 和最终回复必须在同一条会话里可追溯。

## 边界 / 非目标

- 不新增产品功能，除非闭环执行暴露阻断性小缺口且可以最小修复。
- 不修改 `/items` 页面功能。
- 不扩展到搜索 / 编辑 / 删除。
- 不接 TaskPathPlanner。
- 不实现 `pending_choice`。
- 不实现 `active_task` / RuntimeLedger。
- 不实现 Failure Recovery。
- 不调用 `verify-scenario` 或 autonomous run。
- 不把 direct replay API 调用写成本包闭环通过证据；闭环必须从 `wagent chat` 进入。
- 不把人工观察、静态代码审查或单元测试结果冒充为 live closed-loop evidence。

## 成功标准

- `wagent chat` 新会话可记录 session id。
- 用户给出 `/items` URL 后，系统能进入学习新增项目流程。
- 学习输入使用唯一 `测试项目A-${timestamp}`。
- LearnedPath actions 中存在 fill action，且有 `value_slot=item_name`。
- 执行输入使用唯一 `测试项目B-${timestamp}`。
- replay step log / event / history 能证明 fill action 的 effective value 是 B，不是 A。
- execution evidence 中存在：
  - `kind=dom_text_present`
  - `target=测试项目B-${timestamp}`
  - `status=verified`
  - `selector=[data-testid='item-list']` 对应区域内能看到 B
- TaskResultReporter outcome 是 `verified`。
- 用户可见回复说明在列表中看到了 B，并确认新增成功。
- `review.md` 和
  `docs/testing/results/m11-11.3.5.6-items-closed-loop-<YYYY-MM-DD>.md`
  记录命令、session id、关键日志、事件摘要、验证结果和未运行项。
