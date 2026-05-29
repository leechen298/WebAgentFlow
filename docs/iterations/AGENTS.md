# Iteration Documentation Agent Rules

Status: process standard

Chinese version: `AGENTS.zh.md`.

This file governs documentation work under `docs/iterations/`.
Repository-level `AGENTS.md`, `CLAUDE.md`, and `CLAUDE.zh.md` still govern
repository-wide behavior. This file defines the required detail level for
milestone plans, umbrella recovery plans, planned packages, concrete iteration
packages, validation plans, evidence, and reviews.

This file does not implement or define an external automation controller.

## Purpose

Use this file whenever creating or modifying files under `docs/iterations/`.
It turns the expected iteration-document detail level into explicit rules so
future agents do not infer scope, evidence requirements, compatibility
constraints, or closeout state from examples.

These rules apply to:

- milestone plans such as `m<N>-plan.md`;
- umbrella package plans such as an iteration parent `plan.md` that decomposes
  work into child packages;
- planned package entries inside those plans;
- concrete iteration packages;
- validation plans;
- post-closeout validation documents;
- review and evidence records.

## Planned Package Standard

Any milestone plan or umbrella package plan that contains multiple planned
sub-iterations must describe each planned package as a quasi-package
specification.

Each planned package must include these fields:

```text
Package name
Status
Type
Goal
Why this exists
Inputs / required reading
Allowed changes
Forbidden changes
Expected deliverables
Expected tests / verification
Compatibility constraints
Scope guardrails
Exit criteria
Handoff to next package
```

Hard rules:

- `README.md` may be a package index or summary.
- The detailed milestone or umbrella `plan.md` must be the execution
  specification.
- A one-line package summary is not enough.
- Later agents must not have to guess scope, allowed files, forbidden files,
  verification, compatibility constraints, or handoff state.
- If any required planned-package field is missing, review must record at
  least a P2 finding.
- If missing `Forbidden changes`, `Compatibility constraints`, or
  `Scope guardrails` could let runtime, API, schema, prompt, eval, or evidence
  work exceed scope, review must record a P1 finding.

## Iteration Package File Standard

Code and mixed packages must include:

```text
README.md
intent.md
contract.md
technical-design.md
test-plan.md
plan.md
review.md
```

Documentation-only packages must include at least:

```text
README.md
intent.md
contract.md
plan.md
review.md
```

Documentation-only packages may omit `technical-design.md` and `test-plan.md`
only when they do not prepare or change runtime, schema, API, UI, tests,
fixtures, prompts, process rules, evidence rules, validation behavior, release
status, or automation-consumption behavior.

If a documentation-only package modifies any of these topics, it must include
`test-plan.md` and should include `technical-design.md`:

```text
process rules
milestone semantics
product boundaries
Agent boundaries
evidence rules
validation templates
release status
package sequencing
automation consumption contracts
```

Umbrella planning packages may intentionally use a smaller file set only when
their own documents state that child code / mixed packages must create the full
seven-document package before implementation. Even then, the umbrella plan must
write each child package entry using the Planned Package Standard above.

## Required Content For Each Package File

Each package file must be specific enough for review. Placeholder headings are
not sufficient.

### README.md

Must include:

```text
Status
Type
Goal
Scope
Deliverables
Final assessment state, if applicable
```

### intent.md

Must include:

```text
Problem / purpose
Why now
Relationship to roadmap or milestone
Non-goals
Expected handoff
```

### contract.md

Must include:

```text
Public concepts
Allowed changes
Forbidden changes
Compatibility requirements
Out-of-scope follow-ups
```

### technical-design.md

Must include:

```text
Documentation or implementation structure
Affected files
Data / control flow, if relevant
Compatibility strategy
Anti-drift rules
```

### test-plan.md

Must include:

```text
Exact commands to run
Expected results
Commands not run and why
Blocker recording rule
No unverified claims rule
```

### plan.md

Must include:

```text
Ordered execution steps
Phase boundaries
Stop conditions
Review update step
```

### review.md

Must include:

```text
Changed files
Commands run
Test results
Compatibility review
Scope review
Unresolved P1/P2/P3
Final assessment
```

## Anti-Drift Requirements

Any future milestone or package planning must state:

```text
where the work lives
what files may change
what files must not change
which current behaviors are compatibility-sensitive
which adjacent tempting features are explicitly out of scope
which later milestone or package owns those tempting features
how the next package receives handoff
```

Do not:

- use external validation targets to drive runtime abstractions;
- copy target-specific selectors, seed data, routes, answer keys, or component
  details into product runtime or prompts;
- implement future-milestone work in the current package;
- mix documentation planning and implementation unless the current package
  contract explicitly allows it;
- claim tests passed without current-session evidence.

## Validation And Post-Closeout Documentation Standard

Post-closeout validation documents must distinguish these states:

```text
feature closeout complete
independent validation not yet performed
validation planned
validation executed
validation passed / blocked / failed / unverified
```

A validation plan must not be written as a validation result.

Post-closeout validation documents should include:

```text
intent
contract
test plan
API / CLI smoke plan
E2E / integration plan
external-operator review plan
execution plan
report template
review
```

Hard rules:

- E2E not run must be recorded as `not executed` or `not configured`.
- AI-operated validation not run must not be written as passed.
- If an E2E framework or service is unavailable, record the fallback and the
  remaining risk.
- Validation reports must not prefill `passed`.
- Only commands actually run in the current session may be recorded as passed.
- If a command is unavailable, record the blocker.
- For live autonomous or WAgent evidence, follow the repository execution
  boundary in root `AGENTS.md` / `CLAUDE.md`.

## Evidence And Review Rules

Evidence and review records must obey:

```text
No unverified test claims.
No hidden blockers.
No vague "tests passed".
No claim that a live product path passed without the approved product surface.
No conversion of FAIL / BLOCKED / UNVERIFIED into PASS by wording changes.
```

Review must preserve the difference between:

- planned but not implemented;
- implemented but not tested;
- non-live tests passed;
- live product validation passed;
- live product validation failed / blocked / unverified.
