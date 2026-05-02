# Phase 10 全量计划

本文是 Phase 10 的阶段级执行计划，用来回答“接下来按什么顺序做、每
一包交付什么、哪些已经可执行”。Phase 10 使用语义编号目录，目录名前缀
与任务编号一致，例如 `10.2-replay-execution-drift-detection/`。
每个真正开始执行的工作仍然要有 `intent.md` + `plan.md`，本文件不
替代迭代三件套。

## 权威输入

开发 Phase 10 任务前，请先读完本节列出的权威输入，再读对应执行包
的 `intent.md` 和 `plan.md`。

- [`docs/product-model.md`](../../product-model.md) —— 产品边界：
  AI 编码 Agent 只写代码；真实运行由 WebAgentFlow 引擎和内部
  Supervisor 完成。
- [`docs/roadmap.md` § Phase 10](../../roadmap.md) —— Phase 10 的
  阶段范围。
- [`docs/iterations/README.md`](../README.md) —— 每个迭代目录的
  写法和收尾要求。
- [`AGENTS.md`](../../../AGENTS.md) / [`CLAUDE.md`](../../../CLAUDE.md)
  —— 仓库级执行边界，尤其是 autonomous run 的禁止项。

## 当前状态与执行顺序

### 10.1 · LearnedPath persistence

状态：完成。执行包：
[`10.1-learned-path-persistence/`](./10.1-learned-path-persistence/)。

交付：

- `learned_paths` 表与 repo。
- `pass_gate = pass` 自动 ingest。
- history 详情页的 LearnedPath 信用操作。

证据见
[`10.1-learned-path-persistence/review.md`](./10.1-learned-path-persistence/review.md)。

### 10.1.1 · Autonomous use-case catalog

状态：可执行。执行包：
[`10.1.1-autonomous-use-case-catalog/`](./10.1.1-autonomous-use-case-catalog/)。

目标：

- 新增一个 console 页面，列出 `/exploration/specs` 中所有 authored
  specs 和 scenarios。
- 每个 scenario 提供“进入 workbench”动作，把 `url`、`spec_id`、
  `scenario`、`goal` 带到 `/exploration/autonomous`。

边界：

- 不改 autonomous engine。
- 不调用 `/exploration/autonomous-run`。
- 不新增后端接口，除非执行时发现 `/exploration/specs` 缺少必要字段。

定位：

- 这是插入在 `10.1` 与 `10.2` 之间的 supporting iteration。
- 它解决“当前有哪些 authored use cases 可跑”的入口问题，不改变
  engine、不消费 LearnedPath。

### 10.2 · Replay execution + drift detection

状态：draft only，不可直接施工。执行包：
[`10.2-replay-execution-drift-detection/`](./10.2-replay-execution-drift-detection/)。

目标：

- 读取 `confirmed` / `provisional` LearnedPath。
- 对当前页面重新做 page analysis，和存储的 `dom_fingerprint` /
  actions 做 drift check。
- drift 低时按存储 path 执行；drift 高时回退到 autonomous learning
  或产出需要用户处理的状态。

预期触及：

- `apps/api/app/repos/learned_paths_repo.py`
- `apps/api/app/services/learning/page_signature.py`
- `apps/api/app/services/execution/`
- `apps/api/app/routers/exploration.py`
- console history / LearnedPath 展示面

验收方向：

- 有 repo / service 单测覆盖 hit、miss、drift。
- replay 失败不会静默重试；必须返回可解释状态。
- 若使用 live run，只能通过 `verify-scenario` skill，并按
  `pass_gate.status`、Supervisor verdict、5 项 scorecard、`run_id`
  原样汇报。

### 10.3 · Popup-based control support

状态：draft only，不可直接施工。执行包：
[`10.3-popup-based-control-support/`](./10.3-popup-based-control-support/)。

目标：

- 支持需要先点触发器、再在弹层内操作的控件：Cascader、
  DatePicker、RangePicker、MonthPicker、表头筛选 / 排序等。
- planner 的动作模型要能表达“两段式操作”：open popup → choose /
  type / confirm。

预期触及：

- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/action_planner.py`
- `apps/validation-site/src/pages/UsersPage.vue`
- `apps/validation-site/specs/users.assertions.json`

验收方向：

- `users` fixture 中至少一个 popup 控件 scenario 变绿。
- 不把 popup 控件伪装成普通 text input。
- 不影响 Phase 9 已覆盖的 plain text / native radio path。

### 10.4 · Custom click-toggle controls

状态：draft only，不可直接施工。执行包：
[`10.4-custom-click-toggle-controls/`](./10.4-custom-click-toggle-controls/)。

目标：

- 支持 Tag-as-filter、pill、非原生 checkbox/radio 的点击切换控件。
- 这类控件不弹 popup，交互面本身就是触发器。

预期触及：

- `page_analyzer.py`
- `action_planner.py`
- `supervisor_observations.py` / scorecard 需要时补充观察项
- `users` fixture 和 spec

验收方向：

- 能识别“点击某个 tag 后 query param / 列表内容变化”的路径。
- 和 popup-based controls 分开实现，避免把两类状态机混在一起。

### 10.5 · Form-label extractor coverage expansion

状态：draft only，不可直接施工。执行包：
[`10.5-form-label-extractor-expansion/`](./10.5-form-label-extractor-expansion/)。

目标：

- 在现有 Ant Design + HTML5 label 基础上，补常见 UI 库的 label
  提取 handler。
- 候选：Element Plus、Naive UI、Arco Design、TDesign、Quasar、
  MUI。

预期触及：

- `apps/api/app/services/learning/form_label_extractor.py`
- 对应单测 / fixture

验收方向：

- 每个 handler 有独立最小 HTML 样例测试。
- dispatcher 仍然按“第一个命中”返回，不引入 LLM 推断。

### 10.6 · Cross-page pattern mining

状态：draft only，不可直接施工。执行包：
[`10.6-cross-page-pattern-mining/`](./10.6-cross-page-pattern-mining/)。

目标：

- 在多个 LearnedPath 之间识别 login / search / CRUD 等可复用模式。
- 输出可供后续 planner 读取的 pattern，而不是直接执行浏览器动作。

预期触及：

- `learned_paths` 读取层。
- 新的 pattern service / schema。
- console 的模式查看入口（可后置）。

验收方向：

- 至少能从 `login` 与 `users` 的已学路径中归纳出稳定 pattern
  metadata。
- 不在运行时“凭空发明”路径；pattern 只能来自已验证 / 已确认数据。

## 执行规则

开始任一执行包前，最小上下文应包含：

1. 仓库根目录的 `AGENTS.md`。
2. `docs/product-model.md`。
3. 本文件。
4. 对应执行包目录下的 `intent.md` 和 `plan.md`。

施工指令应直接写出上述阅读顺序。

硬边界：

- 每次只能实现当前迭代包，不顺手做后续 Phase 10 项。
- `draft only` 执行包不能直接施工；开工前必须重新核对当前代码和上
  一个迭代结果，并把 `plan.md` 修订成可执行状态。
- 需要 live autonomous run 时，只能走 `verify-scenario` skill；不得
  curl / fetch `/exploration/autonomous-run`。
- 汇报 live run 必须以 `pass_gate.status` 开头，并原样给出
  Supervisor verdict、5 项 scorecard 和 `run_id`。
- 如果只是前端页面 / 文档整理，不需要 live run。
