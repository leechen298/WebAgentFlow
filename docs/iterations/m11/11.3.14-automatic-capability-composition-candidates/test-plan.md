# Test Plan

状态：reviewed_for_implementation

## Unit Tests

### CapabilityGraphBuilder

- Groups capabilities by kind。
- Rejects cross-page capabilities。
- Preserves negative / unsupported reasons。
- Does not expose raw selectors in public summary。

### CompositionRequirementDeriver

- Derives `filters_then_submit` from search/filter intent。
- Derives `filters_then_export` from export intent。
- Derives `filter_then_open_detail` from detail intent。
- Rejects missing required families when no terminal action exists。

### BoundedCompositionCandidateGenerator

- Generates bounded candidate families。
- Does not generate exponential permutations。
- Dedupes identical source capability sets。
- Rejects conflicting controls。
- Computes candidate coverage metrics。

### CompositionCandidateExecutor

- Executes candidate with ordered action schemas。
- Records pass / fail / unverified。
- Records terminal evidence。
- Records negative evidence on failure。

### Promotion Service

- Promotes only execution-passed eligible candidates。
- Does not promote static rejected / failed / unverified candidates。
- Preserves source capability ids。
- Dedupe behavior works。

### Learning Evidence Bundle Builder

- Includes detected components, learned capabilities, learned paths, composition candidates, execution outcomes, and promotion decisions。
- Redacts forbidden target details。
- Does not include provider oracle answers。
- Includes operator action metadata for the approved validation surface。
- Does not expose raw DB rows, private execution handoffs, selectors, DOM, seed copy, cookies, or credentials。

## Integration Tests

- Learning batch with several capabilities produces bounded composition candidates。
- Existing high-confidence LearnedPath is preferred over composition。
- No LearnedPath exists -> ready candidate can execute and promote after pass evidence。
- Failed candidate remains negative evidence。
- Conversation history can display composition summary without private payload。
- Exported `waf.learning_evidence_bundle.v1` can be consumed by an external provider validator without DB access。

## Regression Tests

- Existing `CapabilityComposer` unit tests continue passing。
- Existing LearnedPath replay tests continue passing。
- Existing learning batch and chat tests continue passing。
- No target hardcoding appears in runtime / prompts。

## Metrics Tests

- Candidate family coverage is computed correctly。
- Critical capability participation coverage is computed correctly。
- Promotion reliability is 1.0 when all promoted candidates pass。
- Promotion reliability fails when any promoted path lacks eligible evidence。

## Commands

Implementation closeout must run:

```bash
PYTHONPATH=apps/api .venv/bin/pytest \
  apps/api/tests/test_capability_composer.py \
  apps/api/tests/test_capability_composition_candidates.py \
  apps/api/tests/test_learning_run_service.py \
  apps/api/tests/test_conversation_chat_runtime.py \
  apps/api/tests/test_learning_evidence_bundle.py -q

uv run ruff check \
  apps/api/app/services/learning \
  apps/api/app/schemas \
  apps/api/tests/test_capability_composition_candidates.py

git diff --check
```

The pytest command is required. The ruff command is required when `uv` is
available in the current environment; if `uv` is unavailable, record the exact
environment blocker instead of substituting a weaker claim.

Run the WebAgentFlow evidence-integrity helper checks when exported bundle or
result artifacts exist. Do not run this helper against the design docs
themselves; the docs intentionally name forbidden terms while defining the
redaction policy.

```bash
python .agents/skills/webagentflow-eval-integrity/scripts/eval_artifact_redaction_check.py \
  <path-to-exported-bundle-or-result-artifact>
```

If a stable latest JSON result is produced, also run:

```bash
python .agents/skills/webagentflow-eval-integrity/scripts/eval_result_gate_check.py \
  --result-json <path-to-json-result>
```

Live validation remains not run unless separately authorized。

## Hard Stops

Stop implementation if:

- design requires Validation Site oracle in runtime；
- implementation would call autonomous-run endpoints directly for tests；
- generated candidates can become LearnedPath without execution evidence；
- LLM is asked to output browser steps；
- target-specific constants appear in product runtime or prompts。
