"""M11.3.5 conversation context collection."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from app.repos.conversation_repo import ConversationRepository
from app.services.conversation.intake import redact_sensitive_payload

_URL_RE = re.compile(r"https?://[^\s，。]+")


class PendingTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    site_origin: str | None = None
    page_hint: str | None = None
    source: str = "user_message"
    turns_remaining: int = 3


class LastNoPathReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_url: str | None = None
    user_goal: str | None = None
    reason: str
    created_from_message_id: str | None = None


class LearnedActionSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    alias: str | None = None
    utterances: list[str] = Field(default_factory=list)
    learned_path_id: str | None = None
    target_url: str | None = None
    site_origin: str | None = None
    page_template: str | None = None
    scenario: str | None = None


class ConversationContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recent_messages: list[dict[str, Any]] = Field(default_factory=list)
    pending_intake: dict[str, Any] | None = None
    pending_target: PendingTarget | None = None
    last_no_path_reason: LastNoPathReason | None = None
    learned_actions: list[LearnedActionSummary] = Field(default_factory=list)
    learned_actions_by_scope: dict[str, list[LearnedActionSummary]] = Field(
        default_factory=dict
    )
    current_message_url: str | None = None
    recent_url: str | None = None
    unique_learned_target_url: str | None = None


class ConversationContextCollector:
    def __init__(self, repo: ConversationRepository, *, recent_limit: int = 8) -> None:
        self._repo = repo
        self._recent_limit = recent_limit

    def collect(
        self,
        session_id: str,
        *,
        current_message: str,
    ) -> ConversationContextBundle:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = redact_sensitive_payload(dict(session.metadata_json or {}))
        messages = self._repo.list_messages(session_id, limit=10_000)
        recent_messages = [
            {
                "id": message.id,
                "role": str(message.role),
                "content": redact_sensitive_payload(message.content),
            }
            for message in messages[-self._recent_limit :]
        ]
        learned_actions = [
            LearnedActionSummary.model_validate(action)
            for action in (metadata.get("learned_actions") or [])
            if isinstance(action, dict)
        ]
        learned_by_scope: dict[str, list[LearnedActionSummary]] = {}
        for action in learned_actions:
            key = _target_scope_key(action.target_url, action.site_origin)
            learned_by_scope.setdefault(key, []).append(action)

        current_url = _extract_url(current_message)
        recent_url = current_url or _last_url_from_messages(recent_messages)
        pending_target = _parse_pending_target(metadata.get("pending_target"))
        last_no_path_reason = _parse_last_no_path_reason(
            metadata.get("last_no_path_reason")
        )
        return ConversationContextBundle(
            recent_messages=recent_messages,
            pending_intake=_dict_or_none(metadata.get("pending_intake")),
            pending_target=pending_target,
            last_no_path_reason=last_no_path_reason,
            learned_actions=learned_actions,
            learned_actions_by_scope=learned_by_scope,
            current_message_url=current_url,
            recent_url=recent_url
            or (last_no_path_reason.target_url if last_no_path_reason else None),
            unique_learned_target_url=_unique_learned_target_url(learned_actions),
        )


def make_pending_target(url: str, *, source: str = "user_message") -> PendingTarget:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
    page_hint = parsed.path or None
    return PendingTarget(
        url=url,
        site_origin=origin,
        page_hint=page_hint,
        source=source,
    )


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    return match.group(0) if match else None


def _last_url_from_messages(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        url = _extract_url(str(message.get("content") or ""))
        if url:
            return url
    return None


def _target_scope_key(url: str | None, site_origin: str | None) -> str:
    return url or site_origin or "unknown"


def _unique_learned_target_url(
    learned_actions: list[LearnedActionSummary],
) -> str | None:
    urls = {action.target_url for action in learned_actions if action.target_url}
    return next(iter(urls)) if len(urls) == 1 else None


def _parse_pending_target(value: Any) -> PendingTarget | None:
    if not isinstance(value, dict):
        return None
    try:
        return PendingTarget.model_validate(value)
    except ValueError:
        return None


def _parse_last_no_path_reason(value: Any) -> LastNoPathReason | None:
    if not isinstance(value, dict):
        return None
    try:
        return LastNoPathReason.model_validate(value)
    except ValueError:
        return None


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None
