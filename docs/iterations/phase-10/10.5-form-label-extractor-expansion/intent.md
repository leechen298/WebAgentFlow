# 10.5 · Form-label extractor coverage expansion

状态：Draft only，不可直接外包执行。开工前必须重新核对当前
`form_label_extractor` 已支持的 handler 和测试覆盖。

## 目标

在现有 Ant Design + HTML5 `<label for>` 基础上，扩展常见 UI 库的
表单 label 提取能力。

## 动机

- Analyzer 的 semantic role 质量依赖 label 提取。
- 不同 Vue / React UI 库的 Form.Item class 前缀不同，但多数仍是
  稳定结构，可用规则 handler 覆盖，不需要 LLM 推断。

## 边界（本轮不做）

- 不改 action planner。
- 不为未知页面写业务特例。
- 不引入 LLM label 推断。

## 成功标准

1. 至少补一批明确 UI 库 handler，并有最小 HTML 单测。
2. 既有 Ant Design / HTML5 label 测试不回退。
3. dispatcher 仍按规则命中，不做概率判断。
