# Codex Exploratory Validation

Codex exploratory validation is a second-stage testing workflow. It cannot
replace deterministic E2E regression.

The purpose is to let Codex read product and API contracts, propose boundary
cases, run local deterministic E2E, observe the console and validation-site,
and identify gaps that should become permanent tests.

## Hard Boundaries

Codex exploratory validation must not:

- Call `/exploration/autonomous-runs`.
- Call `/exploration/autonomous-runs/stream`.
- Import or directly run the autonomous explorer.
- Depend on an LLM provider.

## Allowed Activities

It may:

- Run deterministic E2E suites.
- Use headed Playwright to inspect the local console and validation-site.
- Propose new deterministic E2E cases.
- Convert stable findings into permanent Playwright Test cases.

No automatic exploratory script is implemented in the current testing
infrastructure pass.
