# Technical Design

状态：proposed

## Current State

Current capability discovery uses `PageAnalysis.fillable`, `toggle`, `select`, and `submit` collections to
build a filter inventory. 11.3.11 added terminal hints and terminal-state verdicts, but there is no
capability-specific hint projection that bounded learning can consume.

11.3.12.2 added `LearningBatch` and bounded policy execution. The default policy now avoids dependency pairs
unless explicitly enabled.

## Contract Alignment / Invariants

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Redacted page-level hints | New schema under `page_analysis.py` | schema tests | No raw DOM / route-specific text in normal projection |
| Region hints | deterministic helper in PageAnalyzer path | analyzer tests | Use generic region roles |
| Control hints | map discovered controls to capability kinds | unit tests | No direct Playwright payload |
| Public hints vs executable bindings | serialized hints carry redacted refs; private resolver retains bindings | schema / service tests | Prevent selector leakage while preserving execution |
| Sample value source semantics | enum-backed source kinds and redaction rules | schema / discovery tests | Redacted option values are evidence-only unless resolved privately |
| Dependency hints are opt-in | bounded discovery consumes only explicit groups | service tests | No default all-pairwise |
| Terminal targets | reuse terminal hint concepts where available | unit tests | Empty result can be weak valid evidence |
| Compatibility | existing PageAnalysis fields unchanged | existing tests | Hints optional / default empty |

## Proposed Implementation

### Files

Create:

- `apps/api/app/schemas/capability_hints.py`
- `apps/api/app/services/learning/capability_hints.py`
- `apps/api/tests/test_capability_hints.py`

Modify:

- `apps/api/app/schemas/page_analysis.py`
- `apps/api/app/services/learning/page_analyzer.py`
- `apps/api/app/services/learning/capability_discovery.py`
- `apps/api/tests/test_page_analyzer_selector.py`
- `apps/api/tests/test_filter_capability_discovery.py`
- focused updates in `apps/api/tests/test_learning_run_service.py`

Forbidden in this child:

- no Console UI;
- no runtime capability composition;
- no new LearnedCapability HTTP API;
- no direct autonomous-run endpoint calls;
- no target-specific runtime constants.

### Schemas

Add `capability_hints.py` with:

- `CapabilityHintSet`
- `RegionHint`
- `ControlCapabilityHint`
- `TerminalTargetHint`
- `SampleValueSourceHint`
- `DependencyHintGroup`
- enum / literal constraints for `page_purpose`, region roles, capability kinds, terminal target kinds, dependency
  kinds, source kinds, confidence, and support status

Extend `PageAnalysis` with optional/default `capability_hints: CapabilityHintSet`.

### Service Design

`capability_hints.py`:

- derives region hints from discovered element groups and terminal hints;
- derives control hints from fillable / toggle / select / submit elements;
- derives terminal target hints from result-region, URL query, modal, toast, download, and terminal hint signals;
- assigns stable redacted hint ids and never copies selectors, raw accessible labels, target values, DOM paths, or
  route-specific text into the serialized hint projection;
- builds a runtime-only resolver that maps hint ids to original `DiscoveredElement` bindings for the current
  analysis context;
- keeps the resolver out of Pydantic response models, persisted summaries, and LearnedCapability evidence;
- emits sample value source hints only from allowed source kinds:
  `generated_by_type`, `static_safe_default`, `empty_safe_probe`, `existing_option_value_redacted`, and
  `operator_supplied`;
- treats `existing_option_value_redacted` as evidence-only in serialized hints; execution may use the original option
  only through the private resolver in the same analysis context;
- derives dependency hints only when structural evidence supports a dependency.

`page_analyzer.py`:

- attaches `CapabilityHintSet` after existing analysis;
- keeps existing fields unchanged.

`capability_discovery.py`:

- prefers capability hints when present;
- falls back to current raw PageAnalysis-derived inventory when hints are absent;
- resolves planned scenarios back to executable bindings through the private resolver or the original discovered
  element inventory;
- fails closed when a hint cannot be resolved to an executable binding instead of serializing a selector into the
  public hint;
- only emits dependency-pair scenarios when both policy and dependency hints allow them.

## Data Flow

```text
PageAnalyzer
  -> PageAnalysis(existing fields)
  -> CapabilityHintSet(public redacted refs)
  -> private hint resolver(current analysis only)
  -> build_filter_inventory()
  -> generate bounded scenarios
  -> LearningBatch execution
```

## Reference Model

| Layer | Contains | May serialize? | May execute? |
|---|---|---|---|
| `CapabilityHintSet` | redacted hint ids, generic kinds, confidence, warnings | yes | no direct selector access |
| private hint resolver | hint id to `DiscoveredElement` / frame / selector binding | no | yes |
| current fallback inventory | existing PageAnalysis element collections | existing behavior | yes |
| LearnedCapability evidence | redacted summaries and provenance | yes | no raw target values |

The implementation may choose a small dataclass or internal mapping for the private resolver. It must stay process-local
to the current analysis / discovery call and must not be added to the public schema.

## Compatibility

- Existing tests that construct `PageAnalysis` without hints continue to work.
- Existing API responses include hints only as additive fields.
- Existing learning service can run when hints are absent.

## Failure / Edge Cases

- Ambiguous region: emit `unknown` role with warning rather than target-specific label.
- Unsupported control: keep hint with `support_status=unsupported`.
- Empty result: terminal target can be `empty_result` with weaker evidence.
- Redacted option values: may explain that a safe existing option was observed, but must not expose the option text /
  value in serialized hints.
- Missing resolver binding: skip or mark the capability unsupported; do not leak a selector as a fallback.
- Dependency uncertainty: do not emit dependency group.

## Non-goals

- No composition planner.
- No async learning job.
- No Console surface.
- No live validation.

## Test Matrix

- Schema defaults and redaction.
- Public hint refs remain redacted while internal discovery keeps executable bindings.
- Sample value source source-kind semantics and redacted option handling.
- Deterministic region / control / terminal hint derivation.
- Dependency hints are opt-in and do not re-enable default pairwise planning.
- Existing filter discovery fallback remains compatible.
- Hardcoding scan over runtime code.
