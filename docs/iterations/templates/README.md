# <Iteration Title>

Status: proposed
Milestone: M<N>
Type: docs | code

## Iteration Type

- [ ] Docs-only iteration
- [ ] Code iteration
- [ ] Mixed iteration

Mixed iterations follow the Code Iteration Gate.

## Package Documents

- `intent.md` - goal, motivation, boundary, success criteria.
- `contract.md` - concept, state, schema, evidence, and boundary contract.
- `technical-design.md` - required for non-trivial code and mixed iterations.
- `plan.md` - implementation steps and validation commands.
- `review.md` - review notes, user feedback, final deltas.

## Docs Iteration Gate

Required:

- [ ] `intent.md` exists.
- [ ] `contract.md` exists if this changes concepts, status, schemas, evidence, or boundaries.
- [ ] `contract.md` says `N/A` with a reason if no contract changes exist.
- [ ] `plan.md` exists.
- [ ] `review.md` exists.

## Code Iteration Gate

- [ ] `intent.md` exists.
- [ ] `contract.md` exists.
- [ ] `technical-design.md` exists.
- [ ] Technical design has been reviewed before implementation starts.
- [ ] Technical design includes explicit contract alignment.
- [ ] `plan.md` matches the approved contract and technical design.
- [ ] `review.md` records validation evidence before completion.

## Current Status

<Short handoff note for the next agent.>
