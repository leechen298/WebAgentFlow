# 技术设计（Technical Design）

状态：pass（first-wave user-facing behavior gates passed；full learn-then-execute remains follow-up）

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
| URL-only known page must list learned operations | Eval runner prepares current eval session / explicit eval scope with learned actions, sends only target URL through Conversation API | `test-plan.md` CASE-1 | Reply must not expose private ids |
| URL-only unknown page must not pretend execution is possible | Eval runner uses fresh session / isolated scope / explicit filtered catalog with no learned actions | `test-plan.md` CASE-2 | Global historical LearnedPath rows cannot make this pass |
| Unknown URL choose-learn starts learning | Eval runner selects the public learn option after unknown URL guidance and asserts a real learning flow starts | `test-plan.md` CASE-2A | Required; no fake learning-complete text |
| execute-known must match learned action and verify result | Conversation runtime matches learned action, applies user slots, runs replay, checks evidence | `test-plan.md` CASE-3 | Existing 11.3.6 replay gates are supporting, not sufficient |
| execute-unknown must ask for confirmation before learning | Runtime returns learn-and-execute / learn-only / cancel choice | `test-plan.md` CASE-4 | No hidden relearning |
| Execute-unknown choose-learn must not fake full learn-then-execute | Eval runner selects the public learn / learn-and-execute option and records whether runtime supports full continuation | `test-plan.md` CASE-4A | If unsupported, full learn-then-execute is follow-up, not pass |
| vague input must not execute | Router / orchestrator produces clarification or guidance without replay | `test-plan.md` CASE-5 | Mis-execution is a hard fail |
| Test target details must not enter feature code or product prompts | Forbidden-token list from eval spec, scanned against runtime code and prompt assets | `test-plan.md` STATIC-1 | Hard fail before behavior cases can pass |
| Existing test-target special cases block the eval | Scanner and review classify route / selector / operation constants in runtime or prompts as blockers | `test-plan.md` STATIC-1 | No grandfather exception |
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

Existing runtime special cases are not exempt. If the scan finds target page route constants,
target-specific selectors, button text, field labels, fixture item names, operation aliases, or prompt
examples in product runtime / prompt assets, the implementation must remove or generalize them. Moving
them into eval spec / test-only code is acceptable. Leaving them in place with a cleanup note means
the 11.3.7 result is `blocked`, not pass.

Known target-specific runtime code must be cleaned up before 11.3.7 can pass. Read-only inspection has
already found likely blocker patterns in runtime services, including the conversation intake, chat
runtime and learning run service. Implementation should treat those as cleanup targets, while keeping
test constants in eval runner / fixture / tests as test-only data.

### 3. Known / unknown state isolation

Known and unknown setup must be deterministic:

- known cases seed or create learned actions only in the current eval session / explicit eval scope;
- unknown cases use a fresh session, isolated eval scope, explicit filtered catalog, or equivalent
  mechanism that excludes old global LearnedPath rows;
- the artifact records the isolation mechanism and the learned action count seen by the runtime;
- if isolation fails or historical global data can affect the answer, unknown cases are `blocked`.

### 4. First-wave behavior cases

Implement these required user-facing cases:

| Case | Setup | User input | Expected behavior |
|---|---|---|---|
| `url_only_known_page` | Session has one or more learned operations for the target | target URL only | WAgent lists learned operations and offers to learn a new operation |
| `url_only_unknown_page` | Session / scope has no learned operations | target URL only | WAgent says it has not learned the page and asks whether to learn or inspect |
| `url_only_unknown_choose_learn_starts_learning` | Continue from unknown URL guidance | User selects learn / start learning option | WAgent enters a real learning flow, or returns a product-level blocked state with evidence; it does not execute or fake completion |
| `execute_known_action` | Session has matching learned operation | natural-language execution request with needed value | WAgent executes without relearning and verifies evidence |
| `execute_unknown_action` | No matching learned operation | natural-language execution request | WAgent asks whether to learn and execute, only learn, or cancel |
| `execute_unknown_choose_learn_then_execute_or_learning_flow` | Continue from execute-unknown choice | User selects learn-and-execute / learn option | If supported, WAgent learns, executes and verifies; if unsupported, WAgent starts learning only and records full learn-then-execute as follow-up |
| `vague_input_no_execution` | Missing target or ambiguous operation | vague user message | WAgent does not execute and asks for page / operation clarification |
| `forbidden_test_target_not_in_runtime_code_or_prompts` | Static scan over product runtime and prompt assets | N/A | No target-specific URL / route / text / selector / alias appears outside allowed test/docs/fixture layers |

### 5. Follow-up behavior cases

After the first-wave cases pass, extend the runner with:

- explicit learning request;
- slot continuation after WAgent asks for missing information;
- A / 1 / first-choice selection;
- recovery menu after failed / unverified execution;
- controlled page capability discovery;
- controlled multi-operation learning;
- natural-language reuse across multiple learned operations.

Full `learn_then_execute` completion belongs here only if the current product cannot truthfully complete
learning, immediate execution and evidence verification during the first-wave case.

### 6. Artifact and closeout reporting

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
-> setup known or unknown session state with explicit isolation
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
5. `blocked` if known / unknown isolation cannot exclude global historical LearnedPath rows.
6. `blocked` if current runtime has target-specific code / prompt special cases and cleanup is not completed.
7. `pass` if all required gates pass.
8. `unverified` only for docs-only review or skipped behavior surfaces.

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
- Unknown setup can see old global LearnedPath data: affected cases are `blocked`.
- Unknown URL choose-learn does not start a real learning flow: `fail`, unless the product returns a
  reviewable blocked state explaining why learning cannot start.
- Runtime executes on vague input: hard `fail`.
- Runtime hidden-learns unknown action without user confirmation: hard `fail`.
- Runtime or product prompt contains target route / selector / fixture item / operation alias: hard `fail`
  if discovered during scan; if cleanup is deferred, overall 11.3.7 is `blocked`.
- Public response leaks private id / selector / private map: hard `fail`.
- Test target string appears in product code or prompt asset: hard `fail`.
- Product runtime imports eval spec / docs / artifact to access target details: hard `fail`.
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
| State isolation | Prove known / unknown are determined by current eval session / scope, not old global catalog rows | `test-plan.md` ISOLATION-1 |
| Conversation behavior eval | Prove URL-only, choose-learn, execute-known, execute-unknown and vague input behavior | `test-plan.md` CASE-1 to CASE-5 |
| Evidence / reporter | Prove execute-known final reply is evidence-backed | `test-plan.md` CASE-3 |
| Redaction | Prove public response and artifacts do not leak private ids / selectors / maps | `test-plan.md` REDACTION-1 |
| Boundary | Prove eval did not use autonomous-run endpoint or direct replay substitution | `test-plan.md` BOUNDARY-1 |

## 验证命令入口（Validation Commands）

Implemented eval command:

```bash
pnpm run eval:wagent:user-behavior
```

Latest closeout evidence:

- `pnpm run eval:wagent:user-behavior -- --timeout 300` exited `0` with top-level `status=pass`.
- Stable JSON artifact:
  `artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json`.
- Stable Markdown artifact:
  `docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md`.
- `eval_result_gate_check` returned `decision=PASS`.
- `eval_artifact_redaction_check` returned `status=pass`, `match_count=0`.
- Forbidden-target scan returned `status=pass`, `match_count=0`.

This pass is scoped to first-wave user-facing behavior gates. Full learn-then-execute remains a
non-required follow-up, and this package does not claim complete page-wide automatic capability
discovery or automatic learning of all operations on a page.
