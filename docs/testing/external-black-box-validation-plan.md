# External Black-box Product Validation Plan

## Status

- Status: planned
- Scope: manual / operator-driven black-box validation
- Target: external WebAgentFlow-Validation-Site
- CI: not enabled by default

## Purpose

This plan defines product-like black-box validation for WebAgentFlow against an
external target site. It exists to keep the main repository from carrying its
own product test source, answer keys, or target-specific runtime assumptions
while still validating the user-facing `wagent` experience on a realistic page.

The first validation wave covers URL-only behavior, learning, executing a
learned action with new values, vague input handling, and evidence / reporting
quality. It is intentionally separate from deterministic Fixture-Site
regression.

## Repository Boundary

WebAgentFlow main repo does not depend on the external validation site:

- no workspace dependency
- no git submodule
- no copied source
- no runtime hardcoding
- no selector, `data-testid`, component, seed copy, or internal state copy

The target URL may appear in this plan and in later human-readable result
records. It must not become a runtime default, prompt answer key, eval default,
or package dependency.

## Target Site

```text
WebAgentFlow-Validation-Site
http://127.0.0.1:5177/inventory
```

This URL belongs to the operator execution context. WebAgentFlow receives it as
a user-provided URL through the CLI or UI surface.

Fixture-Site remains a different role:

```text
WebAgentFlow-Fixture-Site
http://127.0.0.1:5175
deterministic regression fixture using /validation-api and web/specs
```

## Preconditions

1. WebAgentFlow API is running:

   ```bash
   cd /Users/leechen/projects/WebAgentFlow/v0.1
   pnpm run dev:api
   ```

2. External Validation-Site is running:

   ```bash
   cd /Users/leechen/projects/WebAgentFlow-Validation-Site
   pnpm dev
   ```

3. Optional health checks:

   ```bash
   curl -i http://127.0.0.1:8001/health
   curl -i http://127.0.0.1:5177/inventory
   ```

## Execution Surface

Use `wagent chat` as the operator surface:

```bash
cd /Users/leechen/projects/WebAgentFlow/v0.1

.venv/bin/wagent chat \
  --api-base http://127.0.0.1:8001 \
  --timeout 300 \
  --headless
```

Visible mode is also allowed for manual observation:

```bash
.venv/bin/wagent chat \
  --api-base http://127.0.0.1:8001 \
  --timeout 300
```

Do not call autonomous-run endpoints directly. Do not use internal service
imports or hidden HTTP clients as a substitute for the CLI operator surface.

## Scenario Matrix

### PV-SITE-001 Standalone inventory smoke

Purpose:

- Confirm the external site itself works before invoking `wagent`.

Steps:

- Open `http://127.0.0.1:5177/inventory`.
- Create an inventory item.
- Search for the created item.
- Edit stock or status.
- Search a no-match value and observe the empty state.

Expected:

- Site remains usable.
- Create, search, edit, and empty state behavior are visible.

### PV-CLI-001 URL-only known external page no execution

Input:

```text
http://127.0.0.1:5177/inventory
```

Expected:

- `wagent` does not execute.
- `wagent` asks what the user wants to learn or do next.
- No learning or execution starts.

### PV-CLI-002 Learn create inventory item

Input:

```text
Learn how to create an inventory item with SKU NB-ALP-001, name Alpine Notebook, category Stationery, and stock quantity 24.
```

Expected:

- Learning flow starts.
- Learned action represents creating an inventory item.
- No hidden autonomous endpoint is used outside the expected product flow.

### PV-CLI-003 Execute learned create with new values

Input:

```text
Create an inventory item with SKU MUG-SKY-014, name Skyline Mug, category Office, and stock quantity 18.
```

Expected:

- Execution starts.
- Visible page evidence verifies the new item.
- Final response references `MUG-SKY-014` or `Skyline Mug`.
- Result is not based on selector or `data-testid` knowledge from the main repo.

### PV-CLI-004 Vague input no execution

Input:

```text
随便处理一下
```

Expected:

- No execution starts.
- No learning starts.
- `wagent` asks for a target page or operation detail.

### PV-INTEGRITY-001 Main repo contains no external site source

Expected:

- Main repo does not contain `WebAgentFlow-Validation-Site` source.
- No workspace, submodule, or dependency points to the external site.
- Product validation source has not been copied back into the main repo.

### PV-INTEGRITY-002 Runtime / prompt contains no validation-site answer key

Expected:

- Runtime and prompts do not contain selectors, components, seed copy, or
  implementation details from the external Validation-Site.
- Target URL may appear in plans, docs, and result records, but not in runtime
  or prompt defaults.

## Evidence Requirements

Every validation report must record:

- date
- commit
- operator
- target URL
- `wagent` command
- exact user inputs
- observed `wagent` responses
- visible page evidence
- whether execution started
- whether learning started
- whether result was verified, uncertain, or failed
- whether forbidden direct endpoint usage was checked
- notes and gaps

## Result Classification

- PASS: required scenario expectations were met with reviewable evidence.
- FAIL: the scenario ran and contradicted one or more required expectations.
- BLOCKED: required services, credentials, target site, or operator surface were
  unavailable, or the run would violate validation boundaries.
- FOLLOW_UP: the run produced useful evidence but exposed incomplete coverage,
  ambiguous behavior, or a gap that should be split into a follow-up task.

Manual smoke alone must not be reported as full product capability coverage.

## Non-goals

- Not replacing deterministic Fixture-Site regression.
- Not running legacy `5176/items` eval.
- Not adding a CI requirement yet.
- Not modifying WebAgentFlow runtime.
- Not teaching WebAgentFlow selectors or implementation details.
- Not asserting full product capability if only manual smoke passed.

## Relationship to Legacy Evals

M11.3 legacy `5176/items` evals are historical. They are retained only for
historical reproduction and are not the current product-level validation entry.

This plan is the replacement direction for product-like black-box validation.
It does not reuse legacy `item-list`, `item_name`, or old product-test-site
assumptions.

## Future Automation

Future automation may convert selected scenarios into an explicit eval runner.
Any runner must accept target URL / scenario inputs at runtime, keep gates at
the user-visible behavior level, avoid selectors and target implementation
details, and never reintroduce external validation site source into the main
repository.
