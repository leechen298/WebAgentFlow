# 11.2.1 · 观察信号契约（Observation Signal Contract）

状态：文档生成完成

## 目标

11.2.1 定义运行时观察信号的文档级 contract。它回答：WebAgentFlow 在 replay /
runtime 观察层看到页面变化时，应该用什么结构化语言记录“我看见了什么”。

本包只定义 contract，不实现 runtime observation。

## 背景

11.2.0 已经完成 M11.2 文档初始化，并建立 realistic web runtime case catalog。
11.2.1 在此基础上定义 Observation Signal，为后续包提供稳定语义：

- 11.2.2 基于 signal contract 做 wait-for-change MVP。
- 11.2.3 将 observation 接入 replay execution。
- 11.2.5 将 observation evidence 接入 Task Result Reporter。

## Observation Signal 是什么

Observation Signal 是 replay/runtime 观察层产生的结构化记录，用于描述页面运行时
发生的可观察变化。

它可以记录：

- 页面 URL 或 title 变化。
- 文本、元素、modal、toast、loading、列表、校验信息变化。
- 浏览器级 page load / document reload 生命周期。
- SPA 内容变化。
- passive DOM mutation 或 server push update。

它不是：

- recovery plan。
- retry decision。
- abort decision。
- user takeover request。
- LLM reasoning。
- raw HTML dump。
- 最终 result report。

## 核心 contract 文档

本包的核心 contract 在
[`contract.md`](./contract.md)。

`contract.md` 定义：

- signal kind。
- signal scope。
- 推荐字段。
- 字段边界。
- page load 与页面内 loading 的区别。
- conservative reporting 边界。
- 与 11.2.0 case catalog 的对齐关系。

## 硬边界

- 不写代码。
- 不新增测试代码。
- 不运行 E2E。
- 不修改 public API。
- 不修改 database schema。
- 不修改 TypeScript / Python schema 文件。
- 不修改 replay execution。
- 不修改 Task Result Reporter。
- 不实现 wait-for-change。
- 不实现 page-load waiting。
- 不实现 mutation observer。
- 不实现 network observer。
- 不实现 WebSocket / SSE 观察。
- 不做 recovery / retry / abort / user interruption / takeover。
- 不读取或保存 raw HTML。
- 不创建 M12 / 12.x 目录。
- 不创建 v0.2 分支。
