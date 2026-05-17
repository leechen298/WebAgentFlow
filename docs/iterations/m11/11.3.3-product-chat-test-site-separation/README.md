# 11.3.3 · Product-Level Chat Test Site Separation

状态：ready_for_implementation（docs review passed, implementation not started）
里程碑：M11
类型：code

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

混合型迭代按代码型迭代门禁处理。

## 迭代定位

11.3.3 定义一个独立的 product-test-site，用于产品级 `wagent chat`
人工验收。它和 `apps/validation-site` 的工程验证靶场分离，避免
chat 产品路径被 validation specs、fixed scenario 或 assertion oracle 污染。

文档包已生成并通过审核；当前切到待开发状态。实现阶段尚未开始。

## 迭代文档

- `intent.md` - 目标、动机、边界、成功标准。
- `contract.md` - validation-site / product-test-site 边界、产品级 chat learning 契约。
- `technical-design.md` - 新站点结构、monorepo 集成、chat learning 去 spec 依赖设计。
- `test-plan.md` - 文档阶段检查、后续实现阶段 build / smoke / chat 验收矩阵。
- `plan.md` - 后续实现步骤、验证入口和 review checklist。
- `review.md` - 评审记录、用户反馈、未运行项和 acceptance blockers。

## 代码型迭代门禁

- [x] `intent.md` 已存在。
- [x] `contract.md` 已存在。
- [x] `technical-design.md` 已存在。
- [x] 技术设计在实现前已经审核。
- [x] 技术设计包含明确的 contract alignment。
- [x] `test-plan.md` 已存在并与技术设计的 Test Matrix 一致。
- [x] `plan.md` 与 contract / technical design 一致。
- [x] `review.md` 已记录文档阶段边界和 acceptance blockers。

## 当前状态

11.3.3 现在是待开发代码型迭代：文档、contract、technical design、test plan
和 implementation plan 已就绪；下一步可以进入 product-test-site 与 product-level
learning 的代码实现。当前仍不得标记为 implementation complete 或 accepted。

当前 `validation-site` 继续作为工程验证靶场，保留 specs / assertions /
pass_gate / scorecard / `verify-scenario`。它不迁移到 11.3。

当前 `11.3.2-chat-history-debug-console` 已存在，本包使用 11.3.3 编号，
不覆盖、不重命名、不回收 11.3.2。

后续实现阶段应新增 `apps/product-test-site`，默认端口 `5176`，并改造
`wagent chat` 产品级学习路径，使其从用户自然语言读取 URL 和必要输入，
而不是读取 `apps/validation-site/specs/*.assertions.json`。
实现完成后，根目录 `pnpm run dev` 必须同时启动 product-test-site，普通用户不需要
为了产品级验收额外运行第二套站点命令。
产品级路径还必须只学习和操作用户输入的目标站点；未学习过的站点或页面必须给出
普通用户能理解的反馈，而不是跨站点命中历史 LearnedPath。
