# 意图（Intent）

状态：implementation complete, review pending

## 目标

实现 11.2.4.2 Single-page Basic Business Pages，将此前被人工 review 否决的
toy-like basic fixtures 重做为 production-like frontend-local fixtures。

成功状态：

- `fixture-designs/` 下存在 7 个页面级设计文档。
- 7 个 `/runtime-observation/basic/*` routes 按页面级设计文档实现。
- 每个页面设计都定义 happy path、本地错误状态、loading / pending、success、reset、
  stable anchors 和 deferred states。
- contract / technical-design / test-plan / plan / review 均记录实现与验证边界。

## 动机

11.2.4.2 的第一版实现虽然提供了 7 个 `/runtime-observation/basic/*` routes，并通过 build 级验证，
但页面业务密度不足。它们主要是输入、按钮、结果区和 reset，不足以代表真实业务页面。

WebAgentFlow 自建 fixture 的目标不是制造最小 UI 片段，而是制造可复现、可观察的真实页面运行时表面。
Basic business page 的业务流程可以简单，但页面本身不能是 toy demo。

## Redesign Principle

```text
business-simple, production-like
not UI-minimal
```

Basic pages must have:

- clear primary business goal。
- complete page anatomy。
- main flow。
- local deterministic error / validation flow。
- loading / pending state。
- visible success state。
- secondary action or distractor。
- deterministic reset。
- stable anchors。

## Error Boundary

11.2.4.2 只做 frontend-local deterministic 状态：

- required field validation。
- invalid credentials。
- password mismatch。
- invalid SMS code。
- empty result。
- local not found。
- settings warning。
- confirm cancel。

弱网、断网、HTTP status code、真实 server validation、backend conflict 进入 11.2.4.5。
recovery / retry / abort / user takeover 进入 M12。

## 非目标

- 不新增测试代码。
- 不实现 mock backend 或真实 HTTP delay。
- 不新增 observation signal，不修改 wait service。
- 不接 Task Result Reporter。
- 不做 recovery / retry / abort。
- 不调用 `verify-scenario` / autonomous run。
