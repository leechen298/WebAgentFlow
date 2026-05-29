# 契约（Contract）

状态：ready for review

## Public Concepts

本包不新增产品 Agent 或 lifecycle stage，只细化已有 session learned action 的可复用业务身份。

新增 / 明确的 metadata 概念：

- `business_goal`：用户想学习的业务动作原文或清洗后的业务目标，例如 `Create inventory item`。
- `canonical_goal`：intake 给出的规范化动作名，例如 `create_inventory_item`。
- `action_aliases`：intake 或 deterministic normalizer 给出的有用业务别名，例如 `add inventory item`。
- `business_object`：从 `canonical_goal` / business goal 中可复用的对象短语，例如 `inventory item`。实现可以不新增独立字段，但必须提供等价的 matchable business-object term。
- `match_terms`：后续 matcher 可消费的目标无关业务词集合；本包只保存，不负责执行匹配策略。

`alias` 仍是用户可见 action label，但其主要来源应优先为 business identity，而不是 raw
`Learn how to ...` wrapper。

## Allowed Changes

后续实现可做：

- 扩展 `LearningRunRequest` / `LearningRunResult` 或 chat runtime 的 internal handoff，使 learning completion 可以携带 intake action metadata。
- 在 `_action_from_learning_result()` 保存 backward-compatible session action JSON keys。
- 改进 product-level action label construction，使 label 优先使用 business goal / canonical goal / aliases。
- 添加 focused tests 验证 metadata preservation。
- 小范围复用 intake normalization helper，但不得引入 target-specific logic。

## Forbidden Changes

本包不得：

- 修改 matcher confidence、candidate selection、multi-candidate choice、replay execution 或 Task Result Reporter 行为。
- 修改 suggested utterance policy beyond preserving existing compatibility; utterance quality belongs to 11.3.8.2。
- 新增 public API endpoint、DB migration、frontend UI、fixture site、worker flow 或 autonomous-run flow。
- 修改外部 Validation-Site / Fixture-Site，或恢复 `apps/product-test-site` / `apps/validation-site`。
- 把 `inventory item`、`5177/inventory`、selector、`data-testid`、seed data、field label、button text、placeholder、operation alias 或 page source 写入 runtime / prompts / active eval defaults。
- 把 focused unit tests 或 docs inspection 写成 external black-box validation pass。

## State / Result Contract

本包状态只能按 review / implementation 真实进度推进：

| Status | Meaning |
|---|---|
| `ready for review` | 七件套文档可 review；不得开始代码实现。 |
| `ready_for_implementation` | 仅在文档 / 设计 review 明确通过后可设置。 |
| `implementation_complete_pending_followup` | 后续实现和 focused tests 完成；11.3.8.2 仍需接手 utterances。 |
| `blocked` | 无法在不扩大 schema / API / target-specific scope 的情况下保存业务身份。 |

不得在本包把 `PV-CLI-003` 写成 fixed / passed / verified。

## Schema / API Contract

No public API endpoint changes are planned.

Allowed internal JSON compatibility:

- Session `metadata_json.learned_actions[]` may gain optional keys such as `business_goal`,
  `canonical_goal`, `action_aliases`, `business_object`, and `match_terms`.
- Existing learned action objects with only `alias`, `utterances`, `learned_path_id`, `target_url`,
  `site_origin`, `page_template`, and `scenario` remain valid.
- Any new keys must be optional for readers and serializers.
- Slot values remain execution parameters, not reusable action identity.

DB schema changes are not expected. If implementation concludes a migration is required, stop and update this contract before coding further.

## Evidence / Observation Contract

Allowed evidence for this package:

- focused pytest output for learning label / metadata preservation;
- focused chat runtime service tests proving session learned action metadata contains business identity;
- ruff / `git diff --check` / docs inspection output;
- review notes in this package.

Not allowed as pass evidence in this package:

- external black-box validation rerun;
- `verify-scenario`;
- direct `/exploration/autonomous-runs` or `/exploration/autonomous-runs/stream`;
- direct replay API, internal service import, hidden HTTP client, or ad hoc script as WAgent product validation.

## Compatibility Requirements

- Existing Chinese `登录` and `创建记录` learning flows must remain compatible.
- Existing consumers that display `alias` must continue to receive a safe, short label.
- Existing session actions without new metadata fields must still execute / clarify according to current behavior.
- Existing LearnedPath persistence schema and replay status semantics remain unchanged.
- Existing response provenance, public / private payload redaction, pending choice, recovery, and abort boundaries remain unchanged.

## Product Model / Scope / Roadmap Alignment

- Product model alignment: stays within L3 runtime chat learned action reuse.
- Scope boundary alignment: preserves "LLM understands language; code decides actions"; does not let LLM drive browser steps.
- Roadmap / milestone alignment: M11.3 post-closeout recovery follow-up under 11.3.8.
- Changes lifecycle stage / Agent role / milestone boundary: No.
- If Yes, authoritative docs to update first: N/A.

## Out-of-scope Follow-ups

- Reusable suggested utterances: `11.3.8.2`.
- Safe learned action matching: `11.3.8.3`.
- Cross-chain regression tests: `11.3.8.4`.
- External black-box revalidation / closeout: `11.3.8.5`.
- M12 recovery / retry / abort / interruption.
- Full page-wide automatic capability discovery or full learn-then-execute for arbitrary sites.

## Open Risks

- The current `LearningRunResult` does not include intake metadata; the reviewed implementation may need to add optional internal fields.
- Deriving `business_object` generically is easy to overfit; tests must verify target-agnostic examples and no target constants.
- Keeping `alias` short may conflict with preserving enough business meaning; the implementation should prefer metadata richness over label truncation when both cannot fit in one string.
