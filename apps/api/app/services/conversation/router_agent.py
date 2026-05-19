"""Customer-facing Agent Router for M11.3.5."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.conversation_intake import ConversationIntakeResult
from app.schemas.conversation_router import (
    ApplicationSkillName,
    RouteDecision,
    RouteDecisionKind,
    RouteKnownContext,
    RouteMissingField,
    RouterAgentRole,
    RouteTarget,
)
from app.schemas.llm import LlmMessage, LlmRequest
from app.services import llm_provider
from app.services.conversation.context import ConversationContextBundle
from app.services.conversation.intake import redact_sensitive_payload
from app.services.conversation.prompt_assets import PromptAssetError, load_prompt_asset
from app.services.conversation.skills import ApplicationSkillRegistry

RouterProvider = Callable[
    [dict[str, Any]], RouteDecision | dict[str, Any] | None
]


class CustomerFacingAgentRouterService:
    def __init__(
        self,
        provider: RouterProvider | None = None,
        *,
        confidence_threshold: float = 0.6,
        skill_registry: ApplicationSkillRegistry | None = None,
    ) -> None:
        self._provider = provider
        self.confidence_threshold = confidence_threshold
        self._skill_registry = skill_registry or ApplicationSkillRegistry()
        self._last_trace_payload: dict[str, Any] | None = None
        self.provider_fallback = False

    def route(
        self,
        *,
        raw_message: str,
        intake: ConversationIntakeResult,
        context: ConversationContextBundle,
        page_understanding: dict[str, Any] | None = None,
    ) -> RouteDecision:
        self._last_trace_payload = None
        self.provider_fallback = False
        payload = {
            "raw_message": raw_message,
            "intake": intake.model_dump(mode="json"),
            "context": context.model_dump(mode="json"),
            "page_understanding": page_understanding or {},
            "skill_menu": self._skill_registry.menu_for_prompt(),
        }
        if self._provider is not None:
            provided = self._call_provider(payload)
            if provided is not None:
                return provided
        return deterministic_route(
            raw_message=raw_message,
            intake=intake,
            context=context,
        )

    def consume_last_trace_payload(self) -> dict[str, Any] | None:
        payload = self._last_trace_payload
        self._last_trace_payload = None
        return payload

    def _call_provider(self, payload: dict[str, Any]) -> RouteDecision | None:
        trace_payload = None
        try:
            provided = self._provider(payload)
            if provided is None:
                self.provider_fallback = True
                return None
            if isinstance(provided, dict) and "llm_trace" in provided:
                trace_payload = provided.get("llm_trace")
                provided = provided.get("route_decision")
            if provided is None:
                if isinstance(trace_payload, dict):
                    self._last_trace_payload = redact_sensitive_payload(trace_payload)
                return _safe_provider_error_decision(
                    "router provider returned no route decision"
                )
            decision = (
                provided
                if isinstance(provided, RouteDecision)
                else RouteDecision.model_validate(provided)
            )
            if isinstance(trace_payload, dict):
                self._last_trace_payload = redact_sensitive_payload(trace_payload)
            if decision.source == "provider_error":
                return decision
            if decision.confidence < self.confidence_threshold:
                return decision.model_copy(
                    update={
                        "route_decision": RouteDecisionKind.ASK_USER,
                        "next_agent": RouterAgentRole.CONVERSATION_ORCHESTRATOR,
                        "recommended_skill": (
                            ApplicationSkillName.ASK_USER_FOR_MISSING_INFO
                        ),
                        "reason_summary": "router confidence below threshold",
                        "source": "llm",
                    }
                )
            return decision.model_copy(update={"source": "llm"})
        except (TimeoutError, ConnectionError, RuntimeError) as exc:
            if isinstance(trace_payload, dict):
                self._last_trace_payload = redact_sensitive_payload(trace_payload)
            return _safe_provider_error_decision(
                f"router provider failed: {type(exc).__name__}"
            )
        except (TypeError, ValidationError, ValueError):
            if isinstance(trace_payload, dict):
                self._last_trace_payload = redact_sensitive_payload(trace_payload)
            return _safe_provider_error_decision(
                "router provider output failed schema validation"
            )


def build_runtime_router_service() -> CustomerFacingAgentRouterService:
    return CustomerFacingAgentRouterService(provider=_llm_router_provider)


def deterministic_route(
    *,
    raw_message: str,
    intake: ConversationIntakeResult,
    context: ConversationContextBundle,
) -> RouteDecision:
    target_url = (
        intake.target.url
        or (context.pending_target.url if context.pending_target else None)
        or context.current_message_url
        or context.recent_url
        or context.unique_learned_target_url
    )
    site_origin = intake.target.site_origin or (
        context.pending_target.site_origin if context.pending_target else None
    )
    target_source = _target_source(intake, context)
    matching_actions = _matching_action_count(intake, target_url, context)
    has_required_inputs = _has_required_inputs(intake)
    target = RouteTarget(url=target_url, site_origin=site_origin, source=target_source)
    known_context = RouteKnownContext(
        has_learned_action=matching_actions > 0,
        has_required_user_inputs=has_required_inputs,
        page_context_available=False,
    )

    if _is_bare_url(raw_message, target_url):
        return RouteDecision(
            route_decision=RouteDecisionKind.ASK_USER,
            next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
            recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            target=target,
            user_goal=None,
            known_context=known_context,
            missing_fields=[
                RouteMissingField(
                    semantic_type="operation_goal",
                    display_name="要学习或执行的操作",
                )
            ],
            confidence=0.92,
            reason_summary="user provided only a target URL",
        )

    if intake.confidence < 0.6:
        return RouteDecision(
            route_decision=RouteDecisionKind.ASK_USER,
            next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
            recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            target=target,
            user_goal=intake.action.goal,
            known_context=known_context,
            missing_fields=[
                RouteMissingField(
                    semantic_type="user_intent",
                    display_name="你的操作目标",
                )
            ],
            confidence=max(intake.confidence, 0.1),
            reason_summary="intake confidence below threshold",
        )

    if intake.intent == "learn_operation":
        if intake.missing_fields or intake.should_ask_user:
            return RouteDecision(
                route_decision=RouteDecisionKind.ASK_USER,
                next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
                recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
                target=target,
                user_goal=intake.action.goal,
                known_context=known_context,
                missing_fields=[
                    RouteMissingField(
                        semantic_type=field.semantic_type,
                        display_name=field.display_name,
                    )
                    for field in intake.missing_fields
                ],
                confidence=0.88,
                reason_summary="learning request needs more information",
            )
        return RouteDecision(
            route_decision=RouteDecisionKind.DELEGATE_TO_LEARNING_AGENT,
            next_agent=RouterAgentRole.LEARNING_AGENT,
            recommended_skill=ApplicationSkillName.START_LEARNING,
            target=target,
            user_goal=intake.action.goal,
            known_context=known_context,
            confidence=0.86,
            reason_summary="validated learning request",
        )

    if intake.intent == "provide_missing_info":
        return RouteDecision(
            route_decision=RouteDecisionKind.DELEGATE_TO_LEARNING_AGENT,
            next_agent=RouterAgentRole.LEARNING_AGENT,
            recommended_skill=ApplicationSkillName.START_LEARNING,
            target=target,
            user_goal=intake.action.goal,
            known_context=known_context,
            confidence=0.78,
            reason_summary="user provided missing information for pending task",
        )

    if intake.intent == "execute_operation":
        if matching_actions:
            return RouteDecision(
                route_decision=RouteDecisionKind.DELEGATE_TO_WEB_OPERATION_AGENT,
                next_agent=RouterAgentRole.WEB_OPERATION_AGENT,
                recommended_skill=ApplicationSkillName.START_REPLAY,
                target=target,
                user_goal=intake.action.goal,
                known_context=known_context,
                confidence=0.84,
                reason_summary="current session has a matching learned action",
            )
        if target_url and has_required_inputs and _is_mvp_safe(raw_message):
            return RouteDecision(
                route_decision=RouteDecisionKind.DELEGATE_TO_WEB_OPERATION_AGENT,
                next_agent=RouterAgentRole.WEB_OPERATION_AGENT,
                recommended_skill=ApplicationSkillName.LEARN_THEN_EXECUTE,
                target=target,
                user_goal=intake.action.goal,
                known_context=known_context,
                confidence=0.72,
                reason_summary="task appears complete but target is not learned",
            )
        return RouteDecision(
            route_decision=RouteDecisionKind.ASK_USER,
            next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
            recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            target=target,
            user_goal=intake.action.goal,
            known_context=known_context,
            missing_fields=[
                RouteMissingField(
                    semantic_type="learning_permission",
                    display_name="是否先学习这个操作",
                )
            ],
            confidence=0.68,
            reason_summary="no current-session learned action matched",
        )

    return RouteDecision(
        route_decision=RouteDecisionKind.REPORT_UNKNOWN,
        next_agent=RouterAgentRole.TASK_RESULT_REPORTER,
        recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
        target=target,
        user_goal=intake.action.goal,
        known_context=known_context,
        confidence=0.5,
        reason_summary="no supported route decision",
    )


def _llm_router_provider(
    payload: dict[str, Any],
) -> RouteDecision | dict[str, Any] | None:
    if not settings.llm_api_key:
        return None
    try:
        asset = load_prompt_asset("customer_facing_agent_router", version="v1")
    except PromptAssetError:
        return _safe_provider_error_decision("router prompt asset failed validation")

    request = LlmRequest(
        system=asset.assembled_prompt,
        messages=[
            LlmMessage(
                role="user",
                content=json.dumps(redact_sensitive_payload(payload), ensure_ascii=False),
            )
        ],
        response_schema=RouteDecision.model_json_schema(),
        temperature=0.0,
        max_tokens=1200,
        metadata={"surface": "customer_facing_agent_router"},
    )
    started = time.perf_counter()
    response = llm_provider.generate_structured(request)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = _llm_trace_payload(asset, request, response, latency_ms)
    if response.ok and response.parsed is not None:
        return {"route_decision": response.parsed, "llm_trace": trace}
    error_kind = response.error.kind if response.error is not None else "parse_error"
    return {
        "route_decision": _safe_provider_error_decision(
            f"router provider returned {error_kind}"
        ),
        "llm_trace": trace,
    }


def _safe_provider_error_decision(reason_summary: str) -> RouteDecision:
    return RouteDecision(
        route_decision=RouteDecisionKind.ASK_USER,
        next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
        recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
        confidence=0.0,
        reason_summary=reason_summary,
        source="provider_error",
    )


def _llm_trace_payload(
    asset: Any,
    request: LlmRequest,
    response: Any,
    latency_ms: int,
) -> dict[str, Any]:
    request_payload = request.model_dump(mode="json")
    raw_response = response.model_dump(mode="json") if hasattr(response, "model_dump") else {}
    raw_provider = raw_response.get("raw")
    request_id = raw_provider.get("id") if isinstance(raw_provider, dict) else None
    prompt_material = repr(
        {
            "prompt": asset.assembled_prompt,
            "messages": [message.model_dump() for message in request.messages],
            "schema": request.response_schema,
        }
    )
    return {
        "trace_id": f"trace-{uuid.uuid4()}",
        "purpose": "customer_facing_agent_router",
        "agent_role": "customer_facing_agent_router",
        "provider": "openai_compatible",
        "model": response.model or request.model or settings.llm_default_model,
        "request_id": request_id,
        "prompt_template_id": f"{asset.prompt_id}.{asset.version}",
        "prompt_hash": asset.prompt_sha256
        or hashlib.sha256(prompt_material.encode()).hexdigest(),
        "schema_name": "RouteDecision",
        "schema_version": "m11.3.5",
        "schema_validation": {"ok": bool(response.ok)},
        "latency_ms": latency_ms,
        "token_usage": response.usage.model_dump(mode="json"),
        "raw_request": request_payload,
        "raw_response": raw_response,
        "parsed_output": response.parsed or {},
        "redaction": {
            "applied": True,
            "strategy": "conversation_sensitive_payload_redaction",
        },
    }


def _target_source(
    intake: ConversationIntakeResult,
    context: ConversationContextBundle,
) -> str | None:
    if (
        intake.target.url
        and not context.current_message_url
        and context.pending_target is not None
        and _normalize_url(context.pending_target.url) == _normalize_url(intake.target.url)
    ):
        return "pending_target"
    if intake.target.url:
        return "user_message"
    if context.pending_target is not None:
        return "pending_target"
    if context.recent_url:
        return "recent_message"
    if context.unique_learned_target_url:
        return "unique_learned_action"
    return None


def _is_bare_url(raw_message: str, target_url: str | None) -> bool:
    text = raw_message.strip()
    return bool(target_url and text == target_url)


def _has_required_inputs(intake: ConversationIntakeResult) -> bool:
    return bool(intake.slots) and not intake.missing_fields and not intake.should_ask_user


def _matching_action_count(
    intake: ConversationIntakeResult,
    target_url: str | None,
    context: ConversationContextBundle,
) -> int:
    terms = {
        value
        for value in [
            intake.action.goal,
            intake.action.canonical_goal,
            *intake.action.aliases,
        ]
        if value
    }
    count = 0
    for action in context.learned_actions:
        if (
            target_url
            and action.target_url
            and _normalize_url(action.target_url) != _normalize_url(target_url)
        ):
            continue
        action_terms = {action.alias or "", *action.utterances}
        if terms and action_terms.intersection(terms):
            count += 1
        elif not terms and target_url and action.target_url:
            count += 1
    return count


def _normalize_url(url: str | None) -> str:
    return (url or "").rstrip("/")


def _is_mvp_safe(raw_message: str) -> bool:
    high_impact_tokens = (
        "支付",
        "转账",
        "删除",
        "提交订单",
        "购买",
        "付款",
        "delete",
        "pay",
        "transfer",
        "purchase",
    )
    lowered = raw_message.lower()
    return not any(token in raw_message or token in lowered for token in high_impact_tokens)
