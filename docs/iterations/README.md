# 迭代文档规范（docs/iterations/）

> 这是 WebAgentFlow 的**过程文档**规范。规定每一次迭代（feature、bugfix、
> 重构、探索、文档治理都算）要留下什么文档、放在哪、写什么。目的是让下一轮
> AI 编码 Agent（Claude Code / Codex / Kimi / MiMo / …）和下一次打开这个仓库的
> 你自己，都能快速接上当前在做什么、为什么这么做、做到哪了。

## 为什么要有这个目录

- `docs/product-model.md`、`docs/architecture.md` 是**稳态文档**（回答“我们是谁、
  怎么长的”），改动缓慢、成本高。
- `docs/roadmap.md` 是**交付里程碑路线图**（回答“这个里程碑要交付什么”），
  按 M10 / M11 / ... 粒度。
- `.dev-logs/` 是**运行证据**（scenario 的 autonomous 执行日志存档），给调试用。
- 中间缺的是：**每次具体迭代的意图、契约、技术设计、计划、审核**。这些不能只
  散在对话、提交信息或聊天记录里。`docs/iterations/` 就是这一层的单一事实来源。

把“过程文档当作任务的单一事实来源”：跨 chat、跨 Agent 接手的时候，读迭代目录
就能重新获得上下文。

## 目录结构

```
docs/iterations/
├── README.md                            # 你正在看这份规范
├── templates/                           # 新迭代包模板
│   ├── README.md
│   ├── intent.md
│   ├── contract.md
│   ├── technical-design.md
│   ├── test-plan.md
│   ├── plan.md
│   └── review.md
└── m<N>/
    ├── README.md                        # 本交付里程碑的总目标 + 迭代索引
    ├── 01-<slug>/
    │   ├── README.md                    # 本迭代包索引 + 状态
    │   ├── intent.md                    # 做什么 + 为什么 + 不做什么（迭代开始时写）
    │   ├── contract.md                  # 是什么：概念 / 状态 / 字段 / 边界契约
    │   ├── technical-design.md          # 怎么实现：服务、schema、数据流、兼容性、高层测试入口
    │   ├── test-plan.md                 # （强触发时必填）详细测试方案、E2E / live run 边界
    │   ├── plan.md                      # 改哪些文件 + 分步实施 + 验证入口
    │   ├── review.md                    # codex-review / 用户反馈 / 最终差异 / 实际验证证据
    │   ├── summary.md                   # （可选）收尾摘要：关键决策 + 主要交付 + commit 序列
    │   └── changes.txt                  # （可选）`git diff --name-status <base>..HEAD` 输出
    ├── 02-<slug>/
    │   └── …
    └── …
```

## 迭代包类型

### 文档型迭代

用于 roadmap、product model、scope、文档治理、方案讨论等不改运行时代码的工作。
文档型迭代可以不写 `technical-design.md`。

```
README.md
intent.md
contract.md      # 涉及概念、状态、字段、边界、流程规则或模板变化时必须有；否则写明 N/A 并说明原因
test-plan.md     # 触发复杂验证条件时才需要；普通 docs-only 迭代可省略
plan.md
review.md
```

文档型迭代只要改变 process rules、milestone semantics、Agent boundaries、
evidence semantics 或 iteration templates，也必须写 `contract.md`。

### 代码型迭代

只要这一轮会修改运行时代码、schema、API、service、UI、CLI、测试或迁移，就按代码型
迭代处理。

```
README.md
intent.md
contract.md
technical-design.md
test-plan.md     # 触发复杂验证条件时必填
plan.md
review.md
```

### 混合型迭代

只要同一轮同时包含文档治理和任何代码 / schema / API / service / UI / CLI / 测试 /
迁移改动，就按**代码型迭代**处理，必须通过 `technical-design.md` 门禁。

核心区别：

- `contract.md` 定义“是什么”：概念、状态、字段、边界、输入输出语义。
- `technical-design.md` 定义“怎么实现”：模块边界、数据流、兼容性、异常、高层测试入口。
- `test-plan.md` 定义“怎么验收”：当前迭代具体测什么、谁执行、走哪些命令或产品界面、
  哪些 live run 明确不跑。
- `plan.md` 定义“改哪些文件、按什么顺序改、验证入口是什么”。
- `review.md` 记录“实际做成什么、和原设计有什么偏差、实际跑了什么、哪些没跑以及原因”。

## 两阶段工作规则

### 生成开发文档阶段

当任务是为**代码型**或**混合型**迭代生成开发文档时，必须先按
`docs/iterations/templates/` 生成完整迭代文档包：

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

这一步的目标是把“要做什么、边界是什么、怎么实现、怎么自测、怎么记录实际证据”一次性
钉住。不能只写 `intent.md` + `plan.md` 就把任务交给实现 Agent。

文档型迭代只有在**不准备后续代码实现**时，才可以省略 `technical-design.md` 和
`test-plan.md`。如果文档型迭代改变流程规则、里程碑语义、Agent 边界、证据语义、
迭代模板、概念、状态、字段或产品边界，仍必须包含 `contract.md`。

### 代码开发阶段

当任务是代码开发时，Agent 必须先读取当前迭代包，并按以下文档实现和自测：

1. `intent.md`
2. `contract.md`
3. 已审核的 `technical-design.md`
4. `test-plan.md`
5. `plan.md`
6. `review.md`（了解已有评审、偏差、未验证项）

实现必须服从 `contract.md`、`technical-design.md`、`test-plan.md` 和 `plan.md`。不得绕过、
重新解释或静默替换这些文档。若实现过程中发现设计问题，必须先停止实现，更新对应迭代文档
并经过审核，再继续开发。

## technical-design.md 硬规则

凡是**非平凡代码迭代**，在 `technical-design.md` 生成并完成审核前，不得进入代码实现。

只要满足任意一条，就必须有 `technical-design.md`：

- 修改 schema / API request / API response；
- 新增 service、repository、model、router、CLI command 或 worker flow；
- 修改 replay / reporter / orchestrator / planner；
- 新增 aggregation、state transition、status derivation 或 ranking；
- 跨两个以上模块；
- 涉及兼容性、旧数据、旧 response、迁移或回滚；
- 涉及 Agent / Reporter / recovery / abort / consent 边界；
- 涉及 evidence / observation / verification / scorecard；
- 涉及 runtime safety、browser continuation、retry、timeout 或 partial result；
- 涉及 UI 和 API / service 的协同语义。

典型例子：

- `11.2.3 Replay Integration with Observation`；
- `11.2.5 Observation Evidence into Task Result Reporter`；
- `M12 Recovery / Retry / Abort`；
- 未来 `M11.3 Page Context Bridge`；
- 未来 `Common Component Runtime Semantics`。

不满足上述条件的小改动（typo、纯格式、单文件注释修正）可以不建完整技术设计，但仍要在
`review.md` 里说明为什么没有展开。

## 命名规则

- **里程碑目录**：命名为 `m<N>`，`<N>` 是整数，对齐 `docs/roadmap.md` 里的交付
  里程碑编号。文档正文里请写 M10 / M11，产品生命周期则写 L1/L2/L3。
- **迭代目录**：默认使用 `<NN>-<slug>`。`<NN>` 是两位数字（`01` / `02` / …），
  **在里程碑内部递增**，不跨里程碑。`<slug>` 是简短 kebab-case 英文名，3–5 个词，
  和 git 分支名或 commit 主题呼应。例子：`01-codex-review-skill`、
  `02-supervisor-retry-policy`。
- 如果某个里程碑已经有更明确的阶段内语义编号，也可以使用
  `<milestone-item-number>-<slug>`，例如
  `10.1.1-autonomous-use-case-catalog/`。使用这种形式时，里程碑 README 里的任务编号
  和目录名前缀必须完全一致。
- **固定文件名**：`README.md` / `intent.md` / `contract.md` / `technical-design.md` /
  `test-plan.md` / `plan.md` / `review.md`。不要改名，不要用同义词。

## 什么时候新开一个迭代目录

- 要开始一次“有一次独立收尾”的工作就开。典型粒度：一个 feature / 一个 bug 修复 /
  一次重构 / 一次调研 / 一次文档治理。
- 不要为“改一个 typo”之类的零碎小改动建目录。
- **一个迭代 ≈ 一个 PR 或一个 commit 序列**。如果当前目录的工作分化成两件事，
  把后半段拆进下一个编号的新目录。

## 每个文件写什么

### README.md（迭代包索引）

说明这个迭代包的类型、状态、文档清单和当前审核状态。它是给接手 Agent 快速定位用的，
不是技术细节正文。

### intent.md（迭代开始前写；写完再动手）

回答三个问题，不写代码细节：

1. **目标** —— 这次迭代的成功状态是什么？
2. **动机** —— 为什么现在做？背后的约束 / 用户痛点 / 技术债 / 里程碑目标是什么？
3. **边界** —— **明确不做什么**。列 2–3 条“虽然相关但这轮不碰”的事，防止范围蔓延。

### contract.md（进入设计前写；定义“是什么”）

用于钉住语义边界，尤其是 WebAgentFlow 里容易漂移的状态、证据、Agent / Reporter 边界。

必须覆盖：

- 本轮新增或修改的概念；
- 状态 / 枚举 / 字段含义；
- 输入 / 输出 / API 语义；
- evidence / observation / verification 的来源和边界；
- 和现有 product model、scope boundary、roadmap 的关系；
- 明确不改变的旧契约。

必须显式回答：

- 是否改变 product lifecycle stage、internal Agent role、milestone boundary；
- 如果改变，先更新哪些权威文档；
- 哪些 public API、database schema、replay status semantics、reporter / recovery / abort
  boundary 保持不变。

如果确实没有契约变化，也要写 `No contract changes` 或 `N/A`，并说明原因。空白或隐式省略
不算完成。

### technical-design.md（代码型迭代必填；定义“怎么实现”）

固定章节：

```markdown
# 技术设计（Technical Design）

## 当前状态（Current State）
当前已有代码、schema、service、测试是什么。

## 合约对齐 / 不变量（Contract Alignment / Invariants）
contract.md 中的关键状态、边界、兼容性、非目标，如何落实到实现机制和测试。

## 实现方案（Proposed Implementation）
本轮具体怎么实现。

## 影响面（Affected Surfaces）
哪些入口面会改变：API、response schema、DB、CLI、Console UI、conversation events、
replay、reporter、worker、tests / fixtures、docs。

## 数据模型 / Schema 变更（Data Model / Schema Changes）
新增或修改哪些 schema，是否向后兼容。

## 服务 / 模块设计（Service / Module Design）
新增哪些 service，函数签名是什么，输入输出是什么。

## 数据流（Data Flow）
从入口到输出的流程。

## 状态推导（Status / State Derivation）
状态如何推导，优先级是什么。

## 兼容性（Compatibility）
旧数据、旧 API、旧 response 如何兼容。

## 失败 / 边界情况（Failure / Edge Cases）
异常、空值、timeout、partial result 怎么处理。

## 非目标（Non-goals）
本轮明确不做什么。

## 测试矩阵入口（Test Matrix）
必须覆盖哪些测试。

## 验证命令入口（Validation Commands）
执行哪些命令。
```

技术设计不是最终实现的重复描述。它要先把语义边界、状态推导、兼容性和测试矩阵钉住，
防止后续实现变成“能跑，但语义歪了也能跑”。代码型迭代的 `technical-design.md` 必须
包含 contract alignment：`contract.md` 里的关键状态、边界、兼容性规则、非目标，
都要映射到实现机制和测试覆盖；无法映射时必须写 `N/A` 并说明原因。

`technical-design.md` 不承载完整测试执行手册。它只写高层 Test Matrix：哪些 API unit、
service integration、Console E2E、reporter evidence、recovery boundary 等测试类型必须兜住
哪些契约。详细场景、命令、界面入口、执行人、live run 边界和 not-run 风险放到
`test-plan.md`。

### test-plan.md（强触发时必填；定义“怎么验收”）

`test-plan.md` 不是所有迭代的固定必填项，但只要满足任意一条就必须创建：

- 涉及前后端协同；
- 涉及 Agent / Reporter / recovery / abort / replay；
- 涉及 E2E；
- 涉及 `verify-scenario`、autonomous run、Codex / AI 作为外部测试操作员；
- 测试矩阵超过 5 个 case；
- 涉及人工测试、UI smoke、product-driven browser execution；
- 需要区分 unit / integration / E2E / live product evidence。

`test-plan.md` 必须说明：

- 每个测试层级的范围：unit、integration、API、Console UI、E2E、Agent / Reporter /
  Recovery、Codex / AI external operator、live autonomous run；
- 每个场景的 command / product surface、expected evidence、required 与否；
- 哪些 live run 被明确排除，为什么排除；
- 如果需要真实浏览器、CLI、`verify-scenario` 或 autonomous run，谁来执行、从哪个入口执行、
  需要留下什么可复查证据。

没有真实打开浏览器或产品 UI，不得声称已完成 E2E / UI smoke。没有真实运行 CLI / command，
不得声称 CLI 已测试。代码阅读、静态推理和 diff 审查只能写成 review / inspection，
不能写成 tested。缺少 command output、`run_id`、截图、日志、exit code、pass / fail count
或可复查输出时，结论必须写成 `not run` / `unverified`。

### plan.md（动手前写；随实际工作修订）

把 intent / contract / technical-design 落成可执行步骤。回答三个问题：

1. **要动的文件和模块** —— 列表，不含大段代码。
2. **步骤** —— 顺序化的工作拆分，每步应该能独立验证。
3. **验证入口** —— 运行哪些命令，如何对应成功标准和测试矩阵；如果触发 `test-plan.md`
   条件，详细测试场景必须放在 `test-plan.md`，这里只保留执行入口和顺序。

计划在执行中**允许修订**。如果中途发现原计划错了，在这个文件里更新，不要另开文档。

### review.md（迭代过程 & 结束时写）

这个文件**可以追加多次**。三种内容按时间顺序往里塞：

1. **codex-review 产出**：`/codex-review` skill 执行后的原始结论 + 分级。
2. **用户反馈**：人工审核里用户提出的关键意见，记一句话 + 是否采纳。
3. **最终差异**：迭代收尾时回看一次：和 intent / contract / technical-design / plan 相比，
   实际做出来的有什么偏离？为什么？

验证证据必须记录 command / surface、expected、actual result、exit code、pass / fail / skip
count、证据路径和未运行原因。除非用户明确要求 live run，不得触发 `verify-scenario`、
autonomous run 或产品驱动的浏览器执行。若用户明确要求 live run，必须记录 invocation
surface、`run_id`、`pass_gate.status`、supervisor verdict、scorecard，以及它是 product UI
traffic 还是 skill invocation。`review.md` 只能记录实际执行过的验证；没跑的必须写成
`not run` / `unverified`，不能用“应该可以”替代证据。

## 与其他文档的关系

| 文档 | 性质 | 更新频率 | 和迭代目录的关系 |
|---|---|---|---|
| `docs/product-model.md` | 稳态 | 极少 | 迭代开始前读；迭代**不得**隐式改变产品模型 |
| `docs/architecture.md` | 稳态 | 少 | 架构演进完成并稳定后再回写 |
| `docs/scope-boundaries.md` | 稳态 | 少 | `intent.md` / `contract.md` 的边界必须和它一致 |
| `docs/roadmap.md` | 里程碑级 | 每个交付里程碑更新 | 里程碑 README 应该链回 roadmap 里对应的 M 段落 |
| `docs/iterations/m<N>/` | 过程 | 每次迭代 | **本文档** |
| `.dev-logs/` | 运行证据 | 每次 autonomous run | scenario 调试证据，和迭代无直接绑定 |

## 与 codex-review skill 的联动

全局 review 工具如果只能自动读取 `intent.md` + `plan.md`，执行者必须在 review 请求里手动补充
同目录的 `contract.md`、`technical-design.md`，以及触发时的 `test-plan.md`。对代码型迭代来说，
缺少 `technical-design.md` 的 review 不能作为实现前审核通过；对复杂验证迭代来说，缺少
`test-plan.md` 的 review 不能作为验证方案审核通过。

推荐 review 上下文顺序：

1. `intent.md`
2. `contract.md`
3. `technical-design.md`
4. `test-plan.md`（触发时）
5. `plan.md`
6. 当前 diff

所以：**intent 说明目标，contract 钉住语义，technical-design 钉住实现边界，
test-plan 钉住验收边界，plan 才是施工步骤。**

## 里程碑 README 怎么写

每个 `m<N>/README.md` 是本交付里程碑的索引页。正文请称 M<N>。结构：

```markdown
# M<N>: <标题>

<一段话说明本交付里程碑的总目标，引用 docs/roadmap.md 的对应段落>

## 迭代索引
- [01-<slug>](./01-<slug>/) —— <一句话>（状态：进行中 / 完成 / 放弃）
- [02-<slug>](./02-<slug>/) —— <一句话>
```

里程碑开启时建空骨架，每次新迭代追加一行。迭代完成后更新状态标记，不要删除。

## 实操约定

1. **intent 先行**：没有 `intent.md` 就不要开始写代码。哪怕只有两句话也行。
2. **contract 先钉语义**：涉及概念、字段、状态、边界、evidence、Agent / Reporter / recovery
   语义时，先写 `contract.md`。
3. **technical-design 门禁**：非平凡代码迭代在包含 contract alignment 的
   `technical-design.md` 生成并审核前，不得进入实现。
4. **test-plan 强触发**：复杂代码迭代、跨层验证、E2E、live run 或 Codex / AI 外部测试操作员
   相关迭代必须写 `test-plan.md`。
5. **证据先于结论**：没有真实浏览器 / CLI / run_id / 截图 / 日志 / exit code 等证据，不得声称
   已完成 E2E、UI smoke、CLI、`verify-scenario` 或 autonomous-run 测试。
6. **review 当天写**：不要拖到“以后再补”。用户反馈和收尾反思要当天写进 `review.md`。
7. **不删历史**：迭代做废了、方案推翻了，更新 `review.md` 说明为什么放弃，但**不要删**目录。
