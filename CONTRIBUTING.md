# Contributing to WebAgentFlow

Thank you for your interest in contributing to WebAgentFlow.

This project is still in an early stage. Contributions are welcome, especially those that improve clarity, stability, and development workflow without expanding beyond the current iteration scope.

## How to get started

You can contribute in several practical ways:

- bug fixes
- documentation improvements
- small feature improvements
- developer experience improvements
- test, demo, or example improvements

Before starting larger work, it is helpful to open an issue first so the scope and direction are clear.

## Development setup

To work on this repository locally, make sure you have:

- Node.js 20+
- pnpm
- Python 3.11+
- Docker

For the current setup steps, local services, and common commands, see [docs/dev-setup.md](./docs/dev-setup.md).

## Branch naming

Use short, descriptive branch names with one of these prefixes:

- `feat/*`
- `fix/*`
- `docs/*`
- `chore/*`
- `refactor/*`

Examples:

- `feat/recordings-overview-shell`
- `fix/api-health-route`
- `docs/update-dev-setup`

## Commit message convention

This repository follows Conventional Commits.

Examples:

- `feat: add recordings list page`
- `fix: correct api health route`
- `docs: update dev setup guide`

Keep commit messages focused on the outcome of the change. Prefer small, reviewable commits over large mixed commits.

## Pull request guidelines

When opening a pull request:

- keep the PR focused on a single topic
- describe what changed and why
- include screenshots when the change affects UI
- call out any known limitations or follow-up work
- avoid mixing unrelated refactors into the same PR

If your change updates developer workflow, setup, or examples, mention how reviewers can validate it quickly.

## Issue guidelines

When opening an issue, please include as much useful context as possible:

- problem description
- reproduction steps
- expected behavior
- actual behavior
- environment information

For feature requests, explain the user problem first, then the proposed direction.

## Code style

Please keep contributions aligned with the current project direction:

- prefer code that is clear, simple, and maintainable
- avoid premature abstraction
- do not implement functionality that is outside the current iteration scope
- stay consistent with the existing directory structure and naming style

If you are unsure whether something fits the current phase of the project, open an issue or draft PR before investing in a larger implementation.
