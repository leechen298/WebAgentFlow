# 实施计划

状态：Draft only，不可直接外包执行。执行前需要把具体首个 popup
scenario 选定，并核对当前 fixture DOM。

## 预期触及的模块

- `page_analyzer.py`：识别 trigger 与 popup surface。
- `action_planner.py`：表达两段式操作。
- `users` fixture 与 `users.assertions.json`：补第一个 popup scenario。
- Supervisor observation / scorecard：仅在现有观察项无法表达时补充。

## 粗粒度步骤

1. 选择第一个目标控件，建议从 DatePicker 或 Cascader 二选一。
2. 固化 fixture scenario 和 assertions，明确成功信号。
3. 扩展 analyzer 输出：trigger、popup surface、候选项、确认按钮。
4. 扩展 planner：生成 open popup 和 popup 内动作。
5. 增加服务单测和 fixture 验证。

## 执行前需要确认

- 首个 popup 控件选 DatePicker、Cascader 还是表头筛选。
- popup action 是否进入现有 action schema，还是新增专用结构。

## 验证方向

- 不触发非 skill 的 autonomous-run。
- 如跑 live verification，按 AGENTS.md 原样记录 `pass_gate.status`、
  Supervisor verdict、5 项 scorecard 和 `run_id`。
