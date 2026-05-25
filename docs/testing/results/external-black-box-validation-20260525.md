# External Black-box Product Validation Report

Date: 2026-05-25 21:34:32 CST
Commit: `5d527774a9c4474e461ede83b48a168e0241eb4b`
Operator: Codex external test operator
Target URL: `http://127.0.0.1:5177/inventory`
Plan: `docs/testing/external-black-box-validation-plan.md`

## Result

Overall classification: `FAIL`

Reason: the external site smoke and integrity checks passed, but
`PV-CLI-003` contradicted the expected product behavior. WAgent did not start
execution for the learned create-inventory request. It responded that it had
learned only `Learn how to create` and had not learned the requested operation.

Manual smoke alone is not reported as full product capability coverage.

## Operator Surface

Commands / controls used:

- `pnpm run dev:api`
- `pnpm dev` in `/Users/leechen/projects/WebAgentFlow-Validation-Site`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i http://127.0.0.1:5177/inventory`
- Browser, in-app browser, opened `http://127.0.0.1:5177/inventory`
- `.venv/bin/wagent chat --api-base http://127.0.0.1:8001 --timeout 300 --headless`

WAgent session:

- `9f6c3610-b326-4f8b-887c-285dfaa8699d`

Forbidden direct product operation endpoint check:

- The operator did not call `/exploration/autonomous-runs` or
  `/exploration/autonomous-runs/stream`.
- API terminal observations during the WAgent run showed
  `POST /conversation/sessions` and
  `POST /conversation/sessions/9f6c3610-b326-4f8b-887c-285dfaa8699d/dispatch`.
- Product-internal autonomous exploration was triggered only through the WAgent
  CLI learning flow, not by an operator-side direct endpoint call.

## Preconditions

| Check | Result |
| --- | --- |
| API health | `HTTP/1.1 200 OK`; body `{"code":0,"data":{"status":"ok","database":"ok"},"msg":"ok"}` |
| Validation-Site health | `HTTP/1.1 200 OK` for `http://127.0.0.1:5177/inventory` |
| Main repo status before report | clean |

No pre-test database cleanup was performed. The WAgent CLI scenarios used the
current local API database state.

Note: the normal sandbox could not connect to the externally started
Validation-Site port, while the approved elevated health check returned 200.

## Scenario Results

| Scenario | Status | Evidence |
| --- | --- | --- |
| PV-SITE-001 Standalone inventory smoke | `PASS` | Browser opened `/inventory`; created `QA-COD-525` / `Codex Field Notebook`; search showed the item; edit changed stock to `37` and status to `paused`; no-match search showed `No inventory items found`. Screenshot captured at `/private/tmp/waf-external-validation-site-smoke.png`. |
| PV-CLI-001 URL-only known external page no execution | `PASS` | Input: `http://127.0.0.1:5177/inventory`. WAgent response: `还没学过这个页面。你可以先学习这个页面上的操作、查看页面，或取消。` No learning or execution started from the URL-only input. |
| PV-CLI-002 Learn create inventory item | `FOLLOW_UP` | Input: `Learn how to create an inventory item with SKU NB-ALP-001, name Alpine Notebook, category Stationery, and stock quantity 24.` WAgent response: `开始学习页面操作。` then `学习完成：我学会了Learn how to create 操作。之后你可以说“帮我Learn how to create ”。` Learning started and completed, but the learned operation label is generic and does not clearly represent "create inventory item". |
| PV-CLI-003 Execute learned create with new values | `FAIL` | Input: `Create an inventory item with SKU MUG-SKY-014, name Skyline Mug, category Office, and stock quantity 18.` WAgent response: `我学过这个页面的一些操作：Learn how to create。但还没学过你要做的这个操作。你可以先学习这个新操作，学会后再让我执行，或取消。` Execution did not start, and no visible execution evidence was produced. |
| PV-CLI-004 Vague input no execution | `PASS` | Input: `随便处理一下`. WAgent response: `请问您想在库存页面做什么操作？例如添加库存商品、查看列表等。` No learning or execution started. |
| PV-INTEGRITY-001 Main repo contains no external site source | `PASS` | No workspace dependency or package reference to `WebAgentFlow-Validation-Site` / `5177`; `.gitmodules` absent; no `apps/product-test-site` or `apps/validation-site` source files present. A filename scan found only legacy test/doc paths, not the external inventory site source. |
| PV-INTEGRITY-002 Runtime / prompt contains no validation-site answer key | `PASS` | `python3 .agents/skills/webagentflow-eval-integrity/scripts/forbidden_target_scan.py --manifest /private/tmp/waf-external-validation-target-manifest.json --root /Users/leechen/projects/WebAgentFlow/v0.1` returned `status=pass`, `match_count=0`, `missing_forbidden_paths=[]`. |

## Notes And Gaps

- The WAgent CLI surface did not provide final page evidence for `PV-CLI-003`
  because it refused to execute the request.
- `PV-CLI-002` produced a learned action name that is too generic for the
  planned expected result; this should be split into a follow-up before the
  external black-box path can be reported as passing.
- This run did not modify runtime code, prompts, package scripts, or iteration
  docs.
