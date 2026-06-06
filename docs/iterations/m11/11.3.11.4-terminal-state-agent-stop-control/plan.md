# 实施计划（Implementation Plan）

状态：PACKAGE_COMPLETE

## 输入

- child 1 taxonomy
- child 2 browser event timeline
- child 3 page terminal hints

## 文档生成计划

| Decision | Value |
|---|---|
| Target package path | `docs/iterations/m11/11.3.11.4-terminal-state-agent-stop-control/` |
| Package type | `code / mixed` |
| Required docs | seven-document set |
| Design-review gate | required |
| Test-plan trigger | required |
| Implementation authorization boundary | `review.md` must record `implementation_authorized: yes` |
| Stop conditions | false success, target-specific rules, live run without approval, ingest gate scope drift |
| Handoff / checkpoint | child 5 consumes TerminalStateVerdict |

## 文件 / 模块

Allowed:

- `apps/api/app/schemas/terminal_state.py`
- `apps/api/app/services/learning/terminal_state.py`
- optional additive `apps/api/app/schemas/page_analysis.py`
- optional metadata wiring in `apps/api/app/services/learning/autonomous_explorer.py`
- `apps/api/tests/test_terminal_state.py`

Forbidden:

- LearnedPath ingest.
- pass_gate/Supervisor semantics.
- UI/API routes.
- live validation.

## 步骤

1. Review and authorize.
2. Write schema/service tests.
3. Implement deterministic classifier.
4. Add optional result metadata wiring.
5. Run targeted tests/ruff/diff check.
6. Update review and parent route.

## 验证

| Command | Expected proof | Live autonomous verification excluded? | Notes |
|---|---|---|---|
| `PYTHONPATH=apps/api .venv/bin/pytest apps/api/tests/test_terminal_state.py apps/api/tests/test_terminal_hints.py apps/api/tests/test_browser_event_recorder.py -q` | terminal stack passes | Yes | non-live |
| `uv run ruff check ...` | lint/import clean | Yes | changed files |
| `git diff --check` | whitespace clean | Yes | repo hygiene |

## 复核清单

- [ ] Missing evidence does not produce success.
- [ ] Failed evidence produces unverified_stop/failure.
- [ ] No LearnedPath ingest change.
- [ ] No live validation.
