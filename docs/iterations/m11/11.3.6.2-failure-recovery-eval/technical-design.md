# 技术设计（Technical Design）

状态：draft_for_review（failure recovery eval 设计稿，未实现代码）

## 当前状态（Current State）

11.3.5.8 已实现基础失败恢复菜单和 private payload safety targeted tests。11.3.6.1 负责
runner core、Conversation API driver、evidence collector、gate evaluator 和 artifact writer。

11.3.6.2 不重新设计 runner 框架，而是在 runner core 上增加一个 case family：

```text
failure_recovery_menu_safety
```

## Design Overview

```text
Config / CLI
  -> Case registry
  -> ConversationDriver
  -> Failure trigger
  -> EvidenceCollector
  -> GateEvaluator
  -> ArtifactWriter
  -> Exit reducer
```

### Case Registry

新增 case id：

```text
failure_recovery_menu_safety
```

可选 npm script：

```bash
pnpm run eval:wagent:failure-recovery
```

该 script 应等价于调用 runner 的 failure recovery case，不得绕过 Conversation API。

### Conversation Flow

推荐实现流程：

```text
create_session(metadata.client=wagent_eval)
setup /items learned path if needed
send execute turn with eval fault injection metadata
collect messages / events / history
evaluate recovery gates
write JSON + Markdown
```

如果 11.3.6.1 runner 已支持 case dependency / setup reuse，可以复用 `items_closed_loop` 的
learning result；否则本 case 内显式完成最小 setup，并在 artifact 中记录 setup turn。

## Failure Trigger Design

首选策略是最小 eval-only hook，而不是破坏页面或依赖不稳定 DOM。

### Eval-only Hook

候选 hook 位于 Conversation runtime 的 reporter / recovery 交界处，只允许把本次 eval turn
的 reporter outcome 强制降级为 `needs_review` 或 evidence status 强制为 `missing`。

生效条件必须同时满足：

- session 或 dispatch metadata `client == "wagent_eval"`。
- metadata 包含 `eval_fault_injection.case_id == "failure_recovery_menu_safety"`。
- fault class 在 allowlist 内。

不满足这些条件时，runtime 行为必须完全等同当前产品路径。

### Hook Event

如果需要记录 hook 事件，事件 payload 只能包含脱敏信息：

```json
{
  "case_id": "failure_recovery_menu_safety",
  "fault_class": "needs_review"
}
```

不得写入 private retry payload、selector、slot overrides 或 learned path id。

### No-hook Fallback

如果实现阶段确认现有 runtime 已有稳定 failure path，可以不加 hook，但必须在 review 中记录
触发方式和 evidence。若只使用 non-live fixture，则只能证明 evaluator / artifact 行为，不能声称
live runtime eval pass。

## Evidence Collection

EvidenceCollector 需要读取：

- session detail。
- messages。
- events。
- history。
- raw dispatch responses。
- runner request log。

Gate evaluator 不得把 final assistant text 当作 private payload safety 的唯一来源。visible
reply 只能证明 menu 文案；private payload safety 还需要检查 public messages、session public
payload、events 和 history 的 redacted surface。

## Gate Evaluation

新增 evaluator helpers：

- detect recovery failure class。
- parse visible A/B/C recovery menu。
- check retry wording and side-effect warning。
- scan visible / public payload for forbidden private tokens。
- detect recovery events and verify sanitized payload。
- verify happy-path response has no recovery menu.

Private payload scan 应覆盖大小写和 snake/camel variants，例如：

```text
learned_path_id
slot_overrides
evidence_targets
ReplayAction
execution_payload
private_retry_payload
pending_choice_private_map
selector
xpath
credential
authorization
```

对于 `selector` 这类可能出现在普通英文说明中的词，gate evidence 需要保留匹配 path / context，
避免误判时难以审计。

## Artifact Writer

沿用 11.3.6.1 artifact writer。Markdown result 需要新增：

- failure trigger type。
- recovery failure class。
- menu text excerpt。
- private payload scan result。
- retry not-run statement。

如果没有执行 live recovery case，Markdown result 必须写：

```text
Live Conversation eval: not run
```

## Compatibility

本迭代允许的代码改动范围：

- `scripts/evals/wagent_runtime_eval.py`
- `apps/api/tests/test_wagent_runtime_eval.py`
- `docs/testing/wagent-runtime-eval.md`
- `package.json`
- 必要时的最小 eval-only hook 和对应 targeted tests

除 eval-only hook 外，不修改 TaskResultReporter、TaskPathPlanner、LearnedPath replay execution
的产品语义。若实现发现需要改变产品 recovery contract，必须先回到本迭代文档修订并重新 review。
