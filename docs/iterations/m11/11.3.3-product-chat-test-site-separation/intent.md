# 意图（Intent）

状态：proposed

## 目标

拆分工程验证站和产品级聊天验收站：保留 `validation-site` 作为 deterministic
工程回归靶场，新增独立 `product-test-site` 作为普通用户 `wagent chat`
产品路径验收靶场。

## 动机

当前 `validation-site` 对工程回归非常有价值，因为它提供：

- `*.assertions.json`
- fixed `spec_id`
- fixed `scenario`
- fixed inputs
- pass_gate / scorecard
- `verify-scenario`

但产品级 `wagent chat` 验收要证明的是另一件事：

```text
用户通过自然语言提供页面地址和必要输入
-> WebAgentFlow 观察页面并学习操作
-> 系统沉淀 LearnedPath
-> 用户用自然语言触发执行
```

如果产品级验收仍依赖 `spec_id=login`、`scenario=valid_credentials`、
`login.assertions.json` 或固定测试 oracle，就无法证明普通用户路径真实成立。

## 边界 / 非目标

- 不删除、不弱化、不重构 `apps/validation-site`。
- 不迁移 `11.2.4.2-single-page-basic-business-pages` 到 11.3；它继续属于 M11.2
  runtime observation fixture 体系。
- 不覆盖、不重命名、不回收 `11.3.2-chat-history-debug-console`。
- 本轮不实现 `apps/product-test-site`，只生成文档包。
- 本轮不实现真实业务系统接入、复杂多页面工作流、M12 recovery、用户接管或
  LLM 复杂意图理解。

## 成功标准

- 存在完整 11.3.3 七件套文档包。
- M11 README / m11-plan 记录 11.3.3，且不改变 11.3.2 编号。
- 用户指南说明 `validation-site` 与未来 `product-test-site` 的测试边界，且不把
  product-test-site 写成当前已可用。
- contract / technical design / test plan 明确：产品级 chat learning 不读
  `validation-site/specs/*.assertions.json`，不传 `spec_id / scenario`，不从
  assertions 取输入。
- 文档阶段 `git diff --check` 通过。
