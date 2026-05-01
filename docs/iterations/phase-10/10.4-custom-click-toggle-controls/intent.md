# 10.4 · Custom click-toggle controls

状态：Draft only，不可直接外包执行。开工前必须重新核对 `users`
fixture 中 Tag / pill 类控件的实际 DOM 与当前 analyzer 输出。

## 目标

支持非原生 form input 的点击切换控件，例如 Tag-as-filter、pill、
自定义 `<span>` / `<div>` 选项。

## 动机

- 真实列表页经常用 tag / pill 表示筛选条件，而不是 radio /
  checkbox。
- 这类控件不弹 popup，交互面本身就是触发器，不能和 `10.3` 的两段式
  popup 混成同一种模型。

## 边界（本轮不做）

- 不处理弹层控件。
- 不做跨页面模式归纳。
- 不靠文本硬编码某一个 tag；应抽象为点击切换控件。

## 成功标准

1. Analyzer 能把目标 tag / pill 归类为可点击切换控件。
2. Planner 能根据 selection 语义选择正确控件。
3. `users` fixture 至少一个 click-toggle scenario 可验证。
4. 不影响 native radio / checkbox 既有路径。
