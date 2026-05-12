# AUI-03 · Validation-site 浏览器冒烟

## 目标

使用 Agent 操作真实浏览器，验证 validation-site fixtures 仍然能渲染 deterministic
E2E、replay 和 authored scenario 依赖的核心控件。

这是 **Agent-operated UI exploratory** 证据，不是 deterministic E2E、
API-only exploratory、static selector smoke，也不是 live autonomous run。

## 范围

目标页面：

- `http://127.0.0.1:5175/login`
- `http://127.0.0.1:5175/users`

主要证据报告：

- `docs/testing/results/2026-05-11-validation-site-browser-smoke.md`

## 前置条件

执行浏览器操作前，记录：

```bash
git rev-parse HEAD
git status --short
curl -sS -i http://127.0.0.1:8001/health
curl -sS -I http://127.0.0.1:5175/login
curl -sS -I http://127.0.0.1:5175/users
```

如果 API 或 validation-site 不可访问，相关用例写 `BLOCKED`。不能用 curl、源码阅读、
component test 或 headless E2E 输出替代浏览器可视化证据。

## 允许工具

- Codex Browser panel / in-app browser。
- Claude Code Browser Use / Computer Use。
- 其他具备浏览器操作能力的 Agent。
- Headed Playwright，仅当它作为可视化观察工具使用时。

## 禁止动作

- 不调用 `/exploration/autonomous-runs`。
- 不调用 `/exploration/autonomous-runs/stream`。
- 不 import 或直接运行 autonomous explorer。
- 不使用 `verify-scenario`。
- 不触发 WebAgentFlow 产品侧 LLM provider。
- Codex / Claude Code / 其他 browser-capable Agent 可作为外部测试操作员。
- 不改产品代码、E2E spec、package scripts 或 iteration docs。
- 没有真实浏览器可见证据时，不得写 PASS。

## 用例

### VSB-001 · Login 页面渲染关键控件

目标 URL：

```text
http://127.0.0.1:5175/login
```

操作：

1. 打开 `/login`。
2. 确认页面正常渲染。
3. 确认 username input 可见。
4. 确认 password input 可见。
5. 确认 submit/login button 可见。
6. 确认 error region 行为；如果默认隐藏，需要记录并通过 `VSB-002` 验证。

预期可见结果：

- login 页面可见。
- username input、password input 和 login button 可见。
- 默认隐藏的 error region 行为被说明，而不是假设。

证据要求：

- browser method。
- page URL。
- visible UI observation。
- screenshot、trace、video 或 browser observation excerpt 之一。

### VSB-002 · Login 错误账号密码显示错误提示

目标 URL：

```text
http://127.0.0.1:5175/login
```

操作：

1. 打开 `/login`。
2. 输入 username `wrong`。
3. 输入 password `wrong`。
4. 点击 login submit button。
5. 观察 visible error state。

预期可见结果：

- 页面停留在 failed-login 状态。
- 出现用户可见错误提示。
- 没有触发 autonomous run。

证据要求：

- 输入和点击的浏览器观察。
- 可见 error text。
- 提交后的 current URL。

### VSB-003 · Users 页面渲染搜索控件

目标 URL：

```text
http://127.0.0.1:5175/users
```

操作：

1. 打开 `/users`。
2. 确认 search area 可见。
3. 确认 name search input 可见。
4. 确认 status control 可见。
5. 确认 search button 可见。
6. 确认 result table 或 empty state 可见。

预期可见结果：

- users 页面正常渲染。
- name、status、search controls 可见。
- result table 或 empty state 可见。

证据要求：

- browser method。
- page URL。
- controls 和 result area 的可见观察。
- screenshot、trace、video 或 browser observation excerpt 之一。

### VSB-004 · Users 按 name 搜索会更新结果区域

目标 URL：

```text
http://127.0.0.1:5175/users
```

操作：

1. 打开 `/users`。
2. 在 name search input 输入 `alice`。
3. 点击 search。
4. 观察 result area。

预期可见结果：

- 页面没有崩溃。
- URL 或 visible result area 反映搜索。
- 如果匹配 seeded user 可见，记录 row text。
- 如果没有匹配 seeded user，记录 empty state。

证据要求：

- 输入和点击的浏览器观察。
- 搜索后的 current URL。
- 可见 result count、row text 或 empty-state text。

### VSB-005 · Users 无匹配搜索显示 empty state

目标 URL：

```text
http://127.0.0.1:5175/users
```

操作：

1. 打开 `/users`。
2. 在 name search input 输入 `zzzz-no-match-9999`。
3. 点击 search。
4. 观察 result area。

预期可见结果：

- 页面没有崩溃。
- result area 给出明确 no-match feedback，例如 empty state 或 no-results message。

证据要求：

- 输入和点击的浏览器观察。
- 搜索后的 current URL。
- 可见 no-match result count 或 empty-state text。

## 报告模板

```md
# Validation-site 浏览器冒烟报告

日期：
Commit:
工作区：
工具：
范围：

## 前置条件

- API health:
- validation-site /login:
- validation-site /users:

## 摘要

| 用例 | 状态 | 证据 |
| --- | --- | --- |

## 用例结果

### VSB-001 · Login 页面渲染关键控件

- 状态：
- 方法：
- 页面 URL：
- 可见操作：
- 可见观察：
- 证据：
- 备注：
- 后续：

## 边界

- Autonomous endpoints called:
- `/exploration/autonomous-runs` called:
- `/exploration/autonomous-runs/stream` called:
- Autonomous explorer imported or run directly:
- verify-scenario used:
- 产品侧 LLM provider used:
- Product code modified:
- E2E spec modified:
- Package scripts modified:
```

## 当前证据

最新记录：

- `docs/testing/results/2026-05-11-validation-site-browser-smoke.md`

该报告记录了 Browser Use / in-app browser 对 `VSB-001` 到 `VSB-005` 的 PASS
证据，且未调用 autonomous endpoint，未触发产品侧 LLM provider。
