# WebAgentFlow 迭代开发 Agent 工作流

状态：active

本文是 WebAgentFlow 迭代开发工作流的仓库级备份与同步源。Claude Code、Kimi Code、Codex 等本机 Skill 应与本文保持一致；各工具的本机 Skill 可以保留平台特有 metadata，但核心流程和门禁不得漂移。

仓库文档是权威事实来源；Agent 工作流只定义执行顺序和证据要求。

## 适用场景

当 AI 编码 Agent 处理 WebAgentFlow 的文档型、代码型或混合型迭代时，使用本工作流：

- 文档治理、roadmap、product model、scope、方案讨论；
- 运行时代码、schema、API、service、UI、CLI、测试、migration 或 fixture；
- 按已有迭代包实现；
- 按已有 `test-plan.md` 自测并写回 `review.md`；
- 生成或更新迭代文档（仅当用户明确要求该 Agent 承担设计 / 计划职责）。

## 角色边界

不同 Agent 可以承担不同角色，但必须明确当前角色：

- 设计型 Agent：在用户明确要求时，可以生成或更新完整迭代文档包：
  `README.md`、`intent.md`、`contract.md`、`technical-design.md`、`test-plan.md`、
  `plan.md`、`review.md`。
- 执行型 Agent：按已有文档实现和自测，不得临时重写需求、技术设计或测试计划。
- 评审型 Agent：只做 review / inspection，不得把静态推理写成 tested。

当已有迭代包存在时，所有 Agent 都必须先按既有文档执行。若发现文档缺失、过期、互相冲突或无法执行，先说明问题，再按用户指示更新文档或停止等待审核。

## 两阶段规则

### 生成开发文档阶段

当用户要求 Agent 为代码型或混合型迭代生成开发文档时，必须按 `docs/iterations/templates/`
生成完整迭代文档包：

- `README.md`
- `intent.md`
- `contract.md`
- `technical-design.md`
- `test-plan.md`
- `plan.md`
- `review.md`

不能只生成 `intent.md` + `plan.md`，也不能省略 `technical-design.md` 或 `test-plan.md` 后把
任务交给实现 Agent。文档型迭代只有在不准备后续代码实现时，才可以省略
`technical-design.md` 和 `test-plan.md`；但只要改变流程规则、里程碑语义、Agent 边界、
证据语义、迭代模板、概念、状态、字段或产品边界，仍必须包含 `contract.md`。

### 代码开发阶段

当用户要求 Agent 开发代码时，必须先读取当前迭代包里的 `intent.md`、`contract.md`、
已审核的 `technical-design.md`、`test-plan.md`、`plan.md` 和 `review.md`，然后按这些文档
实现和自测。不得绕过、重新解释或静默替换这些文档。

如果实现过程中发现文档缺失、设计问题或测试计划无法执行，先停止实现，更新对应迭代文档
并经过审核，再继续开发。

## 核心顺序

如果用户给了已有迭代包，或仓库里已经存在相关迭代目录，先按顺序读取：

1. `README.md`
2. `intent.md`
3. `contract.md`
4. `technical-design.md`（代码型 / 混合型迭代）
5. `test-plan.md`（存在时）
6. `plan.md`
7. `review.md`（了解已发生的评审、偏差和未验证项）

语义：

- `intent.md` + `contract.md` 是需求和契约来源，回答“要做什么、边界是什么”。
- `technical-design.md` 是实现依据，回答“怎么实现”。
- `test-plan.md` 是自测依据，回答“怎么证明它真的被验证过”。
- `plan.md` 是施工步骤，必须服从前面的需求、契约、技术设计和测试计划。
- `review.md` 只记录实际结果、偏差、真实验证证据和未运行项。

不得绕过、重写或临时发明一套与既有文档冲突的方案。

## 入口检查

1. 用 `git status --short --branch` 确认仓库、分支和脏工作区。
2. 改文件前先读仓库规则：
   - `AGENTS.md`
   - `CLAUDE.md` 或 `CLAUDE.zh.md`（存在时）
   - `docs/product-model.md`
   - `docs/iterations/README.md`
   - 当前 milestone README / 当前迭代包（如果存在）
3. 不得发明新的 product lifecycle stage、internal Agent role、milestone boundary 或 verification semantics。
4. 如果当前目录不是 WebAgentFlow checkout，停止并询问正确路径。
5. 分支名以 `-local` 结尾时不得 push。

## 判断迭代类型

开始实现前必须分类，并写入迭代包 `README.md`：

- `docs`：只改文档、流程、规划。
- `code`：涉及运行时代码、schema、API、service、UI、CLI、测试、migration 或 fixture。
- `mixed`：文档 + 任何代码型改动。按 `code` 门禁处理。

文档型迭代可以省略 `technical-design.md`。混合型迭代必须走代码型门禁。

## 必需文档

所有非平凡迭代都放在同一个里程碑迭代包：

```text
docs/iterations/m<N>/<iteration>/
```

文档型迭代需要：

- `intent.md`
- `contract.md`：当概念、状态、schema、evidence、边界、流程规则、milestone 语义、Agent 边界或迭代模板变化时必填；否则写 `N/A` 和原因
- `plan.md`
- `review.md`

代码型 / 混合型迭代在实现前需要：

- `intent.md`
- `contract.md`
- 已审核的 `technical-design.md`，且必须包含 contract alignment
- `test-plan.md`
- `plan.md`
- `review.md`

新建迭代文档时优先使用 `docs/iterations/templates/`，并优先用中文。

## 技术设计门禁

非平凡代码实现开始前，`technical-design.md` 必须已经存在并完成审核。

`technical-design.md` 不是测试执行手册，它是实现施工图，必须覆盖：

- 当前状态
- 合约对齐 / 不变量
- 实现方案
- 影响面
- 数据模型 / schema 变更
- service / module 设计
- 数据流
- 状态推导
- 兼容性
- 失败 / 边界情况
- 非目标
- 高层 Test Matrix
- 验证命令入口

`contract.md` 里的每个关键状态、边界、兼容性规则和非目标，都必须映射到实现机制和测试入口；无法映射时写 `N/A` 和原因。

如果用户要求实现，但设计门禁还没满足，先补齐或更新必要文档，然后停下来等待设计审核，除非用户明确说技术设计已经审核通过。

## test-plan.md 执行门禁

只要迭代包里存在 `test-plan.md`，执行型 Agent 就必须按它执行自测；不得改用自己临时生成的测试清单，也不得只挑容易的项执行。

执行前必须确认：

- `test-plan.md` 是当前迭代包里的文档。
- `test-plan.md` 和 `technical-design.md` 的 Test Matrix 没有明显冲突。
- `test-plan.md` 里的 required 项都有执行路径，或能说明无法执行的环境限制。
- `test-plan.md` 里的 live run / E2E / UI smoke 边界没有违反仓库规则。

`technical-design.md` 只写高层 Test Matrix。`test-plan.md` 写详细测试范围、场景、命令或产品入口、预期证据、是否必跑、live-run 边界和未运行风险。`review.md` 只记录实际执行结果。

代码型 / 混合型迭代缺少 `test-plan.md` 时，不得把任务视为完整开发包。执行型 Agent 必须先报告
文档缺口，并按用户指示补齐或等待审核；不得用临时测试清单替代。若 `test-plan.md` 存在但明显
过期、覆盖不完整，或与 `contract.md` / `technical-design.md` 冲突，停止实现或自测，向用户报告
缺口，并请求用户确认是否修补或重新生成测试计划。

## 工具能力检查

执行 E2E、UI smoke、Browser Use、Computer Use 或 live-run 自测前，必须先确认当前工具环境真的可用。

常见能力来源：

- Browser / in-app browser：用于打开本地 Web 应用、截图、点击、检查页面状态。
- Chrome / browser extension：用于需要用户登录态、真实 Chrome tab、扩展或远程认证站点的浏览器验证。
- Playwright MCP：用于浏览器自动化和 E2E。
- Computer Use：用于操作 macOS app、GUI-only 工具或无法通过浏览器完成的验证。
- Shell / CLI：用于运行 repo 测试、Playwright 脚本或命令行验证。

没有实际打开浏览器 / Chrome / Playwright / Computer Use / CLI，就不得声称完成对应验证。若工具不可用、权限不足或用户未要求 live run，必须在 `review.md` 记录 `not run` / `unverified` 和原因。

## 验证诚信

不得声称执行过没有真实证据的测试。

允许作为证据的内容包括：

- 真实命令输出和 exit code。
- pass / fail / skip 数量。
- 浏览器 URL、页面、操作路径、截图、trace 或可复查的产品结果。
- `verify-scenario` 或 autonomous run 的 `run_id`、`pass_gate.status`、supervisor verdict 和 scorecard。
- 日志路径或输出文件路径。

硬规则：

- 没有真实浏览器或产品 UI 证据，不得声称完成 E2E / UI smoke。
- 没有真实 CLI / command 输出，不得声称 CLI 已测试。
- 代码阅读、静态推理和 diff review 只能写成 review / inspection，不能写成 tested。
- 缺少证据时，结论必须写成 `not run` 或 `unverified`。

## WebAgentFlow Live Run 边界

除非用户明确要求 live run，不得触发：

- `verify-scenario`
- autonomous run
- product-driven browser execution
- 直接调用 autonomous-run endpoint

如果用户明确要求 live run，只能使用仓库规则允许的入口，并记录：

- invocation surface
- `run_id`
- `pass_gate.status`
- supervisor verdict
- scorecard
- 是 product UI traffic 还是 skill invocation
- 原始输出或可复查路径

`pass_gate.status` 是权威结果；`unverified` 不是通过。

## 执行流程

1. 检查仓库状态和相关文档。
2. 判断迭代类型。
3. 如果已有迭代包，先按“核心顺序”读取并服从已有文档。
4. 如果缺少需求、契约、技术设计、测试计划或实施计划文档，先补齐或请求用户审核；代码型 /
   混合型迭代不得用临时测试清单替代 `test-plan.md`。
5. 代码型 / 混合型迭代缺少已审核 `technical-design.md` 时，写完设计后停止等待审核。
6. 只要 `test-plan.md` 存在，就必须按它执行自测；无法执行的项必须写入 `review.md` 的 `not run` / `unverified`。
7. 只在门禁满足后按 `technical-design.md` 窄范围实现。
8. 按 `test-plan.md` / `plan.md` 运行允许的自测。
9. 更新 `review.md`，记录实际交付、验证证据、未运行项和 `unverified` 项。
10. 除非用户明确要求，不得 commit。
11. 分支名以 `-local` 结尾时不得 push。

## 最终回复

简洁报告：

- 迭代类型，以及创建 / 更新了哪些迭代文档。
- 修改了哪些文件。
- 实际运行了哪些验证，包含 exit code / counts / 证据。
- 哪些没有运行或仍是 `unverified`，原因是什么。
- 只有在用户明确要求并已创建 commit 时，才报告 commit hash。
