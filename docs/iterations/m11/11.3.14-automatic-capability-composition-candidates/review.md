# Review

状态：REPO_LOCAL_NON_LIVE_IMPLEMENTATION_READY_FOR_REVIEW

## Current Decision

- implementation_authorized: yes
- live_validation_authorized: no
- docs_review_status: implementation authorization review complete
- implementation_status: repo-local non-live implementation ready for second
  code review
- next_action: second code review, then live validation / `wagent chat` /
  live Postgres migration before any `PACKAGE_COMPLETE` claim

## Current Findings

Existing `11.3.12.4-capability-composition-runtime` provides a deterministic composer and promotion guard, but it does
not implement the automatic product chain requested here:

- no automatic candidate family generation；
- no bounded page capability graph traversal；
- no candidate execution loop；
- no successful candidate LearnedPath write；
- no provider-evaluable redacted learning evidence bundle。

Therefore this package is a valid follow-up rather than a duplicate of 11.3.12.4。

Subagent read-only review also confirmed that WebAgentFlow already records useful evidence across
PageAnalysis, capability hints, LearnedCapability, LearnedPath, LearningBatch, ExplorationRun,
terminal verdict, ingest evaluation, and conversation history. The gap is not lack of raw evidence；
the gap is a stable redacted `waf.learning_evidence_bundle.v1` that Validation Site can evaluate
without direct DB access or provider-oracle leakage。

Implementation authorization review resolved the blocking design gaps:

- Persistence decision: use a new `composition_candidates` table instead of
  overloading `LearningBatch.summary_json` or `ExplorationRun.strategy_json`.
- Public target scope decision: provider-facing bundles use `target_scope_ref`
  and redacted refs instead of publishing full target URLs, selectors, seed copy,
  or provider oracle details.
- Test-plan decision: scoped pytest, ruff, redaction checks when artifacts exist,
  and `git diff --check` are the required closeout commands.
- Live validation remains unauthorized.

## Docs Generated

- README.md
- intent.md
- contract.md
- technical-design.md
- test-plan.md
- plan.md
- review.md

## Runtime Changes Implemented

- Added durable `CompositionCandidate` ORM, repository, and Alembic migration.
- Added `CompositionCandidate` request/status/public/coverage schemas.
- Added bounded family candidate generator that reuses existing
  `CapabilityComposer` for fail-closed static checks.
- Added page-scope generation entry point that loads capabilities from
  `LearnedCapabilityRepository` and derives bounded families from user goal
  text when no explicit family list is provided.
- Added Chinese intent keyword support for bounded family derivation
  (`搜索` / `查询` / `筛选`, `导出` / `下载`, `详情`, `重置`).
- Added candidate executor that reconstructs private execution handoff from the
  persisted candidate and source capabilities, records runtime execution
  outcomes, and keeps clean browser mechanics `unverified` until an approved
  pass gate is available.
- Added promotion service split into two gates: record execution result first,
  then promote only a persisted `execution_passed` candidate after pass gate,
  terminal evidence, attempt ingest, and composition promotion checks.
- Added redacted `waf.learning_evidence_bundle.v1` schemas and bundle builder
  with opaque candidate/capability refs, `target_scope_ref`, batch scoping,
  redacted rejection reasons, and execution gate summary.
- Removed raw `source_capability_ids` from `CompositionCandidatePublic`; public
  projection exposes only opaque `source_capability_refs`.
- Added focused `LearnedCapabilityRepository.list_for_page_scope()` helper.
- Added tests for bounded candidate generation, static rejection, promotion,
  and bundle redaction.

## Review Repair Findings

- P0 fixed: `CompositionPromotionService` no longer writes `LearnedPath` from
  caller-provided `status="success"` alone. `record_execution_result()` requires
  pass gate status, terminal-state verdict, and eligible `AttemptIngestEvaluation`;
  `promote_executed_candidate()` only promotes persisted `execution_passed`
  candidates.
- P1 fixed: the previous test that allowed a failed candidate to later promote
  has been replaced. Failed / unverified candidates remain
  `negative_evidence_recorded` and cannot be promoted in the same lifecycle.
- P1 fixed for repo-local implementation: generator supports repo-backed
  page-scope capability loading, bounded family derivation, Chinese intent
  terms, and executor handoff reconstruction. This remains non-live until
  product-path validation is authorized and run.
- P1 partially fixed: bundle export is now batch-scoped and includes execution
  gate summaries for executed candidates, but provider evaluation still requires
  a real runtime execution artifact.
- P1 fixed: public candidate projection and bundle rejection reasons redact raw
  capability ids, selectors, target URLs, and secret/token/cookie-like key/value
  pairs before export.
- P2 fixed: regenerated candidates no longer regress terminal candidate states.
- P2 fixed: `list_for_page_scope()` avoids PostgreSQL JSON equality by filtering
  query signature in Python after SQL-safe page / trust / fingerprint filters.

## Commands Run

Docs generated and reviewed by local file editing.

Read-only checks:

- `rg` scanned this package, M11 index, and roadmap for `11.3.14`,
  `CompositionCandidate`, `waf.learning_evidence_bundle.v1`, implementation authorization,
  provider oracle, coverage, and promotion references.
- `rg -n "[ \t]+$"` found no trailing whitespace in the package, M11 index, or roadmap.
- Codex parent agent and three read-only subagents reviewed the docs gate,
  current 11.3.12.4 composer implementation, and evidence/redaction boundary.

Implementation checks:

- `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_capability_composition_candidates.py -q`
  first failed as expected with `ModuleNotFoundError: No module named
  'app.models.composition_candidate'` before implementation.
- Review repair TDD failures were reproduced before fixes:
  promotion API missing pass/ingest gate parameters, terminal candidate status
  regression, missing bundle batch scope, missing repo-backed generation, and
  missing execution gate summary.
- `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_capability_composer.py apps/api/tests/test_capability_composition_candidates.py apps/api/tests/test_learning_run_service.py apps/api/tests/test_conversation_chat_runtime.py apps/api/tests/test_learning_evidence_bundle.py -q`
  passed after review repair and public-schema / Chinese-intent follow-up:
  184 passed.
- `uv run ruff check apps/api/app/services/learning apps/api/app/schemas apps/api/tests/test_capability_composition_candidates.py`
  passed.
- `uv run ruff check apps/api/app/models/composition_candidate.py apps/api/app/repos/composition_candidates_repo.py apps/api/app/repos/learned_capabilities_repo.py apps/api/alembic/versions/20260607_0001_add_composition_candidates.py apps/api/tests/test_learning_evidence_bundle.py`
  passed.
- `git diff --check` passed.
- `rg -n "validation\\.example\\.invalid|secret=seed|seed=hidden|cap-private|cap-region-private-id|cap-export-private-id" apps/api/app apps/api/alembic apps/cli/wagent apps/console/src`
  returned no matches in product runtime / prompt / frontend surfaces.
- `.venv/bin/python .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py /private/tmp/waf_11_3_14_bundle.json`
  passed on a temporary exported bundle artifact after review repair: status pass, 0 matches.

Redaction helper notes:

- `python .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py --root ...`
  failed because this script version has no `--root` option.
- `.venv/bin/python ... eval_artifact_redaction_check.py docs/iterations/m11/11.3.14-automatic-capability-composition-candidates`
  failed because design docs intentionally mention forbidden terms while
  defining the redaction policy; `test-plan.md` was corrected to run this
  helper only against exported bundle / result artifacts.
- The first temporary bundle scan failed on field name
  `private_execution_payloads_excluded`; the public bundle schema was corrected
  to `private_payloads_excluded`, then the helper passed.

## Commands Not Run

- live validation
- `verify-scenario`
- `wagent chat`
- online DB migration against a live Postgres instance

## Design Review Checklist

- [x] Does the package avoid reopening 11.3.12.4?
- [x] Does candidate generation remain bounded?
- [x] Does promotion require execution evidence?
- [x] Does `waf.learning_evidence_bundle.v1` avoid provider oracle leakage and direct DB coupling?
- [x] Are composition coverage metrics clear enough for Validation Site evaluation?

Passing this checklist plus the resolved persistence / redaction / test-plan
decisions authorizes implementation for the reviewed runtime slice only.

## Closeout Caveats

- This is not a `PACKAGE_COMPLETE` claim. It is a repo-local non-live
  implementation ready for second code review. No autonomous run,
  `verify-scenario`, Console UI smoke, or `wagent chat` live product validation
  was run.
- The package does not add a public autonomous-run caller and does not call the
  autonomous-run endpoints directly.
- Live Postgres migration remains unverified.
- Provider oracle evaluation remains outside WebAgentFlow runtime. WebAgentFlow
  exports only the redacted bundle projection.
