# 意图（Intent）

状态：implementation complete

## 目标

在 `apps/product-test-site` 新增一个产品级列表测试页：

```text
/items
```

页面只做 P0 必需能力：

```text
输入项目名称
-> 点击新增项目
-> 列表出现该项目
-> 操作状态显示新增结果
```

这个页面是后续 working runtime 窄闭环的稳定测试场：

```text
学习新增项目 A
-> 执行新增项目 B
-> 在列表中看到 B
-> Reporter 保守报告结果
```

## 背景

当前 `apps/product-test-site` 只有 `/workspace-login` 和 `/workspace-home`。
登录页适合验证账号、密码、跳转和登录态，但不适合作为第一条 working runtime
happy path，因为它会把账号密码、cookie、重定向和权限等因素混到学习 / 执行 /
验证链路里。

列表页更适合 P0：

- 新增项目后能在页面上留下明确 DOM 结果。
- 后续 ExecutionEvidence 可以限定在 `[data-testid='item-list']` 内查找目标文本。
- 后续参数化 replay 可以明确证明“学习 A 后执行 B”没有复读录制值 A。

## 成功标准

- `/items` route 可访问。
- 页面使用前端本地状态，不依赖后端 API。
- 初始列表包含稳定示例数据。
- 输入唯一项目名后点击新增，列表中出现该项目。
- 新增成功后 `operation-status` 显示明确状态。
- 空名称不会新增空行，并给出页面内状态反馈。
- 页面提供稳定 `data-testid`，满足后续 learning / replay / evidence 定位。
- `/workspace-login`、`/workspace-home` 和 `/` redirect 不被破坏。

## 非目标

- 不接 `wagent chat`。
- 不实现 `item_name` slot extraction。
- 不实现 `value_slot`、`slot_overrides` 或参数化 replay。
- 不采集 `ExecutionEvidence`。
- 不接 `TaskResultReporter`。
- 不做 `pending_choice`、`active_task`、Failure Recovery 或 TaskPathPlanner chat 接入。
- 不做搜索、编辑、删除项目。
- 不接 mock backend，不写数据库，不新增 API。
- 不触发 `verify-scenario` 或 autonomous-run。

## 用户价值

完成本包后，后续迭代有一个足够简单、可观察、可重复的网页操作目标。它让
WebAgentFlow 的 P0 工作重点从“登录页是否碰巧成功”转成“系统是否真的学会并执行
一个可参数化网页操作”。
