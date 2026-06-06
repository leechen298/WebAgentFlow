"""LearnedCapability data access."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.learned_capability import (
    LearnedCapability,
    Provenance,
    TrustStatus,
)
from app.models.learned_path import is_legal_trust_transition
from app.schemas.common import decode_cursor, encode_cursor

ALLOWED_CAPABILITY_KINDS = frozenset(
    {
        "control_input",
        "control_select",
        "control_toggle",
        "submit_search",
        "reset_filters",
        "switch_tab",
        "open_detail",
        "export_download",
        "show_modal_or_toast",
        "unknown",
    }
)

REQUIRED_ACTION_SCHEMA_KEYS = frozenset(
    {"version", "adapter_type", "operation", "required_slots", "control_binding"}
)

REQUIRED_EVIDENCE_KEYS = frozenset(
    {
        "version",
        "source",
        "terminal_outcome",
        "business_match_observed",
        "evidence_strength",
        "warnings",
        "redaction",
    }
)

FORBIDDEN_ACTION_SCHEMA_KEYS = frozenset(
    {
        "playwright_command",
        "playwright_commands",
        "llm_steps",
        "step_by_step_instructions",
        "replay_actions",
        "execution_payload",
    }
)

FORBIDDEN_ACTION_SCHEMA_KEY_TOKENS = frozenset(
    {
        "playwright",
        "llm",
        "replay",
        "execution",
    }
)


def compute_capability_dedup_key(
    *,
    page_template: str,
    query_signature: dict,
    dom_fingerprint: str,
    capability_kind: str,
    region_ref: str,
    control_ref: str,
    terminal_target_json: dict,
) -> str:
    payload = json.dumps(
        {
            "page_template": page_template,
            "query_signature": query_signature,
            "dom_fingerprint": dom_fingerprint,
            "capability_kind": capability_kind,
            "region_ref": region_ref,
            "control_ref": control_ref,
            "terminal_target_json": terminal_target_json,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LearnedCapabilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ingest(
        self,
        *,
        page_template: str,
        query_signature: dict,
        dom_fingerprint: str,
        capability_key: str,
        capability_kind: str,
        human_label: str | None,
        region_ref: str,
        control_ref: str,
        adapter_type: str,
        action_schema_json: dict,
        sample_value_policy_json: dict,
        terminal_target_json: dict,
        evidence_json: dict,
        source_run_id: str | None,
        source_learned_path_id: str | None,
        provenance: Provenance = Provenance.SYSTEM,
    ) -> tuple[LearnedCapability, bool]:
        _validate_capability_payload(
            capability_kind=capability_kind,
            action_schema_json=action_schema_json,
            evidence_json=evidence_json,
        )
        key = compute_capability_dedup_key(
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            capability_kind=capability_kind,
            region_ref=region_ref,
            control_ref=control_ref,
            terminal_target_json=terminal_target_json,
        )
        existing = self._find_by_dedup_key(key)
        if existing is not None:
            return existing, False

        row = LearnedCapability(
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            capability_key=capability_key,
            capability_kind=capability_kind,
            human_label=human_label,
            region_ref=region_ref,
            control_ref=control_ref,
            adapter_type=adapter_type,
            action_schema_json=action_schema_json,
            sample_value_policy_json=sample_value_policy_json,
            terminal_target_json=terminal_target_json,
            evidence_json=evidence_json,
            provenance=provenance,
            trust=TrustStatus.PROVISIONAL,
            source_run_id=source_run_id,
            source_learned_path_id=source_learned_path_id,
            dedup_key=key,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self._find_by_dedup_key(key)
            if existing is None:
                raise
            return existing, False
        self.session.refresh(row)
        return row, True

    def get(self, capability_id: str) -> LearnedCapability | None:
        return self.session.get(LearnedCapability, capability_id)

    def find_by_identity(
        self,
        *,
        page_template: str,
        query_signature: dict,
        dom_fingerprint: str,
        capability_kind: str,
        region_ref: str,
        control_ref: str,
        terminal_target_json: dict,
    ) -> LearnedCapability | None:
        key = compute_capability_dedup_key(
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            capability_kind=capability_kind,
            region_ref=region_ref,
            control_ref=control_ref,
            terminal_target_json=terminal_target_json,
        )
        return self._find_by_dedup_key(key)

    def list_page(
        self,
        *,
        page_template: str | None = None,
        capability_kind: str | None = None,
        trust: TrustStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[LearnedCapability], bool, str | None]:
        stmt = select(LearnedCapability)
        if page_template is not None:
            stmt = stmt.where(LearnedCapability.page_template == page_template)
        if capability_kind is not None:
            stmt = stmt.where(LearnedCapability.capability_kind == capability_kind)
        if trust is not None:
            stmt = stmt.where(LearnedCapability.trust == trust)
        if cursor:
            cursor_ts, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    LearnedCapability.created_at < cursor_ts,
                    and_(
                        LearnedCapability.created_at == cursor_ts,
                        LearnedCapability.id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            LearnedCapability.created_at.desc(), LearnedCapability.id.desc()
        ).limit(limit + 1)

        windowed = list(self.session.scalars(stmt).all())
        has_next = len(windowed) > limit
        if has_next:
            windowed = windowed[:limit]
        next_cursor: str | None = None
        if has_next and windowed:
            tail = windowed[-1]
            next_cursor = encode_cursor(tail.created_at, tail.id)
        return windowed, has_next, next_cursor

    def set_trust(
        self,
        capability_id: str,
        status: TrustStatus,
        reason: str | None,
    ) -> LearnedCapability:
        row = self.get(capability_id)
        if row is None:
            raise ValueError(f"learned_capability not found: {capability_id}")
        current = TrustStatus(row.trust)
        if not is_legal_trust_transition(current, status):
            raise ValueError(
                f"illegal trust transition: {current.value} -> {status.value}"
            )
        row.trust = status
        row.trust_reason = reason
        row.trust_updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(row)
        return row

    def _find_by_dedup_key(self, key: str) -> LearnedCapability | None:
        stmt = (
            select(LearnedCapability)
            .where(LearnedCapability.dedup_key == key)
            .limit(1)
        )
        return self.session.scalars(stmt).first()


def _validate_capability_payload(
    *,
    capability_kind: str,
    action_schema_json: dict,
    evidence_json: dict,
) -> None:
    if capability_kind not in ALLOWED_CAPABILITY_KINDS:
        raise ValueError(f"unsupported capability_kind: {capability_kind}")

    missing_action_keys = REQUIRED_ACTION_SCHEMA_KEYS - set(action_schema_json)
    if missing_action_keys:
        missing = ", ".join(sorted(missing_action_keys))
        raise ValueError(f"action_schema_json missing keys: {missing}")
    forbidden_action_keys = _find_forbidden_action_schema_keys(action_schema_json)
    if forbidden_action_keys:
        forbidden = ", ".join(sorted(forbidden_action_keys))
        raise ValueError(f"action_schema_json contains forbidden key: {forbidden}")

    missing_evidence_keys = REQUIRED_EVIDENCE_KEYS - set(evidence_json)
    if missing_evidence_keys:
        missing = ", ".join(sorted(missing_evidence_keys))
        raise ValueError(f"evidence_json missing keys: {missing}")


def _find_forbidden_action_schema_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        found = {
            str(key)
            for key in value
            if key in FORBIDDEN_ACTION_SCHEMA_KEYS or _is_forbidden_action_key(key)
        }
        for item in value.values():
            found.update(_find_forbidden_action_schema_keys(item))
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for item in value:
            found.update(_find_forbidden_action_schema_keys(item))
        return found
    return set()


def _is_forbidden_action_key(key: object) -> bool:
    normalized = str(key).replace("_", "-").lower()
    compact = normalized.replace("-", "")
    return any(
        token in normalized or token.replace("-", "") in compact
        for token in FORBIDDEN_ACTION_SCHEMA_KEY_TOKENS
    )
