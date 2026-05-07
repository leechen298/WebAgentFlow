# 10.3 · Popup-based control support

## 执行前必读

本包当前是 draft only，不能直接施工。后续修订为可
执行状态前，请先阅读 `AGENTS.md`、`docs/product-model.md`、
`docs/iterations/m10/m10-plan.md`，再读本目录的 `intent.md`
和 `plan.md`。

状态：Draft only，不可直接施工。开工前必须重新核对当前
`page_analyzer`、`action_planner`、validation-site users fixture 和
`10.2` 结果。

## 目标

支持需要“先点击触发器，再在弹层内操作”的控件形态，例如 Cascader、
DatePicker、RangePicker、MonthPicker、表头筛选 / 排序。

## 动机

- `users` fixture 已经包含多类弹层控件，但当前 spec 只覆盖普通文本
  和部分 inline 控件。
- 实际业务页面大量使用组件库弹层控件；如果 analyzer / planner 不能
  表达两段式交互，自主探索会误点或漏填关键筛选项。

## 边界（本轮不做）

- 不处理 Tag / pill 这类点击即切换的伪控件；那是 `10.4`。
- 不重写整个 planner，只扩展两段式 popup 操作表达。
- 不把 popup 控件降级伪装成普通 text input。

## 成功标准

1. Analyzer 能识别 popup trigger 和弹层内候选操作面。
2. Planner 能输出 open popup → choose / type / confirm 的步骤。
3. `users` fixture 至少一个 popup scenario 可被验证。
4. 已有 text input / native radio 场景不回退。
