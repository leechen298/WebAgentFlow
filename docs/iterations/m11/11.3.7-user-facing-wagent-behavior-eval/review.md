# 复盘 / 评审（Review）

状态：pass（first-wave user-facing behavior gates passed；full learn-then-execute remains non-required follow-up）

## 2026-05-23 文档草案

- Author：Codex
- Decision：docs_created
- Notes：
  - 基于用户与 ChatGPT 的讨论，新增 11.3.7 用户视角 WAgent 行为 eval 文档包。
  - 本包定位为 11.3.6 之后的下一阶段验收定义，不实现 runtime 代码。
  - 明确 11.3.6 只证明 runtime 受控执行能力，不能代表页面级自动操作学习或完整产品预期通过。
  - 明确第一批 case：URL-only known、URL-only unknown、execute-known、execute-unknown、
    vague-input。
  - 明确后续扩展：explicit learn、pending continuation、choice selection、recovery menu、
    page capability discovery、multi-operation learning、natural-language reuse。
  - 新增 anti-hardcoding hard gate：测试页面链接及其相关内容不得出现在功能代码或产品 prompt 中。

## 用户反馈

- “M11.3.6 closeout 的测试通过，但结论口径需要修正。” -> accepted。
- “当前测试只证明 chat runtime 对已学习路径的参数化复用、evidence reporting、pending choice /
  planner choice / recovery menu。” -> accepted。
- “它没有证明 WAgent 能自动学习页面所有操作、从新页面生成完整操作库、任意页面任务自动命中并执行。”
  -> accepted。
- “新增下一阶段 proposal：11.3.7 Page Capability Learning Eval / User-facing WAgent Behavior Eval。”
  -> accepted，采用 `11.3.7-user-facing-wagent-behavior-eval`，并把 page capability learning 放入后续扩展。
- “必须严格禁止需要测试的页面链接及其相关内容，出现在功能的代码和提示词中。” -> accepted，
  写入 contract、technical design、test plan 和 review checklist。
- “因为出现的话，可能会出现针对性的实现功能，影响整体产品。” -> accepted，作为
  forbidden-token hard gate 的动机。
- “如果当前代码已有 `/items`、`[data-testid='item-list']` 等测试站点特判，11.3.7 应将其
  视为 blocker，必须改为 generic runtime 或移入 eval spec / test-only layer。” -> accepted，
  已写入 contract、technical design、test plan 和 plan。
- “不允许用 grandfather exception 直接放过，除非明确开 cleanup issue 并将 11.3.7 标为
  blocked。” -> accepted。
- “第一批 required cases 需要包含 `url_only_unknown_choose_learn_starts_learning` 和
  `execute_unknown_choose_learn_then_execute_or_learning_flow`。” -> accepted。
- “如果 `learn_then_execute` 当前不支持，则明确写为 follow-up，不能伪造 pass。” -> accepted。
- “known / unknown 页面状态隔离策略必须明确，不能被全局旧 LearnedPath 污染。” -> accepted。
- “测试页面细节只能存在于 product-test-site fixture source、eval spec、tests、docs / review /
  testing results / artifacts，不能被 product runtime import。” -> accepted。
- “没学过 -> 用户选择学习 -> 真进入学习流程” -> accepted，已明确为 first-wave required
  `url_only_unknown_choose_learn_starts_learning`；必须进入真实 learning flow，或以 evidence-backed
  blocker 记录，不能伪造 pass。
- “anti-hardcoding gate 必须严格执行，已有测试站点特判也应该修掉，不能放过。” -> accepted，
  已把现有特判清理写成 11.3.7 实现步骤和 pass 前置条件。

## 2026-05-23 文档修订

- Author：Codex
- Decision：docs_revised
- Notes：
  - Strengthened anti-hardcoding gate with product-test-site URL / route / button text / field label /
    DOM test id / fixture item names / operation aliases.
  - Added explicit blocker language for existing runtime / prompt target special cases, including route
    and DOM-locator checks. No grandfather exception is allowed.
  - Added first-wave required scenarios:
    `url_only_unknown_choose_learn_starts_learning` and
    `execute_unknown_choose_learn_then_execute_or_learning_flow`.
  - Added staged handling for unsupported full `learn_then_execute`: start learning truthfully and record
    full learn-then-execute as follow-up, not pass.
  - Added known / unknown isolation requirement: current eval session / scope for known; fresh session,
    isolated scope or explicit filtered catalog for unknown.
  - Clarified that product runtime must not import eval spec, docs, review, testing results or artifacts
    to access target details.
  - Follow-up user clarification made unknown choose-learn a required real learning-flow gate.
  - Follow-up user clarification made cleanup of existing product-test-site runtime special cases a
    required implementation prerequisite before 11.3.7 can pass.
  - Read-only inspection found likely current runtime blockers in conversation intake, chat runtime and
    learning run service; test constants in `scripts/evals/` remain test-only and are not product runtime.

## 2026-05-23 设计评审收口

- Reviewer：ChatGPT
- Decision：pass
- Notes：
  - First-wave user-facing cases are complete, including unknown choose-learn and staged
    execute-unknown learning flow.
  - Anti-hardcoding gate is strict and has no grandfather exception.
  - Known / unknown isolation is defined.
  - Current runtime target-specific blockers are documented and must be cleaned before 11.3.7 can pass.
  - Package status is raised to `ready_for_implementation`; implementation has not started.

## 2026-05-24 证据完整性预检

- Reviewer：Codex using `webagentflow-eval-integrity`
- Decision：BLOCKED for any 11.3.7 pass claim
- Scope：
  - This was a pre-implementation integrity review, not a behavior eval run.
  - No `verify-scenario`, autonomous run, Console UI smoke or direct replay endpoint was invoked.
  - No 11.3.7-specific JSON / Markdown result artifact exists yet.
- Evidence：
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/waf-11.3.7-target-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1`
  - Result: exit `1`, `status=fail`, `match_count=100`.
  - High-confidence blocker examples:
    - `apps/api/app/services/conversation/chat_runtime.py:134` contains `/items`.
    - `apps/api/app/services/conversation/chat_runtime.py:152` contains `[data-testid='item-list']`.
    - `apps/api/app/services/conversation/chat_runtime.py:193` contains target-specific `新增项目` result wording.
    - `apps/api/app/services/conversation/intake.py:270` contains `/items`.
    - `apps/api/app/services/conversation/intake.py:770` returns `新增项目`.
    - `apps/api/app/services/learning/learning_run_service.py:502` checks `/items`.
    - `apps/api/app/services/learning/learning_run_service.py:504` checks `新增项目`.
  - Command: `pnpm run eval:wagent:user-behavior`
  - Result: exit `1`, `ERR_PNPM_NO_SCRIPT`, script not implemented.
  - Runner inspection found only `scripts/evals/wagent_runtime_eval.py`; no
    `scripts/evals/wagent_user_behavior_eval.py` or equivalent first-wave 11.3.7 runner exists.
- Gate decision：
  - `forbidden_test_target_not_in_runtime_code_or_prompts`: FAIL / BLOCKER.
  - user-facing first-wave behavior cases: NOT RUN / UNVERIFIED because the preflight hard gate fails
    and the runner is missing.
  - known / unknown isolation: UNVERIFIED because no 11.3.7 runner artifact records isolation strategy
    or visible learned-action counts.
  - redaction: NOT APPLICABLE for 11.3.7-specific artifacts because none exist yet.
- Required next step：
  - Remove or generalize target-specific product runtime / prompt content before treating 11.3.7 as passable.
  - Then implement the 11.3.7 user-behavior runner, isolation evidence, stable artifacts and redaction check.

## 2026-05-24 Target-agnostic cleanup 后复核

- Reviewer：Codex using `webagentflow-eval-integrity`
- Decision：UNVERIFIED for overall 11.3.7 behavior eval; static forbidden-target gate now passes
- Scope：
  - This was a post-cleanup integrity check after `11.3.7.1 Target-Agnostic Runtime Cleanup`.
  - No `verify-scenario`, autonomous run, Console UI smoke or direct replay endpoint was invoked.
  - No first-wave 11.3.7 user-facing behavior eval artifact exists yet.
- Evidence：
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/waf-11.3.7-target-agnostic-cleanup-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1`
  - Result: exit `0`, `status=pass`, `match_count=0`, `missing_forbidden_paths=[]`.
  - Command: `pnpm run eval:wagent:user-behavior`
  - Result: exit `1`, `ERR_PNPM_NO_SCRIPT`, script not implemented.
  - Runner / artifact inspection found no committed `scripts/evals/wagent_user_behavior_eval.py`, no `eval:wagent:user-behavior`
    package script, and no 11.3.7 user-behavior result artifact under `artifacts`, `docs/testing/results` or
    `scripts/evals`.
- Gate decision：
  - `forbidden_test_target_not_in_runtime_code_or_prompts`: PASS for the scanned product runtime / prompt paths.
  - user-facing first-wave behavior cases: NOT RUN / UNVERIFIED because the runner is still missing.
  - known / unknown isolation: UNVERIFIED because no 11.3.7 runner artifact records isolation strategy
    or visible learned-action counts.
  - redaction: NOT APPLICABLE for 11.3.7-specific artifacts because no such artifacts exist yet.
- Required next step：
  - Implement the 11.3.7 user-behavior runner, target manifest / eval spec, isolation evidence, stable artifacts
    and artifact redaction check.
  - Do not mark 11.3.7 as `pass` until all first-wave gates run through the allowed Conversation / eval surface
    and the reviewable artifacts pass redaction.

## 2026-05-24 `2f36fc6` 外部审核

- Reviewer：ChatGPT
- Decision：cleanup package accepted; 11.3.7 remains not passed
- Reviewed commit：`2f36fc6 fix: remove target-specific runtime constants`
- Accepted scope：
  - Treat this commit as the `11.3.7.1 Target-Agnostic Runtime Cleanup` package.
  - It clears the main anti-hardcoding blocker where product runtime carried product-test-site `/items`
    answers such as route checks, `item_name`, list DOM locators and item-specific evidence wording.
  - It does not complete the 11.3.7 user-facing behavior eval.
- Notes：
  - `entry_gate.py` removed obvious product-test-site item vocabulary while retaining generic web-task terms.
  - `intake.py` moved from test-page `item_name` semantics toward generic `entity_name` / named-value handling.
  - `learned_path_replay.py` and reporter-facing evidence wording now describe generic page text evidence.
  - The new target-agnostic regression test keeps product runtime / prompt paths free of the forbidden target tokens.
  - Legacy `scripts/evals/wagent_runtime_eval.py` remains allowed to contain `/items` and `item_name` because it is
    test-only, but future use should either keep it clearly legacy / items-specific or migrate its gates to generic
    slot-aware assertions.
  - Login / workspace handling remains out of this cleanup scope and should be evaluated separately only if a later
    anti-hardcoding gate targets those surfaces.
- Status after review：
  - Previous state: `BLOCKED: forbidden target constants detected`.
  - Current state: `anti-hardcoding blocker cleanup implemented; awaiting user-facing behavior eval implementation`.
  - 11.3.7 must not be marked `pass` until the first-wave behavior cases, known / unknown isolation and artifact
    redaction gates run with reviewable artifacts.

## 2026-05-24 User-facing behavior eval runner 实现后复核

- Reviewer：Codex using `webagentflow-eval-integrity`
- Decision：runner implemented; overall 11.3.7 remains `blocked` / not pass because live API preflight is unavailable
- Implemented commits：
  - `58e8828 test: add 11.3.7 user behavior eval runner`
  - `24cbbf6 test: record 11.3.7 user behavior blocked artifact`
  - Follow-up review fix: scan-`blocked` hard-gate short-circuit and docs refresh before push.
- Scope：
  - Added `pnpm run eval:wagent:user-behavior`.
  - Added `scripts/evals/wagent_user_behavior_eval.py` and eval-only spec
    `scripts/evals/specs/wagent_user_behavior_items.json`.
  - The runner drives only Conversation API surfaces:
    `/conversation/sessions`, `/dispatch`, `/messages`, `/events` and `/history`.
  - The runner does not call `verify-scenario`, autonomous-run endpoints, Console UI smoke or direct replay.
  - Product runtime / prompt code was not changed by the runner implementation.
- First-wave cases represented in the runner：
  - `url_only_known_page`
  - `url_only_unknown_page`
  - `url_only_unknown_choose_learn_starts_learning`
  - `execute_known_action`
  - `execute_unknown_action`
  - `execute_unknown_choose_learn_then_execute_or_learning_flow`
  - `vague_input_no_execution`
  - `forbidden_test_target_not_in_runtime_code_or_prompts`
- Evidence：
  - Command: `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py tests/test_wagent_runtime_eval.py tests/test_conversation_chat_runtime.py tests/test_conversation_intake.py tests/test_learning_run_service.py tests/test_learned_path_replay.py tests/test_conversation_replay_hook.py tests/test_replay_observation_summary.py -q`
  - Result after hard-gate fix: `267 passed in 9.41s`.
  - Command: `../../.venv/bin/ruff check tests/test_wagent_user_behavior_eval.py ../../scripts/evals/wagent_user_behavior_eval.py`
  - Result: `All checks passed!`.
  - Command: `pnpm run eval:wagent:user-behavior -- --case forbidden_test_target_not_in_runtime_code_or_prompts --json-only`
  - Result: exit `0`, `status=pass`, `case=forbidden_test_target_not_in_runtime_code_or_prompts status=pass`.
  - Command: `pnpm run eval:wagent:user-behavior -- --timeout 15`
  - Result: exit `2`, top-level `status=blocked`.
  - Blocked reason in committed JSON: API preflight for `http://127.0.0.1:8001/health` returned
    `[Errno 61] Connection refused`.
  - Stable JSON artifact: `artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json`.
  - Stable Markdown artifact:
    `docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md`.
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-20260523T170951Z.json docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-20260523T170951Z.md`
  - Result: `status=pass`, `match_count=0`.
- Gate decision：
  - `forbidden_test_target_not_in_runtime_code_or_prompts`: PASS in the committed artifact.
  - user-facing first-wave behavior cases: BLOCKED / NOT VALIDATED because API preflight is unavailable.
  - known / unknown isolation: NOT VALIDATED live because the behavior cases did not reach Conversation API sessions.
  - redaction: PASS for the committed blocked JSON / Markdown artifacts.
  - Overall 11.3.7: not pass.

## 2026-05-24 Runner hard-gate review fix

- Reviewer：ChatGPT
- Decision：fix required before push
- Finding：
  - The runner short-circuited on forbidden-target scan `fail`, but not on scan `blocked`.
  - Because the forbidden-target gate is a hard preflight gate, any non-`pass` scan result must stop before service
    preflight or product interaction.
- Fix：
  - `run_eval()` now short-circuits unless the forbidden-target case status is exactly `pass`.
  - Added regression test:
    `test_blocked_forbidden_scan_stops_before_service_preflight`.
- Status：
  - This fixes eval-runner integrity only.
  - It does not change the committed behavior artifact decision: 11.3.7 remains not pass until live first-wave cases
    run against available Conversation API and product-test-site services.

## 2026-05-24 User-facing behavior gate fix closeout

- Reviewer：Codex using `webagentflow-eval-integrity`
- Decision：PASS for 11.3.7 first-wave required gates
- Scope：
  - Fixed only the current required gate failures:
    public `llm_trace_recorded` redaction, known action matching / execution,
    URL-only unknown guidance and execute-unknown guidance.
  - Product runtime / prompts remain target-agnostic; no product-test-site route, DOM locator, fixture item,
    field name or operation alias was added to runtime / prompts.
  - Eval was driven through `pnpm run eval:wagent:user-behavior`, which uses the Conversation API surface.
  - No `verify-scenario`, Console UI smoke, direct replay endpoint or direct autonomous-run endpoint was used.
- Implementation notes：
  - Public LLM trace events / history now expose safe trace metadata only and omit raw prompt / response /
    parsed output content.
  - Known action matching now normalizes generic action phrases and strips user-provided named values, so
    value-specific learned aliases do not block later parameterized execution.
  - Single-candidate scope does not override an explicit conflicting user action; unmatched operations are routed
    to no-match / learn guidance rather than replaying an unrelated action.
  - Unknown URL and unknown execute flows distinguish no learned actions for the page from a learned page with an
    unmatched operation.
  - Product-level learning can save a path when generic visible page text confirms a user-provided value, without
    relying on target-specific constants or external LLM supervisor success.
- Live eval setup：
  - Local API and product-test-site were started.
  - API was restarted with the LLM provider env var empty so intake / router / entry-gate use deterministic fallback and no
    external LLM provider receives local page / conversation data during this run.
- Evidence：
  - Command:
    `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_chat_runtime.py tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py tests/test_conversation_intake.py tests/test_learning_run_service.py tests/test_learned_path_replay.py tests/test_conversation_replay_hook.py tests/test_replay_observation_summary.py -q`
  - Result: `283 passed in 12.66s`.
  - Command:
    `cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/history.py app/services/learning/learning_run_service.py tests/test_conversation_api.py tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py`
  - Result: `All checks passed!`.
  - Command:
    `pnpm run eval:wagent:user-behavior -- --timeout 300`
  - Result: exit `0`, top-level `status=pass`.
  - Clean HEAD refresh:
    rerun at commit `e91c0f5`; latest JSON / Markdown artifacts now record `Commit: e91c0f5`.
  - Stable JSON artifact: `artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json`.
  - Stable Markdown artifact:
    `docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md`.
  - Timestamped JSON artifact:
    `artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-20260524T032157Z.json`.
  - Timestamped Markdown artifact:
    `docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-20260524T032157Z.md`.
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_result_gate_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json`
  - Result: `decision=PASS`, reason `all detectable required gates/cases passed`.
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md`
  - Result: `status=pass`, `match_count=0`.
  - Command:
    `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/wagent-user-behavior-target-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1`
  - Result: `status=pass`, `match_count=0`, `missing_forbidden_paths=[]`.
  - Command: `git diff --check`
  - Result: pass.
- Gate summary from latest artifact：
  - `forbidden_test_target_not_in_runtime_code_or_prompts`: pass.
  - `url_only_known_page`: pass.
  - `execute_known_action`: pass.
  - `url_only_unknown_page`: pass.
  - `url_only_unknown_choose_learn_starts_learning`: pass.
  - `execute_unknown_action`: pass.
  - `execute_unknown_choose_learn_then_execute_or_learning_flow`: pass for required staged learning-flow gates.
  - `vague_input_no_execution`: pass.
- Caveat：
  - `full_learn_then_execute` is explicitly non-required and remains `follow_up` in the latest artifact.
    This PASS does not claim complete learn-then-execute support.

## 最终差异（Final Delta）

### 实际交付

- Created 11.3.7 iteration documentation package.
- Updated M11 index / plan and 11.3.6 closeout wording to separate runtime component acceptance
  from user-facing product behavior acceptance.
- Revised 11.3.7 docs to make anti-hardcoding, no-grandfather blocker handling, first-wave choose-learn
  cases, known / unknown isolation and allowed target-detail locations explicit.
- Recorded post-cleanup preflight status: anti-hardcoding blocker cleanup implemented, forbidden-target scan pass,
  overall 11.3.7 behavior still unverified.
- Implemented `pnpm run eval:wagent:user-behavior` runner and eval-only target spec.
- Added unit coverage for first-wave gate semantics, artifact redaction, exit-code mapping, scan-only execution,
  pnpm argument separator handling and blocked forbidden-scan short-circuit.
- Added stable JSON / Markdown artifacts for the current behavior eval run. The latest stable artifact is `pass`
  for all first-wave required gates, with full learn-then-execute recorded as a non-required follow-up.

### 相对 Intent / Contract / Technical Design / Test Plan / Plan 的偏差

- The original docs-only draft later became a mixed docs + eval-runner implementation package.
- Earlier behavior artifacts were `blocked` or `fail`; the latest artifact supersedes them for the current code and
  records first-wave required gate pass evidence.

### WebAgentFlow Live Run 边界（Live Run Boundary）

本轮没有触发 `verify-scenario`、Console UI smoke、direct replay endpoint 或 direct autonomous-run
endpoint。`pnpm run eval:wagent:user-behavior` used the approved Conversation API eval surface. Product-level
learning inside the API used the existing product learning runtime as part of the Conversation flow; it was not invoked
through a direct autonomous-run endpoint by Codex.

### E2E / Codex 外部测试操作员证据（E2E / Codex Evidence）

本轮已运行 11.3.7 eval runner against local API + product-test-site services. The latest artifact is `pass`;
the pass claim is limited to first-wave required gates and does not include full learn-then-execute.

### 验证证据（Validation Evidence）

| Command / Surface | Expected | Actual result | Exit code | Pass / Fail / Skip | Evidence | Notes |
|---|---|---|---|---|---|---|
| `find docs/iterations/m11/11.3.7-user-facing-wagent-behavior-eval -maxdepth 1 -type f | sort` | Seven docs exist | Seven files listed: README, intent, contract, technical-design, test-plan, plan, review | 0 | Pass | command output | Docs package is complete |
| `rg -n "11\\.3\\.7|User-facing WAgent Behavior Eval|测试页面链接|forbidden-token|runtime execution capabilities" docs/iterations/m11 docs/testing/wagent-runtime-eval.md docs/testing/results/m11-11.3.6-runtime-eval-program-closeout-20260523T135028Z.md` | Scope correction discoverable | Matches found in M11 index / plan, 11.3.6 program docs, closeout docs, runtime eval docs and 11.3.7 package | 0 | Pass | command output | Scope correction is discoverable |
| scenario id grep | Required first-wave scenarios discoverable | All eight required scenario ids found across 11.3.7 docs | 0 | Pass | command output | Includes choose-learn and forbidden-target scenario ids |
| anti-hardcoding / isolation grep | Blocker, no-grandfather and isolation language discoverable | Matches found for no grandfather, blocker / blocked, fresh session, isolated scope, explicit filtered catalog, product runtime import, fixture item names and operation aliases | 0 | Pass | command output | Confirms this revision is represented in docs |
| runtime special-case inspection | Identify whether current product runtime has target-specific blockers | Found likely blockers in `apps/api/app/services/conversation/intake.py`, `apps/api/app/services/conversation/chat_runtime.py`, and `apps/api/app/services/learning/learning_run_service.py`; eval runner constants remained under `scripts/evals/` | 0 | Pass | command output | Read-only inspection only; no runtime cleanup performed in this docs revision |
| placeholder scan for template tokens | No template placeholders | No matches | 1 | Pass | command output | exit `1` means `rg` found no matches |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py tests/test_wagent_runtime_eval.py tests/test_conversation_chat_runtime.py tests/test_conversation_intake.py tests/test_learning_run_service.py tests/test_learned_path_replay.py tests/test_conversation_replay_hook.py tests/test_replay_observation_summary.py -q` | Targeted runtime / eval regression passes | `267 passed in 9.41s` | 0 | Pass | command output | Runner unit coverage plus related runtime tests |
| `../../.venv/bin/ruff check tests/test_wagent_user_behavior_eval.py ../../scripts/evals/wagent_user_behavior_eval.py` | Lint passes | `All checks passed!` | 0 | Pass | command output | Runner / test lint |
| `pnpm run eval:wagent:user-behavior -- --case forbidden_test_target_not_in_runtime_code_or_prompts --json-only` | Static forbidden case can run without live API | `status=pass`, `exit_code=0` | 0 | Pass | command output | Static anti-hardcoding case only |
| `pnpm run eval:wagent:user-behavior -- --timeout 15` | Full runner emits artifact and honest non-pass when preflight blocked | `status=blocked`, exit `2`; API health connection refused | 2 | Blocked | committed JSON / Markdown artifact | This is not a behavior pass |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_result_gate_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json` | Committed JSON is not treated as pass | `decision=BLOCKED`, reason `top-level status is blocked` | 2 | Blocked | command output | Exit `2` is expected for blocked artifact |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-20260523T170951Z.json docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-20260523T170951Z.md` | Public artifact redaction passes | `status=pass`, `match_count=0` | 0 | Pass | command output | Applies to blocked artifact |
| `PYTHONPATH=. ../../.venv/bin/pytest tests/test_conversation_api.py tests/test_conversation_chat_runtime.py tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py tests/test_conversation_intake.py tests/test_learning_run_service.py tests/test_learned_path_replay.py tests/test_conversation_replay_hook.py tests/test_replay_observation_summary.py -q` | Targeted runtime / eval regression passes after gate fixes | `283 passed in 12.66s` | 0 | Pass | command output | Current code |
| `cd apps/api && ../../.venv/bin/python -m ruff check app/services/conversation/chat_runtime.py app/services/conversation/history.py app/services/learning/learning_run_service.py tests/test_conversation_api.py tests/test_conversation_chat_runtime.py tests/test_learning_run_service.py tests/test_wagent_user_behavior_eval.py tests/test_target_agnostic_runtime_cleanup.py` | Touched API/test lint passes | `All checks passed!` | 0 | Pass | command output | Current code |
| `pnpm run eval:wagent:user-behavior -- --timeout 300` | First-wave user-facing behavior gates pass | `status=pass`, exit `0`; all eight cases pass; latest artifact records commit `e91c0f5` | 0 | Pass | JSON / Markdown artifact | Clean HEAD rerun; API was started with the LLM provider env var empty; full learn-then-execute remains follow-up |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_result_gate_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json` | Latest JSON gate decision is pass | `decision=PASS`, reason `all detectable required gates/cases passed` | 0 | Pass | command output | Current latest artifact |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py artifacts/wagent-user-behavior-eval/wagent-user-behavior-eval-latest.json docs/testing/results/m11-11.3.7-user-facing-wagent-behavior-eval-latest.md` | Latest artifacts are redacted | `status=pass`, `match_count=0` | 0 | Pass | command output | Current latest artifact |
| `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/wagent-user-behavior-target-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1` | Product runtime / prompt target scan passes | `status=pass`, `match_count=0`, `missing_forbidden_paths=[]` | 0 | Pass | command output | Manifest extracted from eval-only spec |
| `git diff --check` | No whitespace errors | No output | 0 | Pass | command output | Current diff |

### 未运行 / 未验证（Not Run / Unverified）

| Item | Reason | Risk / Follow-up |
|---|---|---|
| Full `learn_then_execute` behavior | Latest artifact records staged learning-flow only | Remains non-required follow-up; do not claim full learn-then-execute |
| Console UI smoke | Not requested | UI-specific behavior remains unverified |
| `verify-scenario` / autonomous run | Out of scope and prohibited by default | No Supervisor pass_gate evidence claimed |

### 后续事项（Follow-ups）

- Keep target-specific test content out of feature code and product prompt assets.
- Implement full learn-then-execute later if it becomes a required capability.
