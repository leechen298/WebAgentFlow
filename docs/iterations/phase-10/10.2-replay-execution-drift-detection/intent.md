# 10.2 · Replay execution + drift detection

## 执行前必读

开发本目录任务前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/phase-10/phase-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

状态：**可执行**。

硬边界：只执行 M10 `10.2`；不做 `10.3+`；不扩展 popup /
custom click-toggle / form-label extractor；不触发 autonomous run 创建
接口；不把 replay 结果伪装成 `pass_gate` 或 Supervisor verdict。

术语边界：M10 是交付里程碑；L1 / L2 / L3 是产品生命周期阶段。本包
服务于未来的 **M11 Task-to-Path Planning MVP**，但不实现 L3 task
runner。

## 当前关系

10.1 到 10.1.5 已经把“学会一条路”这件事落地：

- `pass_gate = pass` 的 autonomous run 会沉淀为 `learned_paths`。
- LearnedPath 当前保存：
  - `page_template`
  - `query_signature`
  - `dom_fingerprint`
  - `scenario`
  - `actions`
  - `trust`
  - `source_run_id`
- LearnedPath catalog 已经是路径资产的主入口，支持查看 actions、
  过滤 trust、确认路径、标记不稳定、废弃路径。

但系统现在还停在“我学会了”：

- 用户能看到一条 LearnedPath，但不能让系统照着它再走一次。
- 系统也不能告诉用户这条路径现在是还可用、页面变了、还是按钮 /
  输入框找不到了。

10.2 的位置就是把 LearnedPath 从“记录”推进到“可复用资产”。M11 的
Agent D · Path Planner Agent 之后可以调用 replay 能力，但 10.2 自身
不做任务理解、路径选择或参数绑定。

## 目标

让用户能在已有 LearnedPath 的前提下，复刻一次同样的行为，并得到
可解释的 replay / drift 结果。

一句话：**点一条已经学过的路径，系统重新打开页面，照着旧步骤跑一遍；
能跑就说明还可复用，不能跑就说清楚卡在哪里。**

本迭代完成后：

- LearnedPath catalog 里能对单条路径发起 replay。
- 后端能按这条 LearnedPath 重新打开页面并分析当前页面。
- 后端能判断当前页面和已学路径是否还对得上。
- 后端能检查已存 actions 的目标 selector 是否还能定位。
- selector 和 action 类型都可用时，后端能按已存 actions 执行。
- replay 返回独立结果，不混用 autonomous exploration 的 `pass_gate`、
  Supervisor verdict 或历史 run review。
- replay 失败不会静默重试，也不会自动转入重新学习。

## 边界（本轮不做）

- 不做 popup-based control 支持。Cascader、DatePicker、RangePicker、
  表头筛选等属于 `10.3`。
- 不做 custom click-toggle 支持。Tag / pill / 非原生点击筛选属于
  `10.4`。
- 不做跨页面模式归纳。login / search / CRUD 共性归纳已迁入 M14 backlog。
- 不实现完整 L3 task runner；本轮只验证 LearnedPath 能否复刻。
- 不实现 Agent D · Path Planner Agent。
- 不做用户自然语言任务入口、path retrieval / ranking、slot binding、
  pre-execution confirmation 或 Agent E 结果报告；这些属于 M11。
- 不引入 LLM 对每一步 replay 结果做判断。
- 不自动调用 autonomous learning 兜底；drift 是结果，不是隐藏重试入口。
- 不新增账号、多租户、reviewer identity 或数据隔离字段。

## 成功标准

1. 用户能从 LearnedPath catalog 对一条 LearnedPath 发起 replay。
2. replay API 能返回结构化结果，至少包含：
   - 使用的 LearnedPath id
   - replay status
   - drift status
   - drift reasons
   - step logs
   - final URL / title / screenshot 或可审计的最终状态摘要
3. `actions=[]` 的 observational LearnedPath 能被正确处理：它不是
   replay 失败，而是“打开页面并观察即可”的路径。
4. 已存 action 类型超出当前支持范围时，返回 `unsupported_action` 一类
   可解释状态，不尝试乱点。
5. 页面结构 hash 变化时，不直接说“轻微 / 严重”这种不可证明的话；
   第一版以 selector 是否仍可定位作为可执行判断。
6. selector 找不到时，不执行后续步骤，并明确返回缺失目标。
7. replay 不调用 `plan_actions` 生成新动作；它只执行 LearnedPath 中
   已存的 actions。
8. replay 不调用 `/exploration/autonomous-runs` 或
   `/exploration/autonomous-runs/stream`。
9. 单测覆盖命中、无候选、trust 过滤、signature 变化、selector 缺失、
   unsupported action、`actions=[]`。
