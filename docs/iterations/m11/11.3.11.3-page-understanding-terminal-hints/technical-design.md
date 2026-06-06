# 技术设计（Technical Design）

状态：proposed

## 当前状态（Current State）

PageAnalysis 已提供 categorized interactive elements。Conversation Page Understanding 已有
deterministic service，但当前 runtime learning path 尚没有 terminal hints schema 或 extraction helper。

## 合约对齐 / 不变量（Contract Alignment / Invariants）

| Contract requirement | Implementation mechanism | Test coverage entry | Notes |
|---|---|---|---|
| Terminal hints are semantic, not executable | Schema omits selectors/raw DOM paths | boundary tests | No target_selector output |
| Candidate terminal types use child 1 taxonomy | Literal / string constants | unit tests | Child 4 consumes |
| Existing PageAnalysis consumers compatible | Add optional helper/schema only | existing targeted tests | No PageAnalysis required-field change |
| No LLM/browser live dependency | Deterministic bridge from PageAnalysis | unit tests | Provider future work |

## 实现方案（Proposed Implementation）

Expected implementation units:

- `apps/api/app/schemas/terminal_hints.py` or similar focused schema module.
- `apps/api/app/services/learning/terminal_hints.py` deterministic extraction helper.
- Optional `page_terminal_hints` field on `AutonomousExplorationResult` if child 4 needs result bundling.
- Tests in `apps/api/tests/test_terminal_hints.py` using synthetic PageAnalysis.

## 影响面（Affected Surfaces）

| Surface | Changed? | Description | Compatibility notes |
|---|---|---|---|
| API routes | No | N/A | N/A |
| API response schema | No by default | Optional result metadata only | Backward compatible |
| Database schema / migration | No | N/A | N/A |
| CLI | No | N/A | N/A |
| Console UI | No | Child 6 owns display | N/A |
| Conversation events | No | N/A | N/A |
| Replay execution | No | N/A | N/A |
| Reporter | No | N/A | N/A |
| Worker / async jobs | No | N/A | N/A |
| Tests / fixtures | Yes | Synthetic PageAnalysis tests | Non-live |
| Docs | Yes | Child review | N/A |

## 数据模型 / Schema 变更（Data Model / Schema Changes）

Add optional schema:

- `PageRegionHint`
- `PossiblePageFunction`
- `CandidateTerminalStateHint`
- `PageTerminalHintSet`

No DB migration.

## 服务 / 模块设计（Service / Module Design）

Suggested function:

```text
build_page_terminal_hints(analysis: PageAnalysis) -> PageTerminalHintSet
```

Rules:

- fillable/search/select/toggle + submit controls -> search/filter function, list_refresh/network_completion/region_changed.
- submit + fillable controls -> submit/create/update form, navigation/toast_or_status/region_changed.
- clickable with export/download content hint/text -> export/download, download_started/network_completion.
- clickable/navigation elements -> navigation/detail/open, navigation/modal_or_popup_opened.
- no controls -> generic no_observable_change fallback.

## 数据流（Data Flow）

```text
PageAnalysis
  -> deterministic terminal hint extraction
  -> optional result metadata
  -> child 4 combines with BrowserEventTimeline and DOM snapshots
```

## 状态推导（Status / State Derivation）

- `confidence=0.75` when multiple strong structural signals exist.
- `confidence=0.6` when one functional group exists.
- `confidence=0.35` for fallback/no-control pages.
- `source=deterministic` unless no meaningful signals, then `fallback`.

## 兼容性（Compatibility）

No existing caller must provide terminal hints. Missing hints are valid and child 4 must handle absent data.

## 失败 / 边界情况（Failure / Edge Cases）

- Ambiguous generic buttons: emit generic `operate_page` with low confidence, not target-specific function.
- Raw labels may be summarized but cannot become hardcoded runtime rules.
- Selectors are ignored in output.

## 非目标（Non-goals）

- No prompt/provider implementation.
- No terminal verdict or stop decision.
- No LearnedPath ingest change.
- No live validation.

## 测试矩阵入口（Test Matrix）

| Test area | Coverage goal | Detailed plan |
|---|---|---|
| Synthetic PageAnalysis | page classes produce expected possible functions | `test-plan.md` |
| Boundary | no selector/raw DOM output | `test-plan.md` |
| Compatibility | old PageAnalysis/result consumers unaffected | `test-plan.md` |

## 验证命令入口（Validation Commands）

```bash
PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_terminal_hints.py apps/api/tests/test_browser_event_recorder.py -q
uv run ruff check apps/api/app/schemas/terminal_hints.py apps/api/app/services/learning/terminal_hints.py apps/api/tests/test_terminal_hints.py
git diff --check
```
