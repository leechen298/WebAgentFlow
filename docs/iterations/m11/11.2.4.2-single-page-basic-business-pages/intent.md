# 意图（Intent）

状态：implementation-ready

## 目标

实现 11.2.4.2 Single-page Basic Business Pages，为 WebAgentFlow 自建 runtime
observation fixture 库提供第一批简单业务页面。

成功状态：

- `/runtime-observation/basic/login` 可打开。
- `/runtime-observation/basic/register` 可打开。
- `/runtime-observation/basic/sms-login` 可打开。
- `/runtime-observation/basic/search` 可打开。
- `/runtime-observation/basic/detail` 可打开。
- `/runtime-observation/basic/settings` 可打开。
- `/runtime-observation/basic/confirm` 可打开。
- `/runtime-observation` shell 中 basic fixture cards 链接到已实现 route。
- 每个 fixture 有 stable heading、trigger、result region、reset control 和 status label。
- 每个 fixture 能 reset 到 deterministic initial state。
- validation-site build 通过。

## 动机

11.2.4.1 已建立 runtime observation fixture shell，但 basic fixture card 仍是 planned
metadata。11.2.4.2 要把第一批 simple business pages 变成可打开、可交互、可 reset
的自建 fixture，为后续 11.2.4.3 / 11.2.4.4 / 11.2.4.5 继续扩展提供样板。

这些 fixtures 不是为了证明当前 wait service 已能识别所有 UI 变化。它们用于稳定制造
真实页面运行时表面：validation message、toast-like status、modal-like confirm、
loading、empty result、disabled / enabled 等，让后续 observation 信号和 E2E
evidence 有可复现的目标。

## 非目标

- 不实现 medium business pages。
- 不实现 complex business pages。
- 不实现 mobile pages。
- 不实现 mock backend 或真实 HTTP delay。
- 不新增 observation signal，不修改 wait service。
- 不接 Task Result Reporter。
- 不做 recovery / retry / abort。
- 不调用 `verify-scenario` / autonomous run。
