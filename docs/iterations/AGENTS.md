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

## Plan-Compatible Documentation Generation Standard

When an agent is asked to create or revise iteration documents, the
documentation-generation phase should behave like a compact `/plan` run before
any runtime implementation starts. The output must be decision-complete enough
that a later implementation agent can follow the generated docs without
guessing package type, scope, gates, or stop conditions.

Before writing or changing iteration documents, identify and then encode these
decisions in the generated package docs, usually in `plan.md` and `review.md`:

```text
target package path
package type: docs | code | mixed | validation | umbrella / campaign
parent / child relationship, if any
required document set
source-of-truth inputs already read
contract / concept / status / evidence changes
design-review gate
test-plan trigger decision
implementation authorization boundary
expected verification evidence
stop conditions
next handoff or campaign checkpoint
```

For code or mixed packages, generated docs must not authorize implementation
by implication. `technical-design.md` must be reviewed and
`implementation_authorized: yes` must be recorded before code work starts.

For umbrella or campaign packages, the documentation-generation plan must also
decide whether `GOAL_RUNNER.md` and `CURRENT_STATE.md` are required. If they
are required, create them from the templates or explicitly record why an
existing pair remains authoritative.

If the target package, package type, required file set, parent / child route,
or implementation boundary is ambiguous and cannot be resolved from repository
state, stop as `NEEDS_USER_INPUT` instead of generating speculative docs.

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

## Milestone Index Synchronization

Any new concrete package directory, umbrella package, validation package, or
planned child-package sequence must be reflected in the owning milestone
`README.md` and, when applicable, the milestone plan.

The milestone `README.md` must expose enough information for future agents to
discover:

- package id / directory;
- package type;
- current status;
- parent / child relationship for umbrella packages;
- next executable child package when a parent only defines a plan.

The milestone plan or umbrella plan remains the execution-grade
specification, but the milestone `README.md` must not omit the package
entirely. A package directory that exists but is missing from the milestone
`README.md` is a review finding. If the omission can cause an implementation
agent to start from the wrong package, treat it as P1; otherwise treat it as
at least P2.

Parent umbrella packages must not be treated as code implementation packages
when their docs require child packages to create full seven-document sets
first. Child packages planned inside an umbrella plan must either be listed in
the milestone index or the milestone index must point to the parent package and
clearly state the next executable child package.

Review checklist:

- Check package directory exists.
- Check milestone `README.md` entry exists.
- Check milestone plan or parent umbrella plan has execution-grade
  planned-package fields.
- Check status / type match across package `README.md`, milestone
  `README.md`, and plan.
- Check child-package gate before implementation.

## Campaign Goal Runner Standard

A campaign is any umbrella package or milestone sequence intended to be run by
Codex App `/goal` across more than one child package.

Campaigns that may be consumed by `/goal` must provide:

```text
GOAL_RUNNER.md
CURRENT_STATE.md
```

`GOAL_RUNNER.md` is the stable automation contract. It must define:

```text
authoritative inputs
default execution mode
full campaign mode
child package lifecycle
runtime authorization rules
hard stops
final status vocabulary
live validation approval requirements
closeout consistency gate
required child closeout fields
```

`CURRENT_STATE.md` is the short mutable routing snapshot. It must define:

```text
current_mode
parent_package
parent_status
parent_authorizes_runtime_implementation
active_child_package
route_status
route_type
next_action
do_not_reimplement
handoff_source
package queue
conflict rule
live validation rule, when applicable
```

Default `/goal` campaign behavior is `full_campaign_mode`: Codex may continue
from one child package to the next without a new user prompt only when the
current child reaches `PACKAGE_COMPLETE` and the next child is explicitly
listed as eligible in `CURRENT_STATE.md` or the parent plan. A campaign may
choose a stricter default such as one child per goal, but it must say so in
`GOAL_RUNNER.md`.

Each child package checkpoint must record, at minimum:

```text
child package id
route status
changed files
commands run
commands not run
test results
review findings by priority
compatibility review
scope review
next action
```

Full campaign mode does not bypass gates. Stop the campaign immediately as
`BLOCKED`, `NEEDS_USER_INPUT`, or the campaign's equivalent final status when
any of these occur:

- unresolved P0 / P1 design, code, evidence, or scope finding;
- missing required child documents;
- missing reviewed `technical-design.md` for code or mixed work;
- missing `implementation_authorized: yes` before implementation;
- insufficient evidence for the requested status;
- `CURRENT_STATE.md` conflicts with child docs, parent plan, review records,
  or actual git state;
- out-of-scope runtime, test, eval, external result, fixture, schema, API,
  worker, frontend, or documentation file appears in the diff;
- live validation is needed but the current thread does not explicitly provide
  the required target, API, state, scenario, and result-doc update approvals.

Do not encode stale child package ids as the authoritative route inside
`GOAL_RUNNER.md`. The current route must come from `CURRENT_STATE.md` or the
parent plan so completed children do not keep attracting new `/goal` runs.

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
Checkpoint update step
Review update step
```

### review.md

Must include:

```text
FINAL_STATUS block for current routing state
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
