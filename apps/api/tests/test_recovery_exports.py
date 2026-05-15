"""Package-level exports for M12 recovery services."""

from __future__ import annotations

import app.services.recovery as recovery
from app.services.recovery import (
    RecoveryBoundaryClassifier,
    RecoveryProposalGenerator,
    UserAbortHandler,
    classify_recovery_boundary,
    generate_recovery_proposal,
    handle_user_abort,
)


def test_recovery_package_exports_all_m12_service_entrypoints() -> None:
    assert recovery.RecoveryBoundaryClassifier is RecoveryBoundaryClassifier
    assert recovery.UserAbortHandler is UserAbortHandler
    assert recovery.RecoveryProposalGenerator is RecoveryProposalGenerator

    assert recovery.classify_recovery_boundary is classify_recovery_boundary
    assert recovery.handle_user_abort is handle_user_abort
    assert recovery.generate_recovery_proposal is generate_recovery_proposal

    assert set(recovery.__all__) == {
        "RecoveryBoundaryClassifier",
        "RecoveryProposalGenerator",
        "UserAbortHandler",
        "classify_recovery_boundary",
        "generate_recovery_proposal",
        "handle_user_abort",
    }
