# 契约（Contract）

状态：draft_docs（待评审，未开始执行）

## 概念 / 边界契约

### Closed-loop Evaluation

Closed-loop Evaluation 是对真实产品入口的可审计验证，不是新的 runtime 能力。P0
闭环必须从 `wagent chat` 进入，经过 Conversation API、Interactive Chat Runtime、
learning service、replay service 和 TaskResultReporter。

允许使用只读 API 查询会话、事件、history 和 LearnedPath 详情来取证；不允许把直接
调用 replay API 的结果当作 `wagent chat` 闭环通过。

### External Test Operator

Codex / AI 在本包中只能作为外部测试操作员：

- 可以启动本地服务。
- 可以运行 `wagent chat`。
- 可以输入用户消息。
- 可以查询产品 API 的只读 history / events / LearnedPath 详情。
- 可以整理命令输出和日志。

Codex / AI 不得假装是内部 Task Result Reporter、Supervisor Agent、Task Path Planner
或其他 WebAgentFlow 内部 Agent。

### Unique Item Names

本包测试名必须唯一，防止历史 DOM、toast、日志或旧数据造成假阳性：

```text
learn_item_name = 测试项目A-${timestamp}
execute_item_name = 测试项目B-${timestamp}
```

`execute_item_name` 是最终 evidence target；`learn_item_name` 只能用于学习阶段，不得在执行阶段
被 replay 复读。

## 状态 / 结果契约

本包评估结果使用独立的 evaluation status，不改变 TaskResultReporter 原生 outcome。

| evaluation_status | 含义 |
|---|---|
| `pass` | 所有 required gates 通过，Reporter outcome 为 `verified`，且可证明 replay 填入 B |
| `fail` | 闭环完成到执行阶段但结果不满足 required gates，例如填入 A、evidence missing、Reporter 不 verified |
| `blocked` | 环境、服务、依赖、数据库或前置实现缺失导致闭环无法执行 |
| `unverified` | 执行过部分步骤，但证据不足以判断 pass / fail |

`pass` 必须同时满足：

```text
wagent chat session_id exists
learn A completed
LearnedPath has value_slot=item_name
execute B branch invoked replay
replay effective value is B
item-list evidence target is B
execution_evidence has dom_text_present verified for B
TaskResultReporter outcome is verified
final WAgent response confirms B with evidence wording
```

只满足单元测试、mock replay、API replay 或人工页面观察，不得标记 `pass`。

## Schema / API 契约

本包不新增 schema、API、DB migration 或 CLI command。

允许读取这些已有产品表面：

| Surface | 用途 |
|---|---|
| `wagent chat` | 唯一闭环入口 |
| `GET /conversation/sessions/{session_id}` | 读取 session metadata |
| `GET /conversation/sessions/{session_id}/events` | 读取 runtime event payload |
| `GET /conversation/sessions/{session_id}/history` | 读取 message / event 聚合 history |
| `GET /exploration/learned-paths?page_template=/items` | 查找本轮 LearnedPath |
| `GET /exploration/learned-paths/{path_id}` | 检查 actions JSON 中的 `value_slot=item_name` |

如果实现时需要增加只读 debug endpoint 或 CLI flag，必须先更新本包 contract；默认不新增。

## Evidence / Observation 契约

### 必须记录的证据

| Evidence | Required | 说明 |
|---|---:|---|
| `wagent chat` command / transcript | Yes | 必须包含用户输入和 WAgent 回复 |
| session id | Yes | CLI 创建会话时输出 |
| learn item name A | Yes | 必须唯一 |
| execute item name B | Yes | 必须唯一 |
| LearnedPath id | Yes | 从 event / history / API 中取得 |
| LearnedPath `value_slot=item_name` | Yes | 证明 path 可参数化 |
| replay step effective value | Yes | 证明执行填入 B，不复读 A |
| execution evidence | Yes | 必须有 `dom_text_present verified` for B |
| Reporter outcome | Yes | 必须是 `verified` 才能 pass |
| final WAgent response | Yes | 必须是 evidence-based 成功话术 |
| 未运行项 | Yes | 例如 `verify-scenario`、autonomous run |

### DOM evidence contract

P0 evidence target：

```json
{
  "kind": "dom_text_present",
  "text": "测试项目B-${timestamp}",
  "source_slot": "item_name",
  "selector": "[data-testid='item-list']"
}
```

`ExecutionEvidence.target` 必须等于 `ExecutionEvidenceTarget.text`。

### Reporter contract

闭环 pass 要求 Reporter 原生 outcome 是：

```text
verified
```

不得把 UI wrapper 的 `success`、普通 replay `succeeded` 或 CLI exit 0 当作 Reporter
verified。

## 产品模型 / 范围 / 路线图对齐

- Product model 对齐：本包验证 L3 actual work 的最小 runtime loop；不改变 Agent role。
- Scope boundary 对齐：通过 `wagent chat` 操作 WebAgentFlow 自建 product-test-site，不接真实业务站点。
- Roadmap / milestone 对齐：属于 11.3.5.3 - 11.3.5.6 P0 working loop 收口。
- 是否改变已有 product lifecycle / Agent role / milestone boundary：No。
- 如果是 Yes，必须先更新哪些权威文档：N/A。

## 兼容性契约

- 不改变旧 conversation API。
- 不改变 replay API。
- 不改变 `wagent chat` CLI 参数。
- 不改变 TaskResultReporter outcome enum。
- 不改变 LearnedPath DB schema。
- 结果记录文件是新增文档 artifact，不影响 runtime。

## 不变契约

本轮不改变：

- Product lifecycle stages：不变。
- Internal Agent roles：不变。
- Public API contracts：不变。
- Database schema：不变。
- Replay status semantics：不变。
- Reporter / recovery / abort boundaries：Reporter outcome 不变；recovery / abort 不进入本包。

## 非目标

- 不把 TaskPathPlanner 接入单路径 happy path。
- 不新增 `pending_choice`。
- 不新增 failure recovery 菜单。
- 不做 LLM 自主浏览器控制。
- 不运行 autonomous exploration。
- 不把 `localhost:5176` 写成 contract；它只是 product-test-site 本地脚本默认端口示例。

## 未决问题

- 执行本包时是否采用 `--headless`：默认建议用 `--headless` 保持可重复；如需人工观察，可以额外记录 visible run，但不能替代 required evidence。
- 是否新增自动化 shell helper：默认不新增；如果手动命令重复且易错，可先在本包设计评审后补充最小 helper 设计。
