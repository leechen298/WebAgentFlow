# Plan

状态：REPO_LOCAL_NON_LIVE_IMPLEMENTATION_READY_FOR_REVIEW

## Phase 1 - Design Review

1. Review 11.3.12.4 current composer boundaries。
2. Confirm this package adds automatic candidate generation / execution / promotion, not a replacement composer。
3. Confirm Validation Site oracle remains provider-private。
4. Record `implementation_authorized: yes` only after design review passes。

## Phase 2 - Schema And Persistence

1. Define `CompositionCandidate` schema。
2. Define candidate status taxonomy。
3. Implement candidate persistence using a new `composition_candidates` table。
4. Define `waf.learning_evidence_bundle.v1` schema。

## Phase 3 - Candidate Generation

1. Implement `CapabilityGraphBuilder`。
2. Implement `CompositionRequirementDeriver`。
3. Implement `BoundedCompositionCandidateGenerator`。
4. Add unit tests for bounded generation and coverage metrics。

## Phase 4 - Execution And Promotion

1. Implement candidate executor。
2. Integrate terminal / ingest evidence。
3. Implement promotion writer to LearnedPath。
4. Add negative evidence handling。
5. Add integration tests。

## Phase 5 - Conversation And Evidence Bundle

1. Add conversation history summary for composition attempts。
2. Add redacted learning evidence bundle builder。
3. Ensure provider-facing bundle has no oracle / target leakage。
4. Add tests and redaction scan。

## Phase 6 - Closeout

1. Run scoped pytest。
2. Run scoped ruff。
3. Run hardcoding scan。
4. Run `git diff --check`。
5. Record commands in `review.md`。

## Forbidden During This Package

- No live validation without explicit approval。
- No direct autonomous-run endpoint calls。
- No provider oracle in runtime。
- No target-specific prompt/code constants。
