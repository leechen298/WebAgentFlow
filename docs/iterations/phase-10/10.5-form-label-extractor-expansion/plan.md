# 实施计划

状态：Draft only，不可直接外包执行。执行前要确认本轮具体覆盖哪些
UI 库。

## 候选范围

- Element Plus：`el-form-item`
- Naive UI：`n-form-item`
- Arco Design：`arco-form-item`
- TDesign：`t-form-item`
- Quasar：`q-field__label`
- MUI v5：`MuiFormControl-root` + `MuiInputLabel-root`

## 粗粒度步骤

1. 读取当前 `form_label_extractor` 结构和测试。
2. 按“一个 handler + 一个最小 HTML case”的方式补覆盖。
3. 保持 dispatcher 简单：先规则命中，命中即返回。
4. 根据需要补 fixture，不把本轮和 popup / click-toggle 混在一起。

## 执行前需要确认

- 本轮一次接入全部候选，还是拆成 2-3 个小包。
- Quasar / MUI 结构差异是否需要单独任务。

## 验证方向

- 单测为主，不需要 live autonomous run。
- 若补 fixture scenario，再按 AGENTS.md 使用 `verify-scenario`。
