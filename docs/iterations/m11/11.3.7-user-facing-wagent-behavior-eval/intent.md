# 意图（Intent）

状态：proposed

## 目标

定义并后续实现一套用户视角 WAgent 行为 eval，验证 WAgent 面对普通用户输入时，能否从
页面学习状态、用户意图、信息完整度和执行证据出发，稳妥地引导学习或执行，而不是只证明
底层 replay 零件能跑通。

## 动机

11.3.6 runtime eval program 已经证明一批受控 runtime 能力：已学路径参数化复用、
evidence reporting、pending choice、planner-backed choice 和 basic recovery menu。
但这些结果不能被解读为完整产品能力验收，因为它们没有覆盖普通用户入口行为：

- 用户只给页面 URL 时，WAgent 是否能查学习记录并给出下一步；
- 用户明确要执行时，WAgent 是否能区分已学 / 未学；
- 用户明确要学习时，WAgent 是否进入学习流程而不是执行；
- 用户说得模糊或乱说时，WAgent 是否避免误执行；
- 用户补充信息时，WAgent 是否能续上原任务；
- 多个已学操作时，WAgent 是否能用 A/B/C 选择而不泄露内部 id；
- 执行失败或 evidence 不足时，WAgent 是否给出安全恢复出口。

同时，新的 eval 必须防止针对测试页定制实现。测试页面链接、route、页面专有文案、
按钮名、字段名、DOM test id 和 fixture 业务内容只能作为 eval 数据存在，不能写入功能代码
或产品提示词，否则会污染整体产品泛化能力。

## 边界 / 非目标

- 不验证 L1 “自动学习页面所有操作”的完整能力；第一版只验证受控用户入口行为。
- 不让 WAgent 在任意真实页面上全自动尝试所有按钮；学习新操作必须受用户确认约束。
- 不在功能代码或产品 prompt 中硬编码测试页面链接、路径、页面文案、按钮名、字段名、
  DOM test id 或测试业务内容。
- 不默认运行 `verify-scenario`、autonomous run、Console UI smoke 或 product-driven browser
  execution；除非用户后续明确要求 live run。
- 不把 eval-only setup、fixture seed 或测试数据注入冒充真实产品能力。
- 不把登录页作为第一批行为验收目标。

## 成功标准

- 11.3.6 的结论口径被限定为 “runtime execution capabilities pass with caveats”，不再被
  表述为完整 WAgent 产品能力通过。
- 11.3.7 有清晰的用户视角 case：URL-only known、URL-only unknown、execute-known、
  execute-unknown、vague-input。
- 每个 case 都定义 learned / unlearned 状态、用户输入、预期用户可见回复、内部安全边界和
  evidence gate。
- 后续实现必须包含 forbidden-token hard gate，证明测试页面细节没有进入功能代码或产品 prompt。
- 后续实现只通过 Conversation API / project eval runner / 明确批准的产品 UI surface 产生证据，
  不调用 autonomous-run endpoints，不把 Codex 自然语言判断当作 pass / fail。
