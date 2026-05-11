# WebAgentFlow Full Test Matrix

## Status

本文件是测试规划文档，不是执行报告。

来源：MiMo 生成的 Full Test Matrix Draft，经 Codex review 后收敛。本文件不声明
任何测试已经完成，也不把 MiMo 草案中的全部 207 个 case 原样落成永久测试计划。

本文件的职责是：

- 归一化测试证据类型。
- 标出 MiMo draft 中过期、错误分类、越界或优先级不准的内容。
- 为当前 M11 进度给出第一批真正值得落地的测试方向。
- 指向各产品能力域的长期测试矩阵。

详细 case 只有在对应能力域进入实施时再展开。没有命令、测试输出、浏览器截图、
trace 或报告证据时，不能把 case 写成已通过。

## Implementation Policy

本矩阵是测试地图，不是立即开工清单。

- 本矩阵不授权一次性实现所有 case。
- 新增测试必须按能力域、当前里程碑和风险拆成 scoped task。
- 已有测试必须标记为 `existing` 或 `keep-running`，不能重复当成新增实现任务。
- `keep-running` 表示已有基线需要持续运行和维护，只有发现缺口时才新增 case。
- Live smoke 只手动触发，不进常规 CI。
- Deterministic E2E 不依赖 LLM，不调用 autonomous run。
- 详细 case 表只在对应能力域进入施工时展开，不把 MiMo draft 全量复制为永久计划。
- 如果任务目标专指 deterministic E2E，请使用 `e2e/README.md`。
- 如果任务目标专指 Agent-operated UI exploratory，请使用
  `agent-operated-ui/README.md`。
- `e2e-codex-testing-track.md` 只保留为历史 / 过渡索引，不要从本矩阵或旧索引
  直接推导一次性施工清单。

## Evidence Types

| Evidence type | 说明 | CI | 边界 |
| --- | --- | --- | --- |
| Unit | 纯函数、状态机、parser、静态 helper 测试 | yes | 不做 IO，不依赖浏览器或 LLM |
| Repo/API integration | DB repo 或 HTTP API contract 测试 | yes | 需要测试 DB 或 API test client，但不触发 autonomous run |
| Component | Vue component / frontend utility tests | yes | 使用 mock/stub，不等同真实浏览器 E2E |
| Deterministic E2E | Playwright Test 对稳定 seed 数据和固定 app stack 的回归 | yes | 不依赖 LLM，不调用 autonomous run，可重复、可 seed |
| API exploratory | curl / Python / Node 直接调用 API 并保留命令证据 | no | 不能冒充 Agent-operated UI exploratory |
| Agent-operated UI exploratory | Codex / Claude Code / other browser-capable agents、headed Playwright、截图、trace 或可见页面观察 | no | 必须实际观察 UI，不能只读代码或只调 API |
| Live smoke | `verify-scenario` skill 触发的 live autonomous run | no | 需要 LLM / Supervisor verdict / run_id，只能人工或 release smoke |

归类规则：

- 只要 case 需要 LLM provider、`verify-scenario`、live autonomous run 或 Supervisor
  verdict，就必须归为 `Live smoke / manual release smoke`，不能归为
  deterministic E2E，也不能写 CI yes。
- Deterministic E2E 必须不依赖 LLM、不调用
  `/exploration/autonomous-runs` 或 `/exploration/autonomous-runs/stream`。
- API exploratory 和 Agent-operated UI exploratory 不能互相替代。
- Agent-operated UI exploratory 必须保留 browser panel / headed browser /
  screenshot / trace / video / visible observation 证据。
- Full matrix 不管理具体浏览器操作工具细节；具体规则见
  `agent-operated-ui/README.md`。

## Case Status Legend

| Status | 含义 |
| --- | --- |
| existing | 当前代码库已经有对应测试或已记录结果证据 |
| keep-running | 已有基线，当前任务是持续运行和维护，不是新增实现 |
| partial | 有部分覆盖，但缺少关键边界或证据类型 |
| gap | 确认存在测试缺口，建议补 |
| proposed | 合理建议，但需要等对应能力进入施工 |
| deferred | 有价值但不是当前批次，先放后续 backlog |
| reject | 分类错误、范围越界、重复或不应落地 |

## Test File Inventory Snapshot

MiMo draft 中的 “Current Coverage Snapshot” 不能作为 coverage。它只能叫
Test File Inventory Snapshot。

如果未来保留这类数字，必须由命令生成：

```bash
find apps/api/tests -name 'test_*.py' | wc -l
find apps/console/src/__tests__ -name '*.test.*' | wc -l
find apps/cli/tests -name 'test_*.py' | wc -l
find apps/e2e/tests -name '*.spec.ts' | wc -l
```

在没有命令、commit 和退出码证据前，这类数字只能标为 `unverified snapshot`。
它不能代表覆盖率百分比，不能代表测试已通过，也不能替代测试结果文档。

## Domain Summary

### 1. autonomous-exploration

Current status：

- L1 autonomous exploration 是已有核心能力，但当前 M11 下一步不是扩展 live run。
- `verify-scenario` 是唯一允许 AI coding agent 触发 live autonomous run 的路径。
- MiMo draft 中把 `AE-D-*` live run 标成 `Det E2E / CI yes` 是错误分类。

Key risks：

- pass gate 是最关键决策点。
- Supervisor fallback、partial parse、scorecard 降级必须保持可解释。
- Workbench/history UI 需要避免把 unverified 当 pass。
- SSE / live run 相关测试如果触发真实探索，就一定不是常规 CI deterministic E2E。

Existing coverage summary：

- pass gate、Supervisor observation parsing、page verification、action planner、page
  analyzer、frontend verdict display 等已有单元/组件覆盖。
- live autonomous run 的证据必须来自 `verify-scenario` skill 和 run_id，不由本矩阵
  宣称完成。

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| AE pass_gate invariant audit | partial | 可后续核对是否还有缺口，但不是当前第一批 |
| Workbench/history 基础 component smoke | partial | 适合组件测试，不需要 live run |
| verify-scenario release smoke | proposed | 只做 manual release smoke，CI no |
| 全量 AE 60 case 立即落地 | deferred | 范围太大，会偏离当前 M11 runtime 测试重点 |

Recommended next cases：

- 保留 AE P0 invariant 作为 backlog：pass_gate、observation parsing、
  verify-scenario boundary、Workbench/history 基础 smoke。
- 把所有 LLM / verify-scenario / live autonomous run case 统一标为 Live smoke，
  manual only，CI no。

### 2. learned-path-catalog

Current status：

- M10 LearnedPath persistence、catalog、trust 操作、run review 分离已经完成。
- M10.2 replay E2E 已建立，replay 域另有长期矩阵。

Key risks：

- LearnedPath trust state machine 与 run review 互相独立。
- dedup / source_run 关系必须保持稳定。
- catalog UI 的 trust 操作和 replay 入口不能互相污染。

Existing coverage summary：

- repo/API/component 已有覆盖。
- replay E2E 已覆盖 catalog drawer happy path。

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| trust / run-review separation smoke | proposed | 第一批 P1，保护 M10.1.3 设计不变量 |
| catalog trust tag visual exploratory | deferred | 可做视觉探索，不进常规 CI |
| 通过 live autonomous run 生成 LearnedPath 再校验 ingestion | deferred | 属于 live smoke，不是 deterministic E2E |

Recommended next cases：

- 用 API/component smoke 确认 run review accept/reject 不改变 path trust。
- 用 catalog component smoke 确认 trust 操作和 replay 区块互不影响。

### 3. replay

Current status：

- 当前已建立的确定性 E2E 域。
- `apps/e2e/tests/replay/` 已覆盖 9 个 M10.2 replay case。
- 结果证据见 `docs/testing/results/2026-05-08-replay-e2e-first-run.md`、
  replay API exploratory 报告和 replay Agent-operated UI exploratory 报告。

Key risks：

- drift precheck 顺序和状态必须稳定。
- `signature_changed` 是 warning，不应阻断可执行 replay。
- `unsupported_action` 必须结构化返回，不能 500。
- replay 使用后端 Playwright，但不是 autonomous run。

Existing coverage summary：

- deterministic E2E：happy path、observational、catalog UI happy path、
  page_mismatch、target_missing、unsupported_action、flaky warning、
  deprecated 422、signature_changed。
- API exploratory：已有证据型报告。

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| replay deterministic E2E 保持 | existing | 继续作为核心回归轨道 |
| failed action caused by real DOM obstruction | deferred | 等场景稳定后再补 |
| replay audit persistence | deferred | 仅当未来实现 replay audit 时补 |
| live autonomous learning -> replay smoke | deferred | live smoke，不进常规 CI |

Recommended next cases：

- 保持 `pnpm run test:e2e` 作为 replay 回归轨道。
- 后续扩 action type 时在 replay 域追加对应 E2E，不扩大到 M11 conversation。

### 4. conversation

Current status：

- MiMo draft 中 “conversation is currently pure-function only” 已过期，应 reject。
- 当前已完成：
  - 11.0.1 domain contract。
  - 11.0.2 DB-backed session store。
  - 11.0.3 Conversation API。
  - 11.0.4 `wagent conversation` runtime CLI。
  - 11.0.5 service-only Orchestrator Dispatcher。
  - 11.0.6 Explicit Replay Command Hook。
  - 11.0.7 Conversation runtime E2E smoke。
- 下一开发阶段：M11.1 Task-to-Path 仍是 future。

Key risks：

- Orchestrator dispatcher 和 explicit replay hook 已有 baseline；下一风险点是
  M11.1 task-to-path 进入前不要破坏 explicit replay 的确定性边界。
- CLI/API 已经成为用户入口和后续 orchestrator 的外部 contract，需要 smoke 保护。
- 不能让 LLM 逐步控制浏览器，不能调用 autonomous run。

Existing coverage summary：

- CV-U：domain parser/state tests 已有。
- CV-R：repo/store tests 已有。
- CV-API：Conversation API tests 已有。
- CV-CLI：`wagent conversation` CLI tests 已有。
- CV-O：service-only Orchestrator Dispatcher tests 已有。
- CV-RH：explicit replay hook tests 已有。
- CV-E2E：conversation runtime E2E smoke 已有。

Recommended grouping：

| Group | 范围 | Status |
| --- | --- | --- |
| CV-U | domain parser / state transition | existing |
| CV-R | repo / session store | existing |
| CV-API | conversation HTTP API | existing |
| CV-CLI | `wagent conversation` | existing |
| CV-O | service-only Orchestrator Dispatcher | existing / keep-running |
| CV-RH | explicit replay command hook | existing / keep-running |
| CV-E2E | conversation runtime smoke | existing / keep-running |

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| CV-O dispatcher baseline | existing / keep-running | 11.0.5 已完成 service-only baseline，持续运行 |
| CV-API + CV-CLI smoke | keep-running | 已有测试，除非发现缺口才新增 |
| CV-RH explicit replay hook | existing / keep-running | 11.0.6 已完成，持续运行 |
| CV-E2E conversation smoke | existing / keep-running | 11.0.7 已新增 runtime E2E |

Recommended next cases：

- keep-running：Conversation API / CLI / Orchestrator baseline。
- 保留 API + CLI smoke，保护 session create/send/status/transcript/events。
- keep-running：conversation runtime E2E。

### 5. validation-site

Current status：

- validation-site 是 deterministic fixture host。
- 它支撑 replay E2E、page analysis、未来确定性 UI smoke。

Key risks：

- selector / fixture 数据漂移会导致 replay、page analysis 和 E2E 误报。
- login/sessionStorage、users filter 等基础 fixtures 必须稳定。

Existing coverage summary：

- 部分 API、page analyzer、signature helper 已有覆盖。
- replay E2E 间接依赖 `/users` fixture。

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| selector stability smoke | proposed | 可做轻量 unit/API/DOM smoke |
| validation API seed data smoke | proposed | 适合 API integration，不需要浏览器 |
| fixture visual layout checks | deferred | 只做 Agent-operated UI exploratory，不进常规 CI |

Recommended next cases：

- 补最小 selector stability smoke，避免 fixture 漂移破坏 replay。
- 不把 validation-site 页面全量升级成 E2E。

### 6. console-operator-ui

Current status：

- console 是 operator UI。
- 当前已有 history、use cases、catalog、layout、locales 等组件测试。
- replay catalog UI 已进入 deterministic E2E。

Key risks：

- operator 页面对 pass / unverified / fail 的展示不能混淆。
- history/catalog/workbench 入口破坏会影响人工审查和学习资产操作。
- visual correctness 需要 visual exploratory，不应被 API 或 headless E2E 冒充。

Existing coverage summary：

- component coverage 较多。
- replay catalog happy path 有 E2E。
- Workbench/History/Detail 的可视化全链路仍更适合后续重点抽样。

Top gaps：

| Case | Status | 说明 |
| --- | --- | --- |
| Console operator UI 基础 smoke | proposed | 第一批 P1，保护主入口 |
| Workbench visual exploratory | deferred | 必须有可见浏览器证据 |
| 全 console 页面 E2E 化 | reject | 过度 E2E 化，不符合当前策略 |

Recommended next cases：

- 先补 history/catalog/workbench 基础 smoke。
- Agent-operated UI exploratory 只做重点页面和重点状态，不进常规 CI。

## Misclassification Fixes

| MiMo draft 内容 | 处理 | 理由 |
| --- | --- | --- |
| `AE-D-*` login/users live run 标为 `Det E2E / CI yes` | reclassify to Live smoke / CI no | 依赖 LLM、verify-scenario、Supervisor verdict |
| conversation 写成 pure-function only | reject as outdated | 11.0.1-11.0.4 已完成 domain/store/API/CLI |
| Current Coverage Snapshot | rename to Test File Inventory Snapshot | 文件数量不是覆盖率，也不代表测试通过 |
| 原 first batch 回头补 AE/LP/CV 大量旧 case | reject as current first batch | 不贴合当前 M11 runtime 风险 |
| 全量 207 case 一次性落地 | deferred | 范围过大，必须按能力域逐步展开 |
| Agent-operated UI 用 API/headless 证据代替 | reject | 证据类型不匹配 |

## Recommended First Implementation Batch

| Case ID | Work type | Reason | Layer | Priority | CI | Milestone dependency | Evidence required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FIRST-P0-01 CV-O dispatcher baseline | existing baseline / keep-running | 11.0.5 service-only dispatcher 已完成，持续运行 baseline；除非发现缺口才新增 | Unit | P0 | yes | 11.0.5 shipped | pytest output，review.md evidence |
| FIRST-P0-01B CV-RH replay hook baseline | existing baseline / keep-running | 11.0.6 explicit replay hook 已完成，持续运行 baseline | API / integration | P0 | yes | 11.0.6 shipped | pytest output |
| FIRST-P0-01C CV-E2E conversation runtime smoke | existing baseline / keep-running | 11.0.7 已新增 conversation runtime E2E | Deterministic E2E | P0 | yes | 11.0.7 shipped | Playwright output |
| FIRST-P0-01D CV-CLI-E2E conversation CLI runtime smoke | existing baseline / keep-running | 已新增真实 `wagent conversation` subprocess E2E，区别于 mocked CLI tests | Deterministic E2E | P0 | yes | 11.0.7 shipped | Playwright output |
| FIRST-P0-02 Conversation API smoke | existing baseline / keep-running | API 是 CLI 和 orchestrator 的前置 contract；已有 11.0.3 API tests，除非发现缺口才新增 | Repo/API integration | P0 | yes | 11.0.3 shipped | pytest output，HTTP 404/422 覆盖 |
| FIRST-P0-03 Conversation CLI smoke | existing baseline / keep-running | 11.0.4 CLI tests 已存在；当前任务是持续运行，除非发现缺口才新增 | CLI integration | P0 | yes | 11.0.4 shipped | CLI test output，stdout/stderr / exit code evidence |
| FIRST-P0-04 Replay deterministic E2E | existing baseline / keep-running | M10.2 replay 是当前稳定浏览器闭环回归轨道 | Deterministic E2E | P0 | yes, once services are orchestrated | M10.2 shipped | `pnpm run test:e2e` output，seed fixture evidence |
| FIRST-P1-01 LearnedPath trust / run-review separation smoke | evaluate gap before adding | 保护 path trust 与 run review 独立这一设计不变量；先查现有 API/component coverage | API / Component | P1 | yes | M10.1.3 shipped | gap review + API/component test output |
| FIRST-P1-02 Console operator UI basic smoke | proposed, scope before implementation | 保护 history/catalog/workbench 主入口不破；先定具体页面和证据类型 | Component / Agent-operated UI exploratory | P1 | partial: component yes, visual no | M10/M11 current console | component test output；visual 需 screenshot/trace |
| FIRST-MAN-01 verify-scenario live smoke | manual only | release 前人工验证 L1 live loop，不进入常规 CI | Live smoke | Manual | no | release smoke only | `verify-scenario` pass_gate、Supervisor verdict、scorecard、run_id |

## Deferred / Reject Summary

Deferred：

- AE 全量 60 case 展开。
- live autonomous learning -> replay smoke。
- validation-site 全页面 E2E。
- console 全页面 visual exploratory。
- additional conversation E2E variants，等 M11.1 或更多 runtime behavior 进入施工后再定。
- replay DOM obstruction failure，等 fixture 设计稳定后再补。

Reject：

- 把 LLM / verify-scenario / live autonomous run 标成 deterministic E2E。
- 把 LLM-dependent case 标成常规 CI yes。
- 把 headless E2E 当成 Agent-operated UI exploratory。
- 把 MiMo 207 case 原样提交为永久测试计划。
- 把当前 conversation 域描述成 pure-function only。

## Implementation Rules

- 每个能力域的详细 case 只在对应能力进入实施时展开。
- 每个新增 case 必须带 status、evidence type、CI yes/no、依赖里程碑。
- 不通过 `/exploration/autonomous-runs` 或 `/stream` 直接触发 live run。
- 不依赖 LLM provider 的 deterministic tests 才能作为常规 CI 候选。
- 探索式报告写到 `docs/testing/results/`，没有证据不能写 PASS。
