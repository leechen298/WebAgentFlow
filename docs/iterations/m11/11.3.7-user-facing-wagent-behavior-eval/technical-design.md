# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

11.3.6 runtime eval program 已关闭为 `pass_with_caveats`。它通过 Conversation API 验证了
以下受控 runtime 能力：

- learned path 参数化复用；
- execution evidence / Task Result Reporter adapter；
- pending choice public / private separation；
- planner-backed choice branch；
- failure recovery menu safety；
- artifact redaction。

但 11.3.6 的 caveats 明确存在：

- pending-choice / planner-choice 使用 eval-only candidate binding；
- planner top choice 仍是 non-required warning；
- failure recovery failure trigger 使用 eval-only hook；
- 没有执行 `verify-scenario`、autonomous run 或 Console UI smoke；
- 没有验证页面级自动能力发现、多操作学习或普通用户入口行为。

11.3.7 的实现应在此基础上新增用户行为 eval，而不是继续扩大 11.3.6 component gates。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| URL-only known page must list learned operations | Eval runner prepares a session with learned actions, sends only target URL through Conversation API | `test-plan.md` CASE-1 | Reply must not expose private ids |
| URL-only unknown page must not pretend execution is possible | Eval runner uses fresh session / isolated lookup scope with no learned actions | `test-plan.md` CASE-2 | Must offer learning / inspect / cancel style next step |
| execute-known must match learned action and verify result | Conversation runtime matches learned action, applies user slots, runs replay, checks evidence | `test-plan.md` CASE-3 | Existing 11.3.6 replay gates are supporting, not sufficient |
| execute-unknown must ask for confirmation before learning | Runtime returns learn-and-execute / learn-only / cancel choice | `test-plan.md` CASE-4 | No hidden relearning |
| vague input must not execute | Router / orchestrator produces clarification or guidance without replay | `test-plan.md` CASE-5 | Mis-execution is a hard fail |
| Test target details must not enter feature code or product prompts | Forbidden-token list from eval spec, scanned against runtime code and prompt assets | `test-plan.md` STATIC-1 | Hard fail before behavior cases can pass |
| Eval evidence must be auditable | JSON / Markdown artifacts include session id, commands, sanitized public responses, gates | `test-plan.md` ARTIFACT-1 | Raw private payload must be redacted |
| No autonomous-run endpoint substitution | Runner drives Conversation API or approved UI only | `test-plan.md` BOUNDARY-1 | Direct autonomous endpoint calls are prohibited |

## 实现方案（Proposed Implementation）

### 1. Eval spec as data

Create a test-only eval spec that carries all target-specific details:

- target URL;
- target label for artifact readability;
- allowed test utterances;
- learned / unlearned setup mode;
- expected public behavior gates;
- forbidden runtime tokens generated from the target URL, route, labels, fixture strings,
  DOM test ids and target-specific aliases.

The spec must live under a test-only path and must not be imported by product runtime code or
product prompt registry.

### 2. Forbidden-token hard gate

Before running behavior cases, the eval must scan feature code and product prompt assets for the
target-specific forbidden tokens.

Allowed paths:

- docs;
- artifacts;
- eval specs;
- eval runner code and tests;
- fixture source code;
- test files.

Forbidden paths:

- API runtime services / routers / schemas;
- CLI runtime code;
- Console production source;
- product prompt assets, prompt registry, system prompts, developer prompts and few-shot examples.

Any forbidden match fails the eval. The report must include only sanitized token labels or hashes
when a token is sensitive.

### 3. First-wave behavior cases

Implement five required user-facing cases:

| Case | Setup | User input | Expected behavior |
|---|---|---|---|
| `url_only_known_page` | Session has one or more learned operations for the target | target URL only | WAgent lists learned operations and offers to learn a new operation |
| `url_only_unknown_page` | Session / scope has no learned operations | target URL only | WAgent says it has not learned the page and asks whether to learn or inspect |
| `execute_known_action` | Session has matching learned operation | natural-language execution request with needed value | WAgent executes without relearning and verifies evidence |
| `execute_unknown_action` | No matching learned operation | natural-language execution request | WAgent asks whether to learn and execute, only learn, or cancel |
| `vague_input_no_execution` | Missing target or ambiguous operation | vague user message | WAgent does not execute and asks for page / operation clarification |

### 4. Follow-up behavior cases

After the first-wave cases pass, extend the runner with:

- explicit learning request;
- slot continuation after WAgent asks for missing information;
- A / 1 / first-choice selection;
- recovery menu after failed / unverified execution;
- controlled page capability discovery;
- controlled multi-operation learning;
- natural-language reuse across multiple learned operations.

### 5. Artifact and closeout reporting

The runner should write:

- one timestamped JSON artifact;
- one stable latest JSON artifact;
- one timestamped Markdown result;
- one stable latest Markdown result.

The Markdown result must lead with the behavior eval status and separately list:

- required behavior gates;
- forbidden-token scan result;
- redaction scan result;
- not-run live surfaces;
- caveats.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | 11.3.7 design should use existing Conversation API | If implementation needs new routes, it must update contract first |
| API response schema | No | No schema changes in this design | Existing public surfaces stay compatible |
| Database schema / migration | No | No planned migration | Test setup must use existing session / LearnedPath data |
| CLI | Yes | Future eval command may be added | Product `wagent chat` behavior remains target-agnostic |
| Console UI | No | First wave is CLI / API eval | UI smoke only if explicitly requested later |
| Conversation events | Yes | Eval will inspect sanitized events | No private payload leakage allowed |
| Replay execution | Yes | execute-known case uses replay through Conversation runtime | No direct replay substitution |
| Reporter | Yes | execute-known case requires evidence-based final reply | 11.3.6 reporter gates are supporting evidence |
| Worker / async jobs | No | Not in first-wave scope | N/A |
| Tests / fixtures | Yes | Eval spec and runner cases are test-only | Target details stay in tests / fixtures |
| Docs | Yes | New iteration package and index updates | This document is the current change |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

No schema, database, migration or public API changes are planned by this design.

If implementation later needs a new artifact schema, it must be local to the eval runner and documented
in `docs/testing/` or the runner source. It must not become a product API contract unless a new
iteration updates `contract.md`.

## 服务 / 模块设计（Service / Module Design）

Future implementation should prefer a test-only runner boundary:

- `scripts/evals/wagent_user_behavior_eval.py` or equivalent: orchestrates cases and writes artifacts.
- `scripts/evals/specs/*` or equivalent: stores target-specific eval data and forbidden-token list.
- `docs/testing/wagent-user-facing-behavior-eval.md`: describes how to run and interpret the eval.
- API tests may cover target-agnostic runtime behavior, but target-specific expectations should remain
  in tests, not production services.

The product runtime should remain generic:

- URL parsing should accept arbitrary user-provided URLs.
- Learned action lookup should use current session / allowed scope, not fixed target constants.
- Operation names should come from LearnedPath metadata, page analysis or user wording, not fixture names.
- Prompts should describe generic behavior policies, not target-page examples.

## 数据流（Data Flow）

```text
eval spec
-> forbidden-token scan against runtime code and product prompts
-> preflight API / product surface availability
-> setup known or unknown session state
-> send user message through Conversation API
-> collect public response, events, session metadata and reporter evidence
-> evaluate gates
-> write sanitized artifacts
```

If a case needs learned actions, setup must be explicit and recorded. The report must say whether the
learned action was produced through a prior conversation learning flow, a test fixture seed, or an
existing isolated eval setup.

## 状态推导（Status / State Derivation）

Overall status priority:

1. `blocked` if required services or setup are unavailable.
2. `fail` if forbidden-token scan fails.
3. `fail` if any required behavior gate fails.
4. `fail` if redaction scan finds private payload leakage.
5. `pass` if all required gates pass.
6. `unverified` only for docs-only review or skipped behavior surfaces.

`unverified` is not a pass.

## 兼容性（Compatibility）

- 11.3.6 artifacts remain valid and keep their caveats.
- Existing runner scripts may continue to exist; 11.3.7 can reuse utilities but must not merge
  target-specific product behavior into generic runtime.
- Existing docs that mention prior test fixtures remain historical evidence. New functionality must not
  copy those target details into product code or prompts.

## 失败 / 边界情况（Failure / Edge Cases）

- Product page unavailable: case is `blocked`, not fail.
- API unavailable: case is `blocked`, not fail.
- Known setup cannot produce learned action: affected cases are `blocked` with setup reason.
- Runtime executes on vague input: hard `fail`.
- Runtime hidden-learns unknown action without user confirmation: hard `fail`.
- Public response leaks private id / selector / private map: hard `fail`.
- Test target string appears in product code or prompt asset: hard `fail`.
- Evidence says executed but reporter cannot verify DOM / observation result: case is fail or
  unverified according to reporter output, never pass.

## 非目标（Non-goals）

- No arbitrary-page full capability discovery in first wave.
- No fully automatic page-wide operation library generation in first wave.
- No login-page acceptance in first wave.
- No autonomous-run endpoint calls.
- No product prompt few-shot examples copied from the test target.

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Static target-generalization scan | Prove target details are absent from feature code and product prompts | `test-plan.md` STATIC-1 |
| Conversation behavior eval | Prove URL-only, execute-known, execute-unknown and vague input behavior | `test-plan.md` CASE-1 to CASE-5 |
| Evidence / reporter | Prove execute-known final reply is evidence-backed | `test-plan.md` CASE-3 |
| Redaction | Prove public response and artifacts do not leak private ids / selectors / maps | `test-plan.md` REDACTION-1 |
| Boundary | Prove eval did not use autonomous-run endpoint or direct replay substitution | `test-plan.md` BOUNDARY-1 |

## 验证命令入口（Validation Commands）

The exact command will be added during implementation. The intended validation shape is:

```bash
pnpm run eval:wagent:user-behavior
```

Until the command exists, this iteration remains proposed / unverified.
