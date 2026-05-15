# 11.2.0 实施计划

## 触及文件

新增：

- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/README.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/intent.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/plan.md`
- `docs/iterations/m11/11.2-runtime-observation-realistic-hardening/review.md`
- `docs/testing/scenarios/realistic-web-runtime-cases.md`

轻量更新：

- `docs/iterations/m11/README.md`
- `docs/iterations/m11/m11-plan.md`
- `docs/roadmap.md`

不修改：

- 源码。
- 测试代码。
- package 文件。
- 根目录 README。
- architecture 或 product-model 文档。
- M12 / 12.x / v0.2 文件或分支。

## 步骤

1. 用 `git branch --show-current` 和 `git status --short` 确认分支和工作区状态。
2. 阅读当前 M11 README、M11 plan、roadmap 和 M11.1 收口文档。
3. 创建 11.2 总览文档，说明与 M11.1 的关系、M12 边界、Post-action
   Observation、Passive Runtime Observation 和后续拆包。
4. 创建 11.2.0 intent 文档，写清文档初始化目标和硬边界。
5. 创建本 plan 文档，记录触及文件、步骤和验证方式。
6. 初始化 `review.md`，仅作为状态占位，不声明 implementation review 已完成。
7. 在 `docs/testing/scenarios/` 下创建 realistic web runtime case catalog。
8. 在 `docs/iterations/m11/README.md` 中新增一条 11.2 索引。
9. 在 `docs/iterations/m11/m11-plan.md` 中新增 M11.2 章节，记录 scope、边界和
   11.2.0-11.2.7 拆包。
10. 在 `docs/roadmap.md` 中只新增高层 M11.2 说明。
11. 运行允许的验证命令。

## Scenario Catalog 规则

`docs/testing/scenarios/realistic-web-runtime-cases.md` 是 runtime case catalog，
不是测试计划或证据报告。

每个 case 应包含：

- case name。
- scenario。
- why it matters。
- M11.2 expected observation。
- not in scope。
- future M12 implication。
- future package。

catalog 不得声称这些 case 已经自动化、人工验证或被 E2E 覆盖。

## 与 11.2.1 的关系

11.2.1 在 11.2.0 的 scope 和 case catalog 基础上定义 Observation Signal
Contract。它应覆盖本目录和
`docs/testing/scenarios/realistic-web-runtime-cases.md` 中列出的核心 runtime
cases，但不实现观察、wait-for-change、replay integration 或 reporter integration。

11.2.1 必须明确：

- `page_load_started` / `page_load_finished` 是浏览器级 page load /
  document reload signal。
- `loading_started` / `loading_finished` 是页面内 visible loading UI signal。
- timeout / not-observed 不属于 11.2.1 signal kind。

## 与 11.2.2 的关系

11.2.2 在 11.2.1 的 Observation Signal Contract 基础上定义 Wait-for-change MVP。
它应明确 Wait Result 描述“等待过程如何结束”，Observation Signal 描述“观察到了
什么”。

11.2.2 必须明确：

- Wait-for-change MVP 优先覆盖 `post_action` wait。
- `timeout` / `skipped` / `not_required` 是 wait outcome，不是 signal kind。
- Wait Strategy 只是后续实现方向，不代表能力已实现。
- wait 层不使用 Agent 判断业务成功。
- Agent 式解释留给 11.2.5 evidence-aware Task Result Reporter。
- Page Understanding Agent 不参与 11.2.2。
- M11.3 只作为 M11.2 后的候选决策点，不创建 11.3 目录。

## 与 11.2.3 的关系

11.2.3 在 11.2.2 的 step-level WaitResult 基础上定义 replay-level observation
evidence aggregation。它不重复实现 wait-for-change，也不扩大当前 11.2.2 的 signal
范围。

11.2.3 必须明确：

- WaitResult 是 step-level outcome。
- Replay Observation Evidence 是 replay-level aggregation。
- 11.2.3 只为 11.2.5 Task Result Reporter 准备输入，不接 reporter。
- `has_primary_observation` 不等于任务成功。
- `has_timeout` 不等于应该 retry。
- `network_idle_observed` 只能作为 supporting evidence。
- 不改变 `ReplayResult.status`。
- 不做 recovery / retry / abort。

## 后续 Common Component Runtime Semantics 记忆点

later 11.2.x 应记录并拆分 Common Component Runtime Semantics（常用组件库运行时
语义兼容）。该方向不是 popup support，而是组件库生成的运行时界面片段识别与关联：
在 replay action 后，观察由常用组件库生成或改变的 runtime surface，并尽可能关联到
触发它的 action / element。

11.2.2 当前最小实现不做完整组件库 runtime behavior detection。它仍只做
`url_changed`、`title_changed`、保守 `page_load_finished`，以及作为 supporting
signal only 的 `network_idle_observed`。

后续拆包建议保持现有编号不变：

- 11.2.2：最小 wait_result / wait_strategy。
- 11.2.3：replay-level observation evidence aggregation。
- 11.2.4：realistic scenario catalog / fixture planning。
- later 11.2.x：Common Component Runtime Semantics。
- 11.2.5：Reporter 消费 observation / wait evidence。

## 与 11.2.4 的关系

11.2.4 不直接实现 fixture 页面。它先建立 WebAgentFlow 自建真实网页验证场景库的
开发文档，明确 PC / 移动端页面类型、网络延迟 / 错误场景、simple -> very complex
复杂度分层，以及 Phase 1 单页面 fixture 和 Phase 2 mock backend 的边界。

11.2.4 必须明确：

- 不依赖外部真实网站作为验证依赖。
- Phase 1 可用确定性前端 timer 模拟 delay / loading / error surface，但不把它
  写成真实 network evidence。
- Phase 2 才引入 mock backend，覆盖 HTTP slow response、error status、polling、
  upload / export 和 async job completion。
- 当前 MVP 只支持 `url_changed`、`title_changed`、supporting-only
  `network_idle_observed`、`wait_result` 和 `observation_summary`。
- toast、modal、loading、form validation、list change、mobile picker、component
  runtime surface relation 都是 future expected observation，不得写成已实现。

原则：

- 优先通用 Web 信号：DOM insertion / removal、visibility change、aria-expanded、
  aria-controls、aria-owns、role=listbox / option / menu / dialog / tooltip、
  selected / checked / disabled / active state、bounding rect proximity、action 后
  insertion timing、focus movement、active descendant。
- 组件库 class 只作为 supporting evidence，不能作为唯一依据。
- 兼容方向同时覆盖 Ant Design、Element Plus、Naive UI、Arco Design、TDesign、
  MUI / Material-ish、Bootstrap-style components，以及 Ant Design Mobile、Vant、
  NutUI、Varlet、Ionic、Framework7-style mobile components。
- 不调用 Agent 判断业务成功，不让 LLM 进入 L3 per-step execution loop。

## 验证

只运行：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 3 -type d \( -name 'm12' -o -name '12.*' \) -print
```

预期：

- `git diff --check` 退出码为 0。
- code / package status check 无输出。
- M12 directory check 无输出。
- `git status --short` 只出现这些范围：
  - `docs/iterations/m11/`
  - `docs/testing/scenarios/`
  - `docs/roadmap.md`

## 完成措辞

使用：`11.2.0 文档初始化完成`。

不要写：

- `runtime support implemented`。
- `observation feature complete`。
- `wait-for-change implemented`。
- `result reporter observation integrated`。
- `M12 started`。
