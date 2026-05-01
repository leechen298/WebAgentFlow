# 实施计划

状态：Draft only，不可直接外包执行。执行前需要确认目标 fixture 控件
和 scenario。

## 预期触及的模块

- `page_analyzer.py`：识别 tag / pill / custom toggle。
- `action_planner.py`：按 selection 语义选择目标控件。
- `users` fixture 与 spec：补 click-toggle scenario。
- 必要时补 supervisor observation 以表达 toggle 结果。

## 粗粒度步骤

1. 固定第一个目标控件和期望 query / DOM 变化。
2. 给 analyzer 增加 custom click-toggle 分类。
3. 给 planner 增加 selection → custom toggle 的匹配。
4. 补单测和 fixture 验证。

## 执行前需要确认

- 首个目标是否选 `users` 页面已有 tag filter。
- success signal 用 query param、DOM 文案，还是两者都用。

## 验证方向

- 单测覆盖目标 tag 命中、无匹配、误点保护。
- live verification 只能走 `verify-scenario` skill。
