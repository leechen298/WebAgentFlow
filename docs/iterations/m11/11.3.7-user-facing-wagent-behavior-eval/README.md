# 11.3.7 · User-facing WAgent Behavior Eval

状态：proposed（docs drafted，implementation pending）
里程碑：M11
类型：code
父迭代：[`11.3.5-customer-facing-agent-router-skill-runtime`](../11.3.5-customer-facing-agent-router-skill-runtime/)
前置验收：[`11.3.6-wagent-runtime-eval-program`](../11.3.6-wagent-runtime-eval-program/)

## 迭代类型

- [ ] 文档型迭代
- [x] 代码型迭代
- [ ] 混合型迭代

本包是 11.3 working runtime 的下一阶段验收定义。它不再重复验证
`value_slot`、`slot_overrides`、Reporter adapter、pending choice private map
这些底层零件，而是验证普通用户从空白或半空白状态进入时，WAgent 是否能自己判断：

- 这个页面是否已经学过；
- 用户是要学习、执行、补充信息，还是只是模糊表达；
- 信息是否足够，不足时如何追问；
- 学过时如何列出可执行操作并匹配路径；
- 没学过时如何引导学习；
- 执行后是否基于 evidence 回复；
- 失败或不确定时是否给出安全出口；
- 用户乱说时是否保持不执行。

## 与 11.3.6 的关系

11.3.6 已关闭为 `pass_with_caveats`，但它通过的是 runtime 受控执行能力：

- 已学路径的参数化复用；
- DOM evidence reporting；
- pending choice；
- planner-backed choice 分支；
- basic recovery menu；
- private payload redaction。

11.3.6 不证明页面级自动操作学习能力，也不证明 WAgent 面对任意新页面和任意用户任务时
都能自动发现、学习、匹配和执行。11.3.7 专门补这层用户视角产品行为验收。

## 本包做什么

- 定义用户入口行为 eval：URL-only、execute-known、execute-unknown、learn-explicit、
  vague-input。
- 定义 learned / unlearned 两种页面状态下的预期对话分支。
- 定义多候选 choice、pending continuation、failure recovery 的用户视角验收目标。
- 定义页面能力学习 eval 的后续扩展目标：能力发现、多操作学习、LearnedPath catalog
  生成、自然语言复用执行。
- 定义反作弊 / 泛化硬 gate：测试页面链接及其相关页面内容不得进入功能代码或产品提示词。
- 约束所有 live / CLI / UI 证据必须通过可审计产品入口或 project eval runner 产生。

## 本包不做

- 不把 11.3.6 的 runtime eval pass 改写成完整产品能力 pass。
- 不实现 L1 Page Understanding Agent，也不让 LLM 逐步控制浏览器。
- 不默认执行 `verify-scenario`、autonomous run 或 Console UI smoke。
- 不在功能代码或产品 prompt 中写入测试页面 URL、route、页面文案、测试按钮名、
  测试字段名、DOM test id 或 fixture 业务内容。
- 不把 eval-only candidate binding 冒充真实页面多操作能力。
- 不碰登录页作为第一批验收目标。

## 迭代文档

- `intent.md` - 用户视角验收目标、动机、边界和成功标准。
- `contract.md` - page-entry、learned / unlearned、intent handling、anti-hardcoding
  和 evidence 边界契约。
- `technical-design.md` - future eval runner / spec / hard gate 的设计，不包含本轮代码实现。
- `test-plan.md` - 第一批和后续扩展 case、反作弊扫描、live run 边界。
- `plan.md` - 后续实现步骤和验证入口。
- `review.md` - 本次文档生成、用户反馈和后续评审记录。

## 当前状态

本包当前只完成文档定义，尚未实现 runner，也未执行任何 CLI / UI / live eval。
后续进入实现前必须先完成 design review。实现阶段必须先建立测试页面细节的 forbidden-token
清单和代码 / prompt 扫描 gate，再实现用户行为场景本身。
