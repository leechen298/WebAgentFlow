# 实施计划

状态：Draft only，不可直接外包执行。执行前先读完 `10.1` /
`10.1.1` 的 review 与当前代码，再把本计划收敛成可执行版本。

## 预期触及的模块

- LearnedPath repo / schema：读取可 replay 候选。
- `page_signature.py`：复用或扩展当前页面 signature / drift 对比。
- execution runtime：按 LearnedPath actions 执行步骤。
- exploration router：新增 replay 入口或挂到现有 exploration 前缀。
- console：展示 replay 结果、drift 原因和来源 LearnedPath。

## 粗粒度步骤

1. 定义 replay 请求 / 响应契约：输入 URL、scenario、可选
   LearnedPath id；输出 replay status、drift summary、step log。
2. 实现候选选择：优先 `confirmed`，再 `provisional`；忽略
   `deprecated`，`flaky` 只作为调试候选。
3. 实现 drift check：比较 path template、query signature、
   dom fingerprint 和 action target 可定位性。
4. 接入 execution runtime：只执行已存 actions，不调用 autonomous
   planner 生成新动作。
5. 补 API / service / repo 单测，必要时补 console 展示测试。

## 执行前需要确认

- replay 是否作为新的 API 能力暴露，还是先只在 console detail 页做
  内部按钮。
- drift status 的最小枚举集合。
- action schema 是否需要从 `learned_paths.actions` 抽成稳定类型。

## 验证方向

- 单测覆盖 candidate selection、drift 分类、不可定位 action。
- 不通过 curl / fetch 直接跑 autonomous-run。
- 真实运行如不可避免，只走 `verify-scenario` skill。
