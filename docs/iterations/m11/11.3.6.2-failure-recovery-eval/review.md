# 评审记录（Review）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## Current Decision

- Reviewer: pending
- Decision: pending
- Code: not_started
- Live eval: not_run

## Design Summary

本迭代计划在 11.3.6.1 runner core 之上增加 `failure_recovery_menu_safety` case，
验证 11.3.5.8 基础失败恢复菜单和 private payload safety。

## Review Checklist

- [ ] failure trigger contract 稳定且不污染普通 runtime。
- [ ] recovery gates 有明确 source 和 pass / fail semantics。
- [ ] private payload redaction 覆盖 retry / relearn / cancel 私有载荷。
- [ ] happy path no-recovery gate 不依赖 Codex 主观判断。
- [ ] direct replay / autonomous-run 边界清楚。
- [ ] live eval not-run 规则清楚。

## Not Run

- 未实现代码。
- 未运行 unit tests。
- 未运行 live Conversation eval。
- 未触发 autonomous run。

## Next Step

设计 review 通过后，按 `plan.md` 实现 runner case、必要的 eval-only hook、tests 和文档更新。
