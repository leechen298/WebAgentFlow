# External Black-box Product Validation Report

Date: 2026-05-29 22:32:03 CST
Commit: working tree after `11.3.8.6` implementation, before final commit
Operator: Codex external test operator
Target URL: `http://127.0.0.1:5177/inventory`
Plan: `docs/testing/external-black-box-validation-plan.md`

## Result

Overall classification: `PASS`

Reason: all approved scenarios ran against the external Validation-Site target.
The required WAgent learn-then-execute path passed through the approved
`wagent chat` product CLI surface. The learned create operation was executed
with new values, replay completed with `replay_status=succeeded`,
`drift_status=none`, and Task Result Reporter evidence marked the task
`verified`.

## Operator Surface

Commands / controls used:

- `pnpm run dev:api`
- `pnpm dev` in `/Users/leechen/projects/WebAgentFlow-Validation-Site`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i http://127.0.0.1:5177/inventory`
- `.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300 --headless`
- Playwright browser smoke against `http://127.0.0.1:5177/inventory`

WAgent session:

- `44f660a1-b401-4750-add3-bf1d985a6329`

Learning run:

- `04238a54-7847-459d-9148-831ad2a9434c`

Forbidden direct product operation endpoint check:

- The operator did not call `/exploration/autonomous-runs` or
  `/exploration/autonomous-runs/stream`.
- API terminal observations during the WAgent run showed Conversation API
  traffic. Product-internal learning / replay browser work was triggered only
  through the WAgent CLI flow, not by an operator-side direct endpoint call.
- Direct replay API product validation was not used.

## Preconditions

| Check | Result |
| --- | --- |
| API health | `HTTP/1.1 200 OK`; body `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}` |
| Validation-Site health | `HTTP/1.1 200 OK` for `http://127.0.0.1:5177/inventory` |
| DB state policy | clean database; `conversation_events`, `conversation_messages`, `conversation_sessions`, `learned_paths`, and `exploration_runs` all verified count `0` before the passing WAgent run |
| Latest result docs update | approved by user in-thread |

## Scenario Results

| Scenario | Status | Evidence |
| --- | --- | --- |
| PV-SITE-001 Standalone inventory smoke | `PASS` | Browser smoke created `QA-COD-529G` / `Codex Validation Marker G`; search showed the item; edit changed stock to `43` and status to `paused`; no-match search showed `No inventory items found`. Screenshot: `/private/tmp/waf-11.3.8.5-site-smoke-rerun.png`. |
| PV-CLI-001 URL-only known external page no execution | `PASS` | Input: `http://127.0.0.1:5177/inventory`. WAgent response: `还没学过这个页面。你可以先学习这个页面上的操作、查看页面，或取消。` No learning or execution started from the URL-only input. |
| PV-CLI-002 Learn create inventory item | `PASS` | Input: `Learn how to create an inventory item with SKU NB-ALP-001, name Alpine Notebook, category Stationery, and stock quantity 24.` WAgent response included `开始学习页面操作。` and `学习完成：我学会了create inventory item操作。之后你可以说“帮我create inventory item”。` Event `chat_learning_completed` recorded alias `create inventory item` and canonical goal `create_inventory_item`. |
| PV-CLI-003 Execute learned create with new values | `PASS` | Input: `Create an inventory item with SKU MUG-SKY-014, name Skyline Mug, category Office, and stock quantity 18.` WAgent response: `执行中。` then `执行完成。页面证据已确认目标值“MUG-SKY-014”。` Events recorded `chat_execution_completed`, `replay_status=succeeded`, `drift_status=none`, and `verification_outcome=verified`; page evidence verified `MUG-SKY-014`, `Skyline Mug`, `18`, and `Office`. |
| PV-CLI-004 Vague input no execution | `PASS_WITH_CAVEAT` | Input: `随便处理一下`. WAgent returned the normal non-web guidance response. No learning or execution started. Caveat: entry gate used deterministic fallback after timeout, but the no-execution gate held. |
| PV-INTEGRITY-001 Main repo contains no external site source | `PASS` | Main repo did not restore Validation-Site source. External target was started from `/Users/leechen/projects/WebAgentFlow-Validation-Site`. |
| PV-INTEGRITY-002 Runtime / prompt contains no validation-site answer key | `PASS` | `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/waf-external-validation-target-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1` returned `status=pass`, `match_count=0`, `missing_forbidden_paths=[]`. |

## Artifacts

- `artifacts/external-black-box-validation/11.3.8.5-20260529T143203Z-summary.json`
- `artifacts/external-black-box-validation/11.3.8.5-20260529T143203Z-messages.json`
- `artifacts/external-black-box-validation/11.3.8.5-20260529T143203Z-events.json`

## Notes And Gaps

- This report replaces the 2026-05-25 `FAIL` latest result because the user
  approved latest-result-doc updates and the rerun produced reviewable pass
  evidence.
- `PV-CLI-004` is a pass for the no-execution requirement, with a documented
  entry-gate timeout fallback caveat.
- No `verify-scenario` run was performed; this validation belongs to the
  `wagent chat` external black-box surface.
