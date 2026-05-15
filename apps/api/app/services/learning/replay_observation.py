"""Replay observation aggregation service (M11.2.3).

Aggregates step-level ``wait_result`` data into a replay-level
``ReplayObservationSummary``.  This module does NOT re-execute actions,
read pages, call LLMs, or invoke the Task Result Reporter.
"""

from __future__ import annotations

import uuid

from app.schemas.learned_path_replay import (
    ObservationSignalKind,
    ReplayObservationStatus,
    ReplayObservationSummary,
    ReplayStepLog,
    StepObservationRef,
    WaitStatus,
)

# Signal classification
PRIMARY_SIGNAL_KINDS: set[ObservationSignalKind] = {"url_changed", "title_changed"}
SUPPORTING_SIGNAL_KINDS: set[ObservationSignalKind] = {"network_idle_observed"}


def _derive_status(
    *,
    step_count: int,
    has_primary: bool,
    has_timeout: bool,
    has_skipped_or_uncertain: bool,
    all_not_required_or_empty: bool,
) -> ReplayObservationStatus:
    """Derive replay observation status from aggregated evidence.

    Priority (from contract.md):
    1. not_applicable: no steps or all not_required
    2. partial_observation: has primary + (timeout or skipped/uncertain)
    3. observed: has primary, no weakening factors
    4. no_primary_observation: no primary signal at all
    """
    if step_count == 0 or all_not_required_or_empty:
        return "not_applicable"
    if has_primary and (has_timeout or has_skipped_or_uncertain):
        return "partial_observation"
    if has_primary:
        return "observed"
    return "no_primary_observation"


def build_replay_observation_summary(
    *,
    learned_path_id: str,
    steps: list[ReplayStepLog],
    replay_id: str | None = None,
) -> ReplayObservationSummary:
    """Build a replay-level observation summary from step logs.

    Only reads ``step.wait_result``.  Does not re-execute actions, read
    pages, or call any external service.
    """
    step_count = len(steps)

    # Counters
    wait_result_count = 0
    observed_step_count = 0
    timeout_step_count = 0
    skipped_step_count = 0
    not_required_step_count = 0

    # Signal aggregation (deduped)
    primary_signal_kinds: set[ObservationSignalKind] = set()
    supporting_signal_kinds: set[ObservationSignalKind] = set()

    # Step refs
    step_refs: list[StepObservationRef] = []

    # Track uncertainty
    has_timeout = False
    has_skipped_or_uncertain = False

    for step_log in steps:
        wr = step_log.wait_result
        if wr is None:
            # Old step without wait_result — still emit a ref
            step_refs.append(
                StepObservationRef(
                    step_index=step_log.step,
                    notes="no wait_result",
                )
            )
            has_skipped_or_uncertain = True
            continue

        wait_result_count += 1
        wait_status: WaitStatus = wr.status

        # Count by status
        if wait_status == "observed":
            observed_step_count += 1
        elif wait_status == "timeout":
            timeout_step_count += 1
            has_timeout = True
        elif wait_status == "skipped":
            skipped_step_count += 1
            has_skipped_or_uncertain = True
        elif wait_status == "not_required":
            not_required_step_count += 1

        # Classify signals from this step
        step_primary: set[ObservationSignalKind] = set()
        step_supporting: set[ObservationSignalKind] = set()

        for signal in wr.observed_signals:
            kind = signal.kind
            if kind in PRIMARY_SIGNAL_KINDS:
                step_primary.add(kind)
                primary_signal_kinds.add(kind)
            elif kind in SUPPORTING_SIGNAL_KINDS:
                step_supporting.add(kind)
                supporting_signal_kinds.add(kind)

        # Also check primary_signal field
        if wr.primary_signal is not None and wr.primary_signal.kind in PRIMARY_SIGNAL_KINDS:
            pkind = wr.primary_signal.kind
            step_primary.add(pkind)
            primary_signal_kinds.add(pkind)

        step_has_primary = bool(step_primary)
        step_has_supporting = bool(step_supporting)
        # Prefer the WaitResult's own primary_signal designation; fall back
        # to a deterministic pick from sorted collected primary kinds.
        primary_kind: ObservationSignalKind | None = None
        if wr.primary_signal is not None and wr.primary_signal.kind in PRIMARY_SIGNAL_KINDS:
            primary_kind = wr.primary_signal.kind
        elif step_primary:
            primary_kind = sorted(step_primary)[0]

        step_refs.append(
            StepObservationRef(
                step_index=step_log.step,
                wait_id=wr.wait_id,
                wait_status=wait_status,
                primary_signal_kind=primary_kind,
                signal_kinds=sorted(step_primary | step_supporting),
                has_primary_signal=step_has_primary,
                has_supporting_signal=step_has_supporting,
                notes=wr.notes,
            )
        )

    has_primary_observation = bool(primary_signal_kinds)

    # Determine if we have only supporting signals
    has_only_supporting = (
        not has_primary_observation and bool(supporting_signal_kinds)
    )

    # Uncertain: timeout without primary, or skipped steps, or mixed evidence
    has_uncertain = (
        (has_timeout and not has_primary_observation)
        or has_skipped_or_uncertain
        or (has_timeout and has_primary_observation)
    )

    status = _derive_status(
        step_count=step_count,
        has_primary=has_primary_observation,
        has_timeout=has_timeout,
        has_skipped_or_uncertain=has_skipped_or_uncertain,
        all_not_required_or_empty=(
            step_count == 0
            or (wait_result_count == step_count and not_required_step_count == step_count)
        ),
    )

    # Build notes
    notes_parts: list[str] = []
    if has_timeout:
        notes_parts.append(f"{timeout_step_count} step(s) timed out")
    if has_only_supporting:
        notes_parts.append("only supporting signals observed")
    if has_skipped_or_uncertain and not has_timeout:
        notes_parts.append("some steps skipped or missing wait_result")

    return ReplayObservationSummary(
        observation_summary_id=str(uuid.uuid4()),
        replay_id=replay_id,
        learned_path_id=learned_path_id,
        status=status,
        step_count=step_count,
        wait_result_count=wait_result_count,
        observed_step_count=observed_step_count,
        timeout_step_count=timeout_step_count,
        skipped_step_count=skipped_step_count,
        not_required_step_count=not_required_step_count,
        primary_signal_kinds=sorted(primary_signal_kinds),
        supporting_signal_kinds=sorted(supporting_signal_kinds),
        has_primary_observation=has_primary_observation,
        has_timeout=has_timeout,
        has_only_supporting_observation=has_only_supporting,
        has_uncertain_observation=has_uncertain,
        observation_notes="; ".join(notes_parts) if notes_parts else "",
        step_observation_refs=step_refs,
    )
