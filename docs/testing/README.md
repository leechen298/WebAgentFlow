# Testing Infrastructure

This directory contains long-lived testing infrastructure documentation for
WebAgentFlow.

`docs/iterations/` stays milestone-scoped. It should hold delivery intent,
plans, step documents, and reviews for M10/M11/etc. It should not become the
home for permanent test-system documentation.

## Current Test Lines

WebAgentFlow has two planned validation tracks:

- Deterministic E2E regression: stable Playwright Test suites that exercise
  already-shipped behavior.
- Codex exploratory validation: a later workflow where Codex proposes boundary
  cases from contracts and turns stable findings into permanent E2E coverage.

The current implementation starts with deterministic E2E. Codex exploratory
validation is documented as a second stage only.

The E2E suite is deliberately independent of LLM providers. It does not call
`/exploration/autonomous-runs`, does not call
`/exploration/autonomous-runs/stream`, and does not create live autonomous
runs.

## Main Commands

```bash
pnpm run test:e2e
pnpm run test:e2e:headed
pnpm run test:e2e:ui
```

Install the Playwright Test browser once when setting up the E2E workspace:

```bash
pnpm run test:e2e:install
```

See [e2e.md](./e2e.md) for the deterministic E2E design and
[codex-exploratory.md](./codex-exploratory.md) for the deferred exploratory
validation plan.
