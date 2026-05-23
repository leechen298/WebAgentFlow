# 测试计划（Test Plan）

状态：proposed

## 适用条件

本包涉及 Agent / Reporter / recovery / replay、CLI eval、跨层 Conversation API 验收、
artifact 和 AI 外部测试操作员边界，因此必须维护 `test-plan.md`。

## 测试范围（Test Scope）

- Unit：后续实现应覆盖 target-agnostic routing、choice parsing、pending continuation、
  forbidden-token scanning utilities。
- Integration：后续实现应通过 Conversation API 跑用户行为 case。
- API：使用现有 Conversation API；不新增 autonomous-run 调用。
- Console UI：第一版不要求；只有用户明确要求 live UI smoke 时才执行。
- E2E：第一版通过 project eval runner 驱动产品 runtime；浏览器执行只在 execute-known
  需要 replay evidence 时发生。
- Agent / Reporter / Recovery：覆盖 user-facing intent handling、evidence-backed reply、
  failure menu wording 和 private payload redaction。
- Codex / AI External Operator：Codex 只能报告真实命令输出、artifact、exit code 和 case gate。
- Live autonomous run：不在本包默认范围内。

## 测试矩阵（Test Matrix）

| Layer | Scenario | Command / Surface | Expected | Required? | Notes |
|---|---|---|---|---|---|
| Static | STATIC-1 forbidden target details absent from runtime | future `pnpm run eval:wagent:user-behavior` preflight | No test target URL / route / fixture text / DOM test id appears in feature code or product prompts | Yes | Hard fail before behavior cases |
| Integration | CASE-1 URL-only known page | Conversation API via eval runner | WAgent lists learned operations, offers learn-new option, exposes no private id | Yes | Setup must record how learned actions were created |
| Integration | CASE-2 URL-only unknown page | Conversation API via eval runner | WAgent says page is not learned and asks whether to learn / inspect / cancel | Yes | Must not pretend it can execute |
| Integration / replay | CASE-3 execute known action | Conversation API via eval runner | WAgent matches learned action, fills user value, executes, and final reply cites evidence-backed result | Yes | No relearning unless user requested |
| Integration | CASE-4 execute unknown action | Conversation API via eval runner | WAgent asks whether to learn and execute, only learn, or cancel | Yes | No hidden learn-then-execute |
| Integration | CASE-5 vague input no execution | Conversation API via eval runner | WAgent asks for page / operation clarification and does not execute | Yes | Any replay / browser side effect is fail |
| Integration | CASE-6 explicit learn action | Conversation API via eval runner | WAgent learns requested operation and stores replaceable parameters | Later | Follow-up after first wave |
| Integration | CASE-7 pending continuation | Conversation API via eval runner | User answer fills previous missing slot and continues same task | Later | Must preserve target URL |
| Integration | CASE-8 choice selection | Conversation API via eval runner | A / 1 / first choice resolves public choice to private path and clears pending choice | Later | No private map in public payload |
| Integration / recovery | CASE-9 recovery menu | Conversation API via eval runner | Failure / unverified execution shows retry execution, relearn, cancel; success shows no menu | Later | Retry wording must be explicit |
| Artifact | REDACTION-1 public / artifact redaction | Eval runner artifact scan | No `learned_path_id`, selector, private map, raw planner payload, slot override leakage | Yes | Dynamic private ids must be hashed or redacted |
| Boundary | BOUNDARY-1 no disallowed run surfaces | Eval runner operation log | No direct autonomous-run endpoint, no direct replay substitution, no hidden service import | Yes | Direct endpoint use fails case |

## Anti-hardcoding Gate

The eval must build a forbidden-token list from the active test spec. It must include at least:

- target URL components;
- target route / page path;
- page-specific visible text;
- page-specific button / field labels;
- page-specific DOM test ids and selectors;
- fixture-only entity names and aliases.

The scan must cover product runtime code and product prompt assets. It must exclude docs, artifacts,
eval specs, test files and fixture source. A forbidden match in runtime code or product prompts is a
hard fail because it means the implementation may be targeting the test page instead of solving the
general product behavior.

## E2E / UI Smoke 边界（E2E / UI Smoke Boundary）

- If the eval runner does not open a browser or product UI, do not claim UI smoke.
- If execute-known uses browser replay under the Conversation runtime, record it as project eval runner
  evidence, not as Console UI smoke.
- If UI smoke is later requested, record the exact product surface operated, visible result, screenshot
  or log, and run / session id where available.
- Browser evidence must not replace the forbidden-token scan.

## Codex / AI 外部测试操作员边界（Codex / AI External Operator Boundary）

Codex / AI can run the project eval command and report:

- command;
- exit code;
- case status;
- artifact paths;
- session ids;
- sanitized public response excerpts;
- not-run surfaces.

Codex / AI must not:

- invent WAgent behavior;
- infer pass from reading code only;
- call autonomous-run endpoints directly;
- call direct replay API and label it WAgent conversation;
- submit raw artifacts with private payload leakage.

## Live Run 边界（Live Run Boundary）

Default 11.3.7 eval does not run `verify-scenario` or autonomous run. If a later request explicitly
asks for live UI smoke or autonomous validation, the report must follow AGENTS.md:

- lead with `pass_gate.status` when `verify-scenario` is used;
- include `run_id`, supervisor verdict, confidence, scorecard and summary;
- label `unverified` as not pass;
- identify whether traffic came from project UI or approved CLI.

## 未运行项（Not Run）

| Item | Reason | Risk |
|---|---|---|
| `pnpm run eval:wagent:user-behavior` | Runner not implemented in this docs draft | 11.3.7 behavior remains unverified |
| Console UI smoke | Not requested and not part of first-wave docs draft | UI-specific regressions would require separate approval |
| `verify-scenario` | Out of scope for this eval package | No Supervisor pass_gate evidence is claimed |
| autonomous run endpoints | Prohibited unless product UI or approved skill explicitly triggers them | Direct calls would invalidate evidence |
