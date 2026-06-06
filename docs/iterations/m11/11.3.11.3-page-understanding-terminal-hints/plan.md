# 实施计划（Implementation Plan）

状态：proposed

## 输入

- parent `11.3.11-terminal-state-agent-learning-stop-control`
- child 1 and child 2 docs/review
- `apps/api/app/schemas/page_analysis.py`
- `apps/api/app/services/learning/page_analyzer.py`
- conversation Page Understanding service for boundary reference

## 文档生成计划

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.11.3-page-understanding-terminal-hints/` |
| Package type | `code / mixed` |
| Required docs | seven-document set |
| Contract / status / evidence changes | Adds PageTerminalHintSet schema and deterministic extraction contract |
| Design-review gate | required before runtime implementation |
| Test-plan trigger | required due Agent/evidence semantics |
| Implementation authorization boundary | `review.md` must record `implementation_authorized: yes` before code |
| Stop conditions | selector leakage, target-specific rules, provider/live dependency, stop-controller scope drift |
| Handoff / checkpoint | child 4 consumes terminal hints + browser event timeline |

## 文件 / 模块

Allowed after authorization:

- `apps/api/app/schemas/terminal_hints.py`
- `apps/api/app/services/learning/terminal_hints.py`
- `apps/api/app/schemas/page_analysis.py` optional additive result field only
- `apps/api/app/services/learning/autonomous_explorer.py` optional metadata wiring only
- `apps/api/tests/test_terminal_hints.py`

Forbidden:

- LLM prompt/provider implementation.
- selectors/raw DOM paths in output.
- action planner / LearnedPath ingest / stop controller.
- UI/API route changes.
- live run artifacts.

## 步骤

1. Run design review and set implementation authorization.
2. Add schema and unit tests for synthetic PageAnalysis.
3. Implement deterministic terminal hints helper.
4. Optionally add autonomous result metadata wiring if low-risk.
5. Run required non-live tests and ruff.
6. Update `review.md` and parent route.

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_terminal_hints.py apps/api/tests/test_browser_event_recorder.py -q` | terminal hints and child 2 still pass | Yes | non-live |
| `uv run ruff check ...` | lint/import clean | Yes | changed files |
| `git diff --check` | whitespace clean | Yes | repo hygiene |

## 复核清单（Review Checklist）

- [ ] No selector/raw DOM leakage.
- [ ] Candidate terminal types match child 1 taxonomy.
- [ ] No LLM provider/live dependency.
- [ ] Existing PageAnalysis consumers remain compatible.
