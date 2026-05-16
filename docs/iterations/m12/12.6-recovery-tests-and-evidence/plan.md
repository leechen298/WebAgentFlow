# Plan

Status: proposed
Milestone: M12
Type: mixed

## Inputs

- `AGENTS.md`
- `CLAUDE.md`
- `CLAUDE.zh.md`
- `docs/iterations/README.md`
- `docs/iterations/templates/*`
- `docs/iterations/m12/README.md`
- `docs/iterations/m12/m12-plan.md`
- M12.1-M12.5 review documents
- M12.5 contract / technical design / test plan
- recovery schemas, services, and tests under `apps/api`

## This Design Package Steps

1. Create `docs/iterations/m12/12.6-recovery-tests-and-evidence/`.
2. Add seven non-empty documents:
   - `README.md`
   - `intent.md`
   - `contract.md`
   - `technical-design.md`
   - `test-plan.md`
   - `plan.md`
   - `review.md`
3. Update M12 README index:
   - 12.1-12.5 = implemented / shipped;
   - 12.6 = proposed / evidence closure design package.
4. Update `m12-plan.md`:
   - current package = 12.6 recovery tests and evidence design package;
   - 12.6 status = proposed / current evidence closure design package.
5. Run docs-level static checks.
6. Stage only `docs/iterations/m12`.
7. Commit as:
   `docs(m12): initialize recovery evidence closure package`.

## Later Evidence-Closure Steps

1. Run M12 recovery deterministic suite from `test-plan.md`.
2. Run recovery ruff check from `test-plan.md`.
3. Run `git diff --check`.
4. Record exact command outputs and exit codes.
5. Create `docs/testing/results/2026-05-16-m12-recovery-tests-and-evidence.md`.
6. Update `12.6/review.md` with validation evidence and findings.
7. Update M12 README / `m12-plan.md` only after a real completion decision.
8. Add focused tests only if a concrete coverage gap is found.

## Validation for This Design Package

| Check | Command | Expected |
|---|---|---|
| Seven-doc package exists | `test -f docs/iterations/m12/12.6-recovery-tests-and-evidence/<file>` | all seven files exist |
| No empty placeholder docs | inspect seven docs / non-zero content | `contract.md`, `technical-design.md`, and `test-plan.md` contain substantive sections |
| Markdown whitespace | `git diff --check` | clean |
| No code/package changes | `git status --short -- '*.py' '*.ts' '*.tsx' '*.js' '*.jsx' 'package.json' 'pnpm-lock.yaml' 'package-lock.json'` | no output |
| No M11 changes | `git status --short docs/iterations/m11` | no output |
| Scope | `git diff --name-only` | only `docs/iterations/m12/**` |
| Staged scope | `git diff --cached --name-only` | only `docs/iterations/m12/**` |
| Staged whitespace | `git diff --cached --check` | clean |

## Review Checklist

- [ ] This design package does not modify `apps/**` or `packages/**`.
- [ ] This design package does not run or claim recovery suite results.
- [ ] `review.md` does not declare `m12_completed` or
  `m12_completed_with_followups`.
- [ ] Not-run / unverified semantics are explicit.
- [ ] Later evidence closure commands are decision-complete.
- [ ] M12 index points to 12.6 as the current evidence closure design package.
