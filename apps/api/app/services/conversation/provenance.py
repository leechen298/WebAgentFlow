"""Response provenance helpers for user-visible conversation replies."""

from __future__ import annotations

from typing import Any

from app.schemas.conversation import ConversationResponseProvenance

CODE_PRODUCER_INTERACTIVE_CHAT = "interactive_chat_runtime_code"
CODE_PRODUCER_ORCHESTRATOR = "conversation_orchestrator_code"
AGENT_PRODUCER_CONVERSATION_INTAKE = "conversation_intake_agent"


def code_response_provenance(
    producer_id: str,
    *,
    display_name: str | None = None,
    llm_trace_ids: list[str] | None = None,
    generated_from_event_ids: list[str] | None = None,
    fallback: bool = False,
) -> dict[str, Any]:
    return {
        "source_type": "code",
        "producer": {
            "type": "code",
            "id": producer_id,
            "display_name": display_name or _display_name_for_code(producer_id),
            "internal_agent_role": None,
        },
        "llm_trace_ids": list(llm_trace_ids or []),
        "generated_from_event_ids": list(generated_from_event_ids or []),
        "fallback": fallback,
    }


def agent_response_provenance(
    agent_role: str,
    *,
    display_name: str | None = None,
    llm_trace_ids: list[str] | None = None,
    generated_from_event_ids: list[str] | None = None,
    fallback: bool = False,
) -> dict[str, Any]:
    return {
        "source_type": "agent",
        "producer": {
            "type": "agent",
            "id": agent_role,
            "display_name": display_name or _display_name_for_agent(agent_role),
            "internal_agent_role": agent_role,
        },
        "llm_trace_ids": list(llm_trace_ids or []),
        "generated_from_event_ids": list(generated_from_event_ids or []),
        "fallback": fallback,
    }


def unknown_response_provenance() -> dict[str, Any]:
    return {
        "source_type": "unknown",
        "producer": {
            "type": "unknown",
            "id": "unknown",
            "display_name": "Unknown",
            "internal_agent_role": None,
        },
        "llm_trace_ids": [],
        "generated_from_event_ids": [],
        "fallback": False,
    }


def metadata_with_response_provenance(
    metadata: dict[str, Any] | None,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(metadata or {})
    merged["response_provenance"] = provenance
    return merged


def normalize_response_provenance(
    metadata: dict[str, Any] | None,
    role: str,
) -> ConversationResponseProvenance | None:
    if str(role) != "agent":
        return None
    raw = (metadata or {}).get("response_provenance")
    if not isinstance(raw, dict):
        raw = unknown_response_provenance()
    try:
        return ConversationResponseProvenance.model_validate(raw)
    except ValueError:
        return ConversationResponseProvenance.model_validate(
            unknown_response_provenance()
        )


def _display_name_for_code(producer_id: str) -> str:
    if producer_id == CODE_PRODUCER_INTERACTIVE_CHAT:
        return "Interactive Chat Runtime"
    if producer_id == CODE_PRODUCER_ORCHESTRATOR:
        return "Conversation Orchestrator"
    return producer_id


def _display_name_for_agent(agent_role: str) -> str:
    if agent_role == AGENT_PRODUCER_CONVERSATION_INTAKE:
        return "Conversation Intake Agent"
    return agent_role
