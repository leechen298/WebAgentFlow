# 实施计划（Implementation Plan）

状态：PACKAGE_COMPLETE

## 输入

- Child 2 browser event timeline.
- Child 4 terminal verdict.
- Child 5 attempt ingest evaluation.
- Existing autonomous run detail API and Console detail page.

## 步骤

1. Add child docs and review scope.
2. Add Console evidence summary card.
3. Add locale keys.
4. Add component regression.
5. Add API/read-model regression if missing.
6. Run targeted tests and diff check.
7. Close parent campaign.

## Stop Conditions

- UI invents pass/fail status instead of rendering persisted evidence.
- UI exposes raw request/response body or secrets.
- Implementation triggers live autonomous validation.
- Any prior child regression fails.

## Checklist

- [x] Evidence summary renders compact persisted fields.
- [x] Legacy results hide the summary.
- [x] No live validation.
- [x] Parent campaign closeout updated.
