# Embedded Product Test Site Removal Closeout

Date: 2026-05-24
Status: embedded product-test-site removal complete
Repository: WebAgentFlow v0.1

## Summary

This closeout only covers removal of the embedded product-test-site source tree
and root workspace script integration from the WebAgentFlow main repository.

It does not claim that legacy product-test-site runtime, test, or eval
semantics have been fully cleaned up.

The standalone `WebAgentFlow-Validation-Site` remains external to this
repository. WebAgentFlow does not know that repository as a workspace,
submodule, dependency, or runtime target. Users and test operators provide
ordinary URLs to the WebAgentFlow CLI / API / runtime.

## Completed

- `apps/product-test-site` removed.
- Root `dev` and `dev:lan` no longer start product-test-site.
- Root `build` no longer builds product-test-site.
- Root `dev:product`, `dev:product:lan`, and `build:product` scripts removed.
- Validation-site scripts are retained: `dev:validation`, `dev:validation:lan`,
  and `build:validation`.
- `pnpm-lock.yaml` updated by `pnpm install --lockfile-only` so the
  product-test-site workspace importer is no longer present.

## External Validation Site Evidence

The external product-like validation site is outside this repository:

```text
Repository: /Users/leechen/projects/WebAgentFlow-Validation-Site
GitHub: leechen298/WebAgentFlow-Validation-Site
Target: http://127.0.0.1:5177/inventory
```

Standalone verification for that repository previously passed:

- `pnpm install --frozen-lockfile`: pass
- `pnpm build`: pass
- `curl -i http://127.0.0.1:5177/inventory`: returned `HTTP/1.1 200 OK`
- Browser smoke: create, search, edit, and empty state passed
- Source/config scan: no old routes or old contracts found

Those checks are recorded here as external-site evidence. They are not a main
repository workspace dependency and were not converted into a WebAgentFlow
runtime special case.

## Historical Eval Boundary

Old M11.3.6 / M11.3.7 `5176/items` eval results remain historical evidence.

Old eval scripts are not revalidated by this cleanup because their embedded
target site has been removed.

This cleanup intentionally does not modify `scripts/evals/*`.

## Known Existing Lint Status

`pnpm lint:js` has known pre-existing failures outside this cleanup scope.
This closeout does not claim lint cleanup for unrelated console files.

## Not Completed

The following work is explicitly outside this closeout:

- Legacy `/workspace-login` runtime special case in
  `apps/api/app/services/learning/learning_run_service.py` is not cleaned.
- Legacy `/items`, `5176`, `item_name`, and `item-list` semantics in
  `scripts/evals/*` are not cleaned.
- Old product-test-site scenario references in API / CLI tests are not cleaned.
- External Validation Site black-box test plan is not established.

## Decision

Embedded product-test-site source and workspace integration removal is complete.
Legacy product-test-site runtime, test, and eval semantics remain future cleanup
work.
