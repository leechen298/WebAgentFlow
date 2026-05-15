# 意图（Intent）

状态：documentation generated; implementation not started

## 目标

规划 WebAgentFlow 自建真实网页验证场景库，为后续 validation-site fixture 页面、
mock backend 和 E2E 证据建设提供设计输入。

## 动机

11.2.2 和 11.2.3 已经形成最小观察链路：

```text
Replay action
-> wait_result
-> observation_summary
```

但这些能力仍主要通过 service / mock tests 验证。WebAgentFlow 后续需要一套可控、
可复现、可 reset 的真实网页场景库，覆盖 PC / 移动端页面、常见组件交互、网络慢响应、
错误响应和复杂运行时 surface。

线上网站不适合作为基础验证依赖，因为：

- 结构不可控。
- 登录 / 权限 / 风控不可控。
- 网络状态不可复现。
- 难以稳定制造 timeout、loading、partial refresh、same-url reload 或组件库 surface。
- 难以形成可审查的 deterministic evidence。

## 边界 / 非目标

- 本轮只生成开发文档，不开发 fixture 页面。
- 不写前端源码。
- 不写后端源码。
- 不新增测试代码。
- 不运行 E2E。
- 不运行 `verify-scenario` 或 autonomous run。
- 不依赖外部真实网站。
- 不接 Task Result Reporter。
- 不做 M12 recovery / retry / abort / user takeover。
- 不实现 Common Component Runtime Semantics resolver。
- 不读取或保存 raw HTML。

## 成功标准

- 新增完整 11.2.4 文档包。
- PC / 移动端页面类型被系统纳入 scenario catalog。
- 网络延迟、服务端错误、UI 错误 surface、上传 / 导出失败被纳入规划。
- simple / medium / complex / very_complex 按业务页面复杂度分层清楚。
- 11.2.4.1 - 11.2.4.4 单页面 fixture 与 11.2.4.5 mock backend 边界清楚。
- runtime behavior / interaction pattern 不作为页面业务复杂度分类依据。
- 当前 MVP 支持信号和未来 expected observation 明确区分。
- 后续实现者可以根据本文档拆出 11.2.4.x 实现包。
