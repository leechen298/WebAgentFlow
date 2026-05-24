# 11.3.8 External Validation Sites Separation

## Goal

Move validation site source code out of the WebAgentFlow main repository while keeping the evaluation protocol, manifests, runner integration, result artifacts, and review records in the main repository.

The separation should make WebAgentFlow behave more like a runtime / agent product and less like a project that carries both the exam and the answer key in the same tree.

## Current problem

`apps/product-test-site` is convenient for local regression, but it creates a long-term leakage risk:

- Codex can inspect the validation page source while modifying evals or runtime behavior.
- Runtime-facing prompts and product code can accidentally grow special cases for known fixture routes, text, selectors, or DOM structure.
- Forbidden scans can catch obvious leaks, but source co-location still makes future regressions easier.
- Product-like validation becomes weaker when the test target implementation lives inside the product repository.

The desired steady state is:

- WebAgentFlow main repository owns validation protocol and evidence.
- Fixture implementation lives in a separate deterministic fixture repository.
- Product-like validation target lives in a separate black-box repository.

## Repository boundaries

### 1. WebAgentFlow main repository

The main repository should keep the core system and validation protocol only.

Allowed long-term contents:

- Eval case definitions.
- Eval runner code.
- Target manifests.
- Allowed URL configuration.
- Expected high-level behavior gates.
- Run artifacts and result summaries.
- Review / closeout documentation.
- Migration docs and audit records.

Suggested retained paths:

```text
WebAgentFlow/
  scripts/evals/
  docs/testing/results/
  docs/testing/manifests/
  docs/iterations/
```

The main repository may know stable target URLs such as:

```text
http://127.0.0.1:5176/items
http://127.0.0.1:5177/inventory
```

It should not know implementation details for product-like validation targets.

### 2. WebAgentFlow-Fixture-Site

Purpose: deterministic regression fixture.

This repository is allowed to be test-shaped. It can expose stable test support surfaces such as:

```text
/items
/reset
/seed
/api/state
```

Allowed fixture characteristics:

- Stable `data-testid` attributes.
- Deterministic seed/reset behavior.
- Fixture-only APIs for asserting state.
- CI-friendly local startup.
- Known scenarios for automatic gates.

This repository is not a black-box generalization proof. It is the stable measuring jig.

### 3. WebAgentFlow-Validation-Site

Purpose: product-like black-box validation.

This repository should look more like a small real business application.

Initial route surface:

```text
/inventory
/orders
/customers
```

First version should focus on safe operations only:

- Create.
- Search.
- Edit.

Explicitly out of scope for the first version:

- Login.
- Delete flows.
- Payments.
- Permissions.
- Complex cross-page flows.

WebAgentFlow should treat this target as a black box. The main repository should record target URL, task prompt, expected high-level behavior, and results, but not source-level details.

## What the main repository may retain

The main repository may keep fixtures and validation references at the protocol level:

```yaml
target_name: fixture-items
target_url: http://127.0.0.1:5176/items
cases:
  - url_only_known_page
  - execute_known_action
  - vague_input_no_execution
```

It may also keep product-like validation manifests such as:

```yaml
target_name: validation-inventory
target_url: http://127.0.0.1:5177/inventory
cases:
  - create_inventory_item_from_user_request
  - search_inventory_by_user_visible_text
  - edit_inventory_item_quantity
```

## What the main repository must not retain

The main repository should not retain validation target implementation details, including:

```text
- Page source code.
- Component names.
- DOM `data-testid` values for product-like targets.
- Internal selector maps.
- Fixed fixture prose that can be memorized by runtime prompts.
- Site business logic.
- Internal state shape for product-like targets.
```

Avoid product validation manifests like:

```yaml
selector: "[data-testid='item-list']"
button_selector: "[data-testid='item-create-button']"
```

Exception: fixture-only eval manifests may contain selector-level details when needed for deterministic regression, but those manifests must remain clearly marked fixture-only and excluded from product runtime / product prompt paths.

## Migration plan

### Phase 1: copy out, keep compatibility

Do not delete `apps/product-test-site` during this phase.

1. Create `WebAgentFlow-Fixture-Site`.
2. Copy the current `apps/product-test-site` implementation into that repository.
3. Preserve its deterministic routes and any existing reset/seed/state helpers.
4. Update WebAgentFlow eval runner configuration so fixture target URLs are read from external target manifest/config instead of assuming an in-repo app.
5. Mark `apps/product-test-site` as deprecated in docs.
6. Run M11.3.6 / M11.3.7 evals against the external fixture URL.
7. Record results under `docs/testing/results/`.
8. Keep local fallback instructions until external fixture evals are confirmed stable.

### Phase 2: remove in-repo site source

Only after Phase 1 passes.

1. Delete `apps/product-test-site` from WebAgentFlow.
2. Remove or replace package scripts that start the in-repo validation site.
3. Keep eval manifests, results, and closeout notes.
4. Add a forbidden scan gate that fails if fixture or validation site source returns to the main repository.
5. Keep setup docs pointing to the external repositories.

## Eval runner URL / manifest refactor

The eval runner should treat targets as externally configurable.

Recommended manifest shape:

```yaml
targets:
  fixture_items:
    kind: fixture
    url: ${WAF_FIXTURE_ITEMS_URL:-http://127.0.0.1:5176/items}
    manifest: docs/testing/manifests/fixture-site-items.yaml

  validation_inventory:
    kind: product_validation
    url: ${WAF_VALIDATION_INVENTORY_URL:-http://127.0.0.1:5177/inventory}
    manifest: docs/testing/manifests/validation-site-inventory.yaml
```

Recommended rules:

- Runner reads URLs from manifest/config/env.
- Runtime code does not import validation-site code.
- Product prompts do not include fixture selectors, DOM IDs, route-specific answers, or fixed fixture text.
- Fixture-only assertions may use internal APIs, but product-like validation assertions should prefer browser-observable behavior.
- Results should record target name, target URL, commit SHA where available, run timestamp, and gates passed/failed.

## Not in scope for this iteration

- Do not change product runtime code.
- Do not delete `apps/product-test-site` yet.
- Do not build the new external repositories inside this branch.
- Do not add login, delete, payment, permission, or complex multi-page validation flows.
- Do not move existing M11.3.6 / M11.3.7 result artifacts.

## Acceptance criteria

This planning iteration is complete when:

- The three-repository boundary is documented.
- The main repository allowed/disallowed contents are documented.
- The two-phase migration plan is documented.
- Eval runner external URL / manifest direction is documented.
- No runtime code is changed.
- `apps/product-test-site` remains in place.
- A future implementation pass can safely copy out the fixture site without breaking M11.3.6 / M11.3.7 eval compatibility.

## Suggested external repository names

```text
leechen298/WebAgentFlow-Fixture-Site
leechen298/WebAgentFlow-Validation-Site
```

Suggested descriptions:

```text
WebAgentFlow-Fixture-Site: Deterministic validation fixture for WebAgentFlow eval regression.
WebAgentFlow-Validation-Site: Product-like black-box validation target for WebAgentFlow browser-agent evaluation.
```

## Local creation commands

The current GitHub connector used for this planning pass can write to existing repositories but does not expose a repository-creation operation. If creating the repositories locally, use:

```bash
gh repo create leechen298/WebAgentFlow-Fixture-Site \
  --public \
  --description "Deterministic validation fixture for WebAgentFlow eval regression" \
  --clone=false

gh repo create leechen298/WebAgentFlow-Validation-Site \
  --public \
  --description "Product-like black-box validation target for WebAgentFlow browser-agent evaluation" \
  --clone=false
```

After the repositories exist, a follow-up pass can populate them with README docs, package metadata, and copied or newly generated site code.

## Codex handoff prompt

```markdown
Please plan the WebAgentFlow validation site extraction. Do not delete existing code.

Goal:
- WebAgentFlow main repository should no longer retain validation site source long term.
- Main repository keeps eval cases, manifests, runner, results, and review docs.
- Internal fixture site moves to a separate repository for deterministic regression.
- Product-like validation site moves to a separate repository for black-box manual validation and later eval.
- Migration must not break existing M11.3.6 / M11.3.7 evals.

Create or update:
- docs/iterations/m11/11.3.8-external-validation-sites-separation/README.md

Include:
1. Current problem.
2. Three-repository boundary.
3. What the main repository may retain.
4. What the main repository must not retain.
5. Migration steps.
6. How the eval runner should read external target URL / manifest.
7. Non-goals.
8. Acceptance criteria.

Constraints:
- Do not change runtime code.
- Do not delete apps/product-test-site.
- Do not create external repository code in this pass.
- Only write the migration plan.
```
