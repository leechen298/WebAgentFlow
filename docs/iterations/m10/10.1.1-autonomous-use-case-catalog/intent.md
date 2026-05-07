# 10.1.1 · Autonomous use-case catalog

## 执行前必读

接手本目录开发前，请先按顺序阅读：

1. `AGENTS.md`
2. `docs/product-model.md`
3. `docs/iterations/m10/m10-plan.md`
4. 本目录的 `intent.md`
5. 本目录的 `plan.md`

硬边界：只执行 M10 `10.1.1`；不做 `10.2+`；不改 autonomous
engine。自动化验证不得替用户触发真实
`/exploration/autonomous-run`；若实现批量运行 UI，只能复用现有
console client，并用 mock / 单测验证。

## 目标

在 `/exploration/autonomous` workbench 之前新增一个“自主探索用例”
列表页，让操作员能先看到当前仓库里 authored specs 的
全部可跑场景，再一键带参数进入 workbench。增量目标：支持勾选多个
scenario、全选可运行 scenario，并从目录页批量运行选中的用例。

状态：可执行。本需求是 `10.1` LearnedPath persistence 后插入的辅助
入口，不改变 autonomous engine。

## 动机

- 当前 console 已有 workbench 和 run history，但缺少“当前有哪些用例
  可以跑”的入口。执行者只能知道某个 URL 后再进 workbench，不利于
  拆分执行和回归执行。
- 后端已经有 `GET /exploration/specs`，返回 `spec_id`、
  `url_pattern`、`description`、`scenarios`、`inputs`、
  `selections`、期望 verdict。第一版可以纯前端复用，不需要扩展
  engine。
- M10 后续要做 replay / drift / popup controls。先把用例目录
  补上，可以让每个后续迭代都有清晰的人工入口和回归入口。

## 边界（本轮不做）

- 不改 autonomous engine，不改 `run_autonomous_exploration`。
- 不改 `POST /exploration/autonomous-run` 或 stream 接口；批量运行
  只允许复用现有 `apps/console/src/api/autonomousStream.ts` client。
- 自动化验证不触发真实 run；批量运行行为用 mock 的
  `streamAutonomousRun` 覆盖，真实运行只由用户在 console 页面点击。
- 不新增 Agent、生命周期阶段、loop，也不改变 `pass_gate` / Supervisor
  判定逻辑。
- 不替代历史页：history 仍然展示 run 结果；本页只展示“可启动的
  authored use cases”。
- 不把 validation-site 的 fixture catalogue 复制到 console；以
  `/exploration/specs` 为唯一数据源。

## 成功标准

1. console 侧新增路由 `/exploration/autonomous/cases`，侧边栏位于
   “自主探索”和“自主探索历史”之间。
2. 页面从 `listSpecs()` 加载 authored specs，能展示每个 spec 下的
   scenarios、输入值、选择值、期望 verdict 信息。
3. 每个 scenario 都能跳转到 `/exploration/autonomous`，并携带：
   - `url=<validation-site-origin + spec.url_pattern>`
   - `spec_id=<spec.spec_id>`
   - `scenario=<scenario.key>`
   - `goal=<scenario.description 或 spec.description>`
4. scenario 行支持勾选；缺少 `url_pattern` 的 scenario 不可勾选，
   并保留 tooltip 说明。
5. 页面提供“全选可运行用例 / 清空选择”控制；全选只选择当前 specs
   中能构造 URL 的 scenario。
6. 页面提供“批量运行选中用例”按钮；无选择或正在运行时禁用。
7. 批量运行复用 `streamAutonomousRun`，为每个选中 scenario 构造：
   - `url=<validation-site-origin + spec.url_pattern>`
   - `goal=<scenario.description 或 spec.description>`
   - `fill_values=<scenario.inputs>`
   - `toggle_values=<scenario.selections>`
   - `headless=true`
   - `spec_id=<spec.spec_id>`
   - `scenario=<scenario.key>`
8. 批量运行要展示每个选中 scenario 的状态：queued / running /
   completed / failed / aborted；可中止仍在运行的任务。
9. 默认并发上限为 3，避免一次性打开过多 SSE 连接；全量选择时按队列
   推进。
10. validation-site origin 可配置；默认本地值为
   `http://localhost:5175`。
11. 页面有 loading / error / empty 状态，不因 API 不可用导致白屏。
12. i18n 至少补齐 zh / en / ja 的导航和页面文案，现有 i18n 测试不
   失败。
13. 自动验证不触发真实 autonomous run；只用 mock 验证批量 payload、
   队列状态、全选/清空、abort 行为，以及页面渲染、参数跳转和构建 /
   测试。
