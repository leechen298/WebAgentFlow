# 10.1.1 · Autonomous use-case catalog

## 目标

在 `/exploration/autonomous` workbench 之前新增一个“自主探索用例”
列表页，让操作员和外部执行者能先看到当前仓库里 authored specs 的
全部可跑场景，再一键带参数进入 workbench。

状态：可执行。本需求是 `10.1` LearnedPath persistence 后插入的辅助
入口，不改变 autonomous engine。

## 动机

- 当前 console 已有 workbench 和 run history，但缺少“当前有哪些用例
  可以跑”的入口。执行者只能知道某个 URL 后再进 workbench，不利于
  外包拆单和回归执行。
- 后端已经有 `GET /exploration/specs`，返回 `spec_id`、
  `url_pattern`、`description`、`scenarios`、`inputs`、
  `selections`、期望 verdict。第一版可以纯前端复用，不需要扩展
  engine。
- Phase 10 后续要做 replay / drift / popup controls。先把用例目录
  补上，可以让每个后续迭代都有清晰的人工入口和回归入口。

## 边界（本轮不做）

- 不改 autonomous engine，不改 `run_autonomous_exploration`。
- 不调用 `POST /exploration/autonomous-run` 或 stream 接口；本轮只
  做列表和 deep link。
- 不新增 Agent、phase、loop，也不改变 `pass_gate` / Supervisor
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
4. validation-site origin 可配置；默认本地值为
   `http://localhost:5175`。
5. 页面有 loading / error / empty 状态，不因 API 不可用导致白屏。
6. i18n 至少补齐 zh / en / ja 的导航和页面文案，现有 i18n 测试不
   失败。
7. 验证不触发真实 autonomous run；只验证页面渲染、参数跳转和构建 /
   测试。
