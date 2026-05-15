# 测试计划（Test Plan）

状态：documentation generated; tests not implemented

## 适用条件

11.2.4 涉及 future fixture pages、mock backend、E2E、replay observation 和 AI
外部测试操作员边界，因此必须维护 `test-plan.md`。本轮只规划，不新增测试代码。

## 测试范围（Test Scope）

- Unit：N/A，本轮不写代码。后续 11.2.4.5 mock backend 可补 API unit tests。
- Integration：N/A，本轮不写代码。后续 replay / fixture integration 另开实现包。
- API：N/A，本轮不改 API。后续 mock backend 实现后补。
- Console UI：N/A，本轮不改 Console。
- E2E：规划 future fixture E2E，不在本轮执行。
- Agent / Reporter / Recovery：只定义不调用 Reporter / recovery / abort 的边界。
- Codex / AI External Operator：本轮不进行 live UI smoke。
- Live autonomous run：本轮不运行 `verify-scenario` 或 autonomous run。

不覆盖：

- fixture 页面实现。
- mock backend 实现。
- live UI smoke。
- `verify-scenario`。
- autonomous run。
- Task Result Reporter。
- M12 recovery。
- Common Component Runtime Semantics resolver。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| documentation | PC catalog exists | inspect docs | PC page types covered | Yes | docs-only validation |
| documentation | mobile catalog exists | inspect docs | mobile page types covered | Yes | docs-only validation |
| documentation | complexity ladder | inspect docs | simple / medium / complex / very complex present | Yes | docs-only validation |
| documentation | current vs future observation | inspect docs | MVP signals separated from future signals | Yes | no false implementation claims |
| documentation | network delay and errors | inspect docs | slow response / HTTP errors / upload-export failures covered | Yes | 11.2.4.5 planning |
| future route smoke | each fixture route opens | validation-site route | route loads with stable heading | Yes later | not run in this docs package |
| future route smoke | trigger visible | validation-site page | trigger action visible and stable | Yes later | stable selector required |
| future route smoke | deterministic initial state | validation-site page | reset restores baseline | Yes later | no state bleed |
| future route smoke | deterministic post-action state | click trigger | expected visible result appears | Yes later | timer durations fixed |
| future replay | URL/title change fixture | replay run | current MVP observed | Yes later | current MVP path |
| future replay | toast/modal/loading/list refresh | replay run | current MVP does not falsely claim unsupported signal | Yes later | future signal only |
| future replay | network idle supporting | replay run | supporting evidence only, not primary | Yes later | 11.2.2 invariant |
| future replay | observation summary | replay result | summary does not change ReplayResult.status | Yes later | 11.2.3 invariant |
| boundary | reporter not called | implementation tests | no Task Result Reporter integration | Yes later | 11.2.5 only |
| boundary | recovery not triggered | implementation tests | no retry / abort / takeover | Yes later | M12 only |
| boundary | autonomous run not called | command review | no `/exploration/autonomous-runs` direct call | Yes | docs package excludes live run |
| boundary | no external websites | fixture review | all routes local / self-hosted | Yes later | deterministic evidence |
| boundary | raw HTML not persisted | schema/review | no raw HTML / DOM dump storage | Yes later | observation boundary |

## Documentation Validation

本轮只运行文档级检查：

```bash
git diff --check
git status --short
git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.yaml' 'package-lock.json'
find docs/iterations -maxdepth 4 -type d \( -name 'm12' -o -name '12.*' -o -name 'm14' -o -name '14.*' -o -name '11.3-*' \) -print
```

## Future Fixture Route Smoke

后续 fixture 页面实现后，每个 route 应验证：

- route 可打开。
- trigger 可见。
- 初始状态 deterministic。
- 点击后状态变化 deterministic。
- reset 生效。
- 页面不依赖外部真实网站。

## Future Replay / Observation

后续 replay observation 验证必须覆盖：

- URL/title change fixture -> current MVP observed。
- toast / modal / loading / list refresh fixture -> current MVP 不误报已支持 signal。
- `network_idle_observed` 不进入 primary signal。
- `observation_summary` 不改变 `ReplayResult.status`。
- Frontend timer-based delay 不写成真实 network evidence。
- 11.2.4.5 mock backend 才验证 HTTP slow response / error status。

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- 本轮不要求 E2E。
- 本轮不要求 live UI smoke。
- 如果没有真实打开浏览器或产品 UI，不得声称已经完成 UI smoke / E2E。
- 如果只运行文档检查，必须明确写成“未进行浏览器验证”。
- 后续浏览器验证必须记录入口 URL / 页面、操作路径、截图或可复查观察结果。

## Live Run 边界（Live Run Boundary）

本轮不运行 `verify-scenario`、autonomous run 或 product-driven browser execution。

如果后续用户明确要求 live run，必须记录：

- invocation surface。
- run_id。
- pass_gate.status。
- supervisor verdict。
- scorecard。
- 是 product UI traffic 还是 skill invocation。
- 原始输出或可复查路径。

`pass_gate.status` 是权威结果；`unverified` 不是通过。

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| Fixture route smoke | 本轮不实现页面。 | 不能证明 future routes 已可打开。 |
| Mock backend tests | 本轮不实现 backend。 | 不能证明 HTTP delay / errors。 |
| E2E | 本轮只生成文档。 | 不能证明浏览器 replay。 |
| Live UI smoke | 本轮不改 UI。 | 不能证明可视化交互。 |
| `verify-scenario` | 本轮不触发 autonomous run。 | 无 live supervisor evidence。 |
| Task Result Reporter tests | 11.2.5 才接 reporter。 | 当前不能证明 reporter 消费 fixture evidence。 |
| M12 recovery tests | M12 才处理 recovery / retry / abort。 | 当前不能证明 failure dialogue。 |
