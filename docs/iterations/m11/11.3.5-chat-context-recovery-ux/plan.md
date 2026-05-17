# 实施计划（Plan）

状态：proposed（docs generated, implementation not started）

## 阶段 1：文档和状态

- 新增本迭代七件套。
- 在 M11 README / m11-plan 登记 11.3.5。
- 在 product model / roadmap 中保持责任边界一致。

## 阶段 2：后续实现建议

1. 增加 `pending_target` session metadata helpers。
2. 扩展 Conversation Intake context。
3. 修改 ChatRuntime：
   - 裸 URL 保存 pending target。
   - 短句学习继承 pending target。
   - no-path 保存 recovery context 并引导学习。
4. 修改 CLI progress：
   - 模糊输入显示中性 loading。
   - 明确学习 / 执行才显示具体动作。
5. 补 Conversation History events。
6. 补 API / CLI / Console tests。

## 验证

文档阶段：

```bash
git diff --check
```

实现阶段按 `test-plan.md` 逐项执行。
