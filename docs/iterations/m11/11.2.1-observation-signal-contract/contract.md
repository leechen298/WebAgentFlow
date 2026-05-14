# 观察信号契约（Observation Signal Contract）

状态：文档级 contract proposal

本文档定义 M11.2 运行时观察信号的推荐 contract。它不是已实现 schema，不创建
Python / TypeScript 类型，不修改 API，也不修改数据库结构。

## 定义

Observation Signal 是 replay/runtime 观察层产生的结构化记录，用于描述页面运行时
发生的可观察变化。

它用于回答：

- 页面发生了什么？
- 这个变化来自哪里？
- 这个变化和哪个 replay action / step 有关？
- 它是 post-action observation 还是 passive runtime observation？
- 它是否可能作为 result reporter 的 evidence？

它不是：

- recovery plan。
- retry decision。
- abort decision。
- user takeover request。
- LLM reasoning。
- raw HTML dump。
- 最终 result report。

## Signal 类型（Signal Kind）

11.2.1 定义以下文档级 signal kind：

```text
url_changed
title_changed
text_appeared
text_disappeared
element_appeared
element_disappeared
element_enabled
element_disabled
modal_opened
modal_closed
toast_shown
loading_started
loading_finished
page_load_started
page_load_finished
list_changed
form_validation_message
network_idle_observed
spa_content_changed
passive_dom_mutation
server_push_update
```

这些 kind 是后续 11.2.x 的共同语言，不代表 runtime observation 已经实现。

### 页面加载与页面内 Loading UI 的区别

`page_load_started` / `page_load_finished` 描述浏览器级页面加载、导航、完整刷新
或 document reload。它可以覆盖 URL 变化，也可以覆盖 same-url reload。

`loading_started` / `loading_finished` 描述页面内可见 loading UI，例如 spinner、
skeleton、button loading 或局部区域 loading。

两组 signal 不能混用：

- 表单提交导致 document reload：使用 `page_load_started` /
  `page_load_finished`。
- 表格区域显示 spinner 后刷新列表：使用 `loading_started` /
  `loading_finished`，并可配合 `list_changed`。

`page_load_started` / `page_load_finished` 可以属于 `post_action` 或
`passive_runtime` scope。若由当前 replay action 触发，标记为 `post_action`；
若由页面自身逻辑、自动刷新、服务端状态变化或权限状态变化触发，标记为
`passive_runtime`。

Timeout / not-observed outcome 不作为 11.2.1 的 signal kind。它们属于后续
wait-for-change result 设计。

## Signal 范围（Signal Scope）

### post_action

`post_action` 表示用户或 replay action 后短时间内产生的变化。

示例：

- click Submit -> `toast_shown`。
- click Save -> `page_load_started` / `page_load_finished`。
- fill required fields -> `element_enabled`。
- click Search -> `loading_started` / `loading_finished` / `list_changed`。

### passive_runtime

`passive_runtime` 表示非当前 action 直接触发的页面变化。

示例：

- polling 自动刷新列表 -> `list_changed`。
- WebSocket 推送消息 -> `server_push_update`。
- 后台任务完成后页面自动 reload -> `page_load_started` / `page_load_finished`。
- 广告、计时器、个性化脚本改变 DOM -> `passive_dom_mutation`。

## 推荐字段

下表是文档级字段 proposal，不是已实现 schema。不要求每个 signal 都具备所有字段。

| 字段 | 含义 | 边界 |
|---|---|---|
| `signal_id` | signal 的唯一标识。 | 可由后续实现生成；11.2.1 不规定格式。 |
| `kind` | signal kind。 | 必须来自本 contract 定义的 kind 集合。 |
| `scope` | `post_action` 或 `passive_runtime`。 | 不代表 recovery 或 retry 语义。 |
| `observed_at` | 观察发生时间。 | 用于排序和关联，不代表任务完成时间。 |
| `source` | 观察来源。 | 可描述为 replay runtime、DOM observer、page lifecycle、network idle 等后续来源方向；11.2.1 不实现来源。 |
| `trigger` | 触发关系摘要。 | 说明由 action、page logic、server push、polling 等触发；不是因果证明。 |
| `related_action_id` | 关联 replay action。 | 仅当可关联当前 action 时填写。 |
| `related_step_id` | 关联 replay step。 | 仅当可关联当前 route / replay step 时填写。 |
| `target_hint` | 目标区域或元素的人类可读提示。 | 辅助解释，不作为稳定定位。 |
| `selector_hint` | selector 辅助线索。 | 只能作为辅助线索，不承诺稳定，不作为唯一证据。 |
| `text_hint` | 相关文本线索。 | 应短小，只记录相关片段。 |
| `before_summary` | 变化前摘要。 | 简短摘要，不是完整 DOM，不保存 raw HTML。 |
| `after_summary` | 变化后摘要。 | 简短摘要，不是完整 DOM，不保存 raw HTML。 |
| `url_before` | 变化前 URL。 | 可为空；same-url reload 时可能与 `url_after` 相同。 |
| `url_after` | 变化后 URL。 | 可为空；URL 不变不代表没有 page load。 |
| `title_before` | 变化前 title。 | 可为空；title 不变不代表没有变化。 |
| `title_after` | 变化后 title。 | 可为空；title 变化不直接等于任务成功。 |
| `confidence` | 观察可信度。 | 只表示观察本身可信度，不等于任务成功。 |
| `evidence_weight` | reporter 消费参考权重。 | 只是后续消费参考，不直接等于任务成功。 |
| `is_terminal_candidate` | 是否可能成为当前等待的终止信号。 | 只是候选，不代表任务完成。 |
| `is_error_candidate` | 是否可能表示错误状态。 | 只是候选，不自动触发 retry / recovery。 |
| `notes` | 简短备注。 | 不写 LLM reasoning，不写 raw HTML。 |

## 不允许进入 Signal 的内容

Observation Signal 不应包含：

- raw HTML。
- 完整 DOM dump。
- LLM chain-of-thought 或 reasoning。
- recovery plan。
- retry decision。
- abort decision。
- user takeover request。
- 最终 result report。
- 未经证据支持的业务成功结论。

## 与 Replay / Result Evidence 的关系

Observation Signal 可以关联 replay action / step，但它不执行 replay，也不改变
replay contract。

后续 11.2.3 可以把 signal 挂到 replay execution evidence 上；后续 11.2.5 可以让
Task Result Reporter 消费这些 evidence。

11.2.1 不实现这些集成。

## 保守汇报边界（Conservative Reporting）

signal 可以支持保守汇报：

- 观察到 toast 出现。
- 观察到 loading 结束。
- 观察到页面加载 / 刷新开始。
- 观察到页面加载 / 刷新完成。
- 观察到结果列表发生变化。
- 观察到表单校验信息出现。
- 观察到页面内容在 URL 未变化时发生变化。

signal 不能直接推断：

- 任务一定成功。
- 用户目标一定完成。
- 业务状态一定正确。
- 页面刷新完成不等于业务操作一定成功。
- 系统已经恢复。
- 下一步应该 retry。
- 下一步应该 abort。

## 与 11.2.0 Case Catalog 的关系

11.2.1 对齐
[`docs/testing/scenarios/realistic-web-runtime-cases.md`](../../../testing/scenarios/realistic-web-runtime-cases.md)。

Signal kind 应覆盖 11.2.0 中列出的核心场景：

- modal -> `modal_opened` / `modal_closed`。
- toast -> `toast_shown`。
- delayed button -> `element_enabled` / `element_disabled`。
- delayed network result -> `loading_started` / `loading_finished` /
  `list_changed` / `text_appeared`。
- full page reload -> `page_load_started` / `page_load_finished`，可选
  `url_changed` / `title_changed` / `text_appeared` / `network_idle_observed`。
- partial refresh -> `list_changed`。
- SPA content update -> `spa_content_changed`。
- validation error -> `form_validation_message`。
- passive server update -> `server_push_update`。
- passive DOM mutation -> `passive_dom_mutation`。

该对齐不代表上述场景已经实现、自动化或被 E2E 覆盖。
