"""Shared observation signal classification policy.

The wait service and replay observation aggregation must agree on which
signals are primary evidence and which are supporting-only evidence.
"""

from __future__ import annotations

from app.schemas.learned_path_replay import ObservationSignalKind

PRIMARY_SIGNAL_KINDS: set[ObservationSignalKind] = {"url_changed", "title_changed"}
SUPPORTING_SIGNAL_KINDS: set[ObservationSignalKind] = {"network_idle_observed"}
