# WAgent Runtime Eval Boundary

This repository no longer keeps a target-specific WAgent runtime eval runner.
`pnpm run eval:wagent` is a target-agnostic cleanup guard that checks product
runtime, CLI, console, and default docs for forbidden target leakage.

Scenario-specific runners, page URLs, selectors, seed data, and artifacts belong
to an external fixture provider. WebAgentFlow may consume a redacted result
summary that follows `docs/testing/schemas/eval-result.v1.schema.json`, but it
must not embed the provider's page contents or answer keys.

## Current Command

```bash
pnpm run eval:wagent
```

The command delegates to:

```bash
cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest tests/test_target_agnostic_runtime_cleanup.py -q
```

## Boundary

- Runtime behavior must be based on the current page context and user input.
- Default docs must use placeholder URLs and scenario IDs.
- External fixture providers own their own browser smoke, scenario runners, and
  raw artifacts.
- WebAgentFlow stores only generic result contracts and redacted summaries.
